"""Input normalization shared by the HTTP API and SVG renderer."""

import math
import re
from urllib.parse import quote, urlsplit, urlunsplit

MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 300
_HEX_COLOR = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
_XML_CONTROLS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f"
    r"\ud800-\udfff\ufffe\uffff]"
)


def safe_int(value: object, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return default


def safe_float(value: object, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def clamp(number: float, minimum: float, maximum: float):
    return min(max(number, minimum), maximum)


def normalize_color(value: object, default: str) -> str:
    if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value.strip()):
        return default
    color = value.strip().removeprefix("#")
    if len(color) == 3:
        color = "".join(character * 2 for character in color)
    return f"#{color.lower()}"


def clean_text(value: str) -> str:
    """Remove characters that cannot be represented in an XML document."""
    return _XML_CONTROLS.sub("", value)


def normalize_website_url(value: str) -> str:
    """Return an HTTP(S) URL without credentials or ambiguous port/scheme input."""
    if not isinstance(value, str):
        raise ValueError("A website URL must be a string")

    value = value.strip()
    if not value or len(value) > MAX_URL_LENGTH:
        raise ValueError("Invalid website URL length")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("Control characters are not allowed in a website URL")
    if "\\" in value:
        raise ValueError("Backslashes are not allowed in a website URL")
    if "://" not in value:
        value = f"https://{value}"

    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError("Malformed website URL") from exc

    if parts.scheme.lower() not in {"http", "https"} or not hostname:
        raise ValueError("Only HTTP and HTTPS website URLs are supported")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Credentials are not allowed in a website URL")
    if any(character.isspace() for character in parts.netloc):
        raise ValueError("Whitespace is not allowed in a website hostname")

    scheme = parts.scheme.lower()
    if port is not None and port != (443 if scheme == "https" else 80):
        raise ValueError("Only standard HTTP and HTTPS ports are supported")
    try:
        hostname = hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise ValueError("Invalid website hostname") from exc
    if not hostname or len(hostname) > 253:
        raise ValueError("Invalid website hostname")

    # Encode delimiters that would otherwise break Markdown or HTML snippets.
    path = quote(_BAD_PERCENT.sub("%25", parts.path or "/"), safe="/%:@!$&*+,;=-._~")
    query = quote(_BAD_PERCENT.sub("%25", parts.query), safe="/%:@!$&*+,;=-._~?")
    fragment = quote(_BAD_PERCENT.sub("%25", parts.fragment), safe="/%:@!$&*+,;=-._~?")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    return urlunsplit((scheme, netloc, path, query, fragment))
