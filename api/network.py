"""Bounded HTTP fetching with public-address validation and DNS pinning."""

import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import urllib3

from .validation import normalize_website_url

CHUNK_SIZE = 64 * 1024
MAX_REDIRECTS = 3
CONNECT_TIMEOUT = 3.0
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
USER_AGENT = "Mozilla/5.0 (compatible; SitePreview/1.0)"
_IPV6_REJECT_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("fec0::/10", "64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32")
)


class FetchError(Exception):
    """Raised when a remote resource cannot be fetched safely."""


@dataclass(frozen=True)
class FetchedResource:
    data: bytes
    content_type: str


def _public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False
    return not (
        isinstance(ip, ipaddress.IPv6Address)
        and any(ip in network for network in _IPV6_REJECT_NETWORKS)
    )


def resolve_public_address(hostname: str, port: int) -> str:
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if not _public_address(hostname):
            raise FetchError("Non-public addresses are not allowed")
        return str(literal)

    try:
        addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise FetchError("Website hostname could not be resolved") from exc
    if not addresses or any(not _public_address(item[4][0]) for item in addresses):
        raise FetchError("Website hostname must resolve only to public addresses")
    return addresses[0][4][0]


def _raster_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brands = data[8 : min(len(data), 64)]
        if any(brand in brands for brand in (b"avif", b"avis")):
            return "image/avif"
    return None


def fetch_public_bytes(
    url: str,
    *,
    max_bytes: int,
    timeout: float,
    allowed_hosts: set[str] | None = None,
    raster_only: bool = False,
) -> FetchedResource:
    """Fetch a public resource without exposing local networks or unbounded reads.

    Connecting to the validated IP while retaining the original Host and TLS SNI
    prevents a second DNS lookup from changing the destination (DNS rebinding).
    Redirects are validated independently before another connection is opened.
    """
    deadline = time.monotonic() + timeout
    current_url = normalize_website_url(url)
    context = ssl.create_default_context()

    for redirect_count in range(MAX_REDIRECTS + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchError("Remote resource timed out")
        parts = urlsplit(current_url)
        hostname = parts.hostname or ""
        if redirect_count == 0 and allowed_hosts is not None and hostname not in allowed_hosts:
            raise FetchError("Remote resource host is not allowed")
        if redirect_count and raster_only and parts.scheme != "https":
            raise FetchError("Image redirects must use HTTPS")

        port = parts.port or (443 if parts.scheme == "https" else 80)
        address = resolve_public_address(hostname, port)
        pool_type = (
            urllib3.HTTPSConnectionPool if parts.scheme == "https" else urllib3.HTTPConnectionPool
        )
        options = {
            "retries": False,
            "timeout": urllib3.Timeout(
                connect=min(CONNECT_TIMEOUT, remaining), read=remaining, total=remaining
            ),
        }
        if parts.scheme == "https":
            options.update(server_hostname=hostname, assert_hostname=hostname, ssl_context=context)
        pool = pool_type(address, port, **options)
        response = None
        try:
            path = parts.path or "/"
            if parts.query:
                path = f"{path}?{parts.query}"
            host_header = f"[{hostname}]" if ":" in hostname else hostname
            headers = {
                "Host": host_header,
                "User-Agent": USER_AGENT,
                "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8"
                if raster_only
                else "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            }
            response = pool.request(
                "GET",
                path,
                headers=headers,
                redirect=False,
                preload_content=False,
            )
            if response.status in REDIRECT_STATUSES:
                location = response.headers.get("Location")
                if not location or redirect_count == MAX_REDIRECTS:
                    raise FetchError("Remote resource returned an invalid redirect")
                current_url = normalize_website_url(urljoin(current_url, location))
                continue
            if response.status != 200:
                raise FetchError("Remote resource returned an unsuccessful status")

            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if raster_only and content_type not in {
                "image/png",
                "image/jpeg",
                "image/gif",
                "image/webp",
                "image/avif",
            }:
                raise FetchError("Remote resource is not a supported raster image")
            if (
                not raster_only
                and content_type
                and content_type not in {"text/html", "application/xhtml+xml"}
            ):
                raise FetchError("Remote resource is not an HTML document")
            try:
                if int(response.headers.get("Content-Length", "0")) > max_bytes:
                    raise FetchError("Remote resource is too large")
            except ValueError as exc:
                raise FetchError("Remote resource has an invalid length") from exc

            chunks = []
            size = 0
            while True:
                if time.monotonic() >= deadline:
                    raise FetchError("Remote resource timed out")
                chunk = response.read(min(CHUNK_SIZE, max_bytes + 1 - size), decode_content=True)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > max_bytes:
                    raise FetchError("Remote resource is too large")
            data = b"".join(chunks)
            if raster_only:
                detected_type = _raster_type(data)
                if detected_type is None:
                    raise FetchError("Remote resource has invalid image contents")
                content_type = detected_type
            return FetchedResource(data, content_type or "text/html")
        except (urllib3.exceptions.HTTPError, OSError, ValueError) as exc:
            raise FetchError("Remote resource could not be fetched") from exc
        finally:
            if response is not None:
                response.close()
            pool.close()

    raise FetchError("Remote resource exceeded the redirect limit")
