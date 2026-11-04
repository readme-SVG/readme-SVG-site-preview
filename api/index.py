"""Flask routes for website metadata, SVG badges, and static UI assets."""

from pathlib import Path
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup, SoupStrainer
from flask import Flask, Response, jsonify, request, send_from_directory

from .cache import TTLCache
from .card import generate_svg
from .network import FetchError, fetch_public_bytes, resolve_public_address
from .validation import (
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    clamp,
    clean_text,
    normalize_color,
    normalize_website_url,
    safe_float,
    safe_int,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
MAX_HTML_BYTES = 512 * 1024
MAX_QUERY_BYTES = 8 * 1024
TITLE_POSITIONS = {
    "top": "overlay_top",
    "bottom": "overlay_bottom",
    "overlay_top": "overlay_top",
    "overlay_bottom": "overlay_bottom",
    "outside_top": "outside_top",
    "outside_bottom": "outside_bottom",
}
_TITLE_CACHE = TTLCache[str, str](max_entries=256, ttl=60)
app = Flask(__name__, static_folder=None)


def build_screenshot_url(url: str) -> str:
    return f"https://s0.wordpress.com/mshots/v1/{quote(url, safe='')}?w=1200&h=630"


def fetch_website_info(url: str) -> dict:
    """Preserve the metadata fallback while rejecting unsafe target URLs."""
    url = normalize_website_url(url)
    screenshot_url = build_screenshot_url(url)
    title = _TITLE_CACHE.get(url)
    if title is None:
        title = "Website Link"
        try:
            resource = fetch_public_bytes(url, max_bytes=MAX_HTML_BYTES, timeout=4)
            soup = BeautifulSoup(resource.data, "html.parser", parse_only=SoupStrainer("title"))
            title_tag = soup.find("title")
            if title_tag:
                candidate = clean_text(title_tag.get_text()).strip()
                if candidate:
                    title = candidate[:100]
            _TITLE_CACHE.set(url, title, size=len(url) + len(title))
        except (FetchError, ValueError):
            # A missing title must not prevent screenshot generation.
            title = "Website Link"
            _TITLE_CACHE.set(url, title, size=len(url) + len(title), ttl=5)
    return {"title": title, "image_url": screenshot_url, "url": url}


def _target_url() -> tuple[str | None, Response | None]:
    if len(request.query_string) > MAX_QUERY_BYTES:
        return None, Response("Query string is too large", status=414)
    url = request.args.get("url", "").strip()
    if not url:
        return None, Response("Missing 'url' parameter", status=400)
    if len(url) > MAX_URL_LENGTH:
        return None, Response("Website URL is too long", status=400)
    try:
        normalized = normalize_website_url(url)
        hostname = urlsplit(normalized).hostname or ""
        resolve_public_address(hostname, 443 if urlsplit(normalized).scheme == "https" else 80)
        return normalized, None
    except (ValueError, FetchError):
        return None, Response("Invalid or unsupported website URL", status=400)


@app.after_request
def security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path not in {"/badge", "/info"}:
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'",
        )
    return response


@app.route("/")
def index():
    return send_from_directory(ROOT_DIR, "index.html", max_age=0)


@app.route("/styles.css")
def styles():
    return send_from_directory(ROOT_DIR, "styles.css", mimetype="text/css", max_age=300)


@app.route("/app.js")
def script():
    return send_from_directory(ROOT_DIR, "app.js", mimetype="application/javascript", max_age=0)


@app.route("/i18n/<path:path>")
def i18n_files(path: str):
    # Only translation modules are public; never expose arbitrary root files.
    if not path.endswith(".js"):
        return Response("Not found", status=404)
    return send_from_directory(
        ROOT_DIR / "i18n", path, mimetype="application/javascript", max_age=300
    )


@app.route("/badge")
def badge():
    url, error = _target_url()
    if error is not None:
        return error

    width = clamp(safe_int(request.args.get("width"), 320), 200, 1000)
    height = clamp(safe_int(request.args.get("height"), 0), 0, 1000)
    radius = clamp(safe_int(request.args.get("radius"), 10), 0, 30)
    title_color = normalize_color(request.args.get("title_color"), "#ffffff")
    title_opacity = clamp(safe_float(request.args.get("title_opacity"), 1.0), 0.0, 1.0)
    plate_color = normalize_color(request.args.get("plate_color"), "#0f1117")
    plate_opacity = clamp(safe_float(request.args.get("plate_opacity"), 0.78), 0.0, 1.0)
    title_position = TITLE_POSITIONS.get(
        request.args.get("title_position", "overlay_bottom").lower(), "overlay_bottom"
    )
    image_scale = clamp(safe_float(request.args.get("image_scale"), 1.0), 0.1, 3.0)
    image_offset_x = clamp(safe_int(request.args.get("image_offset_x"), 0), -1000, 1000)
    image_offset_y = clamp(safe_int(request.args.get("image_offset_y"), 0), -1000, 1000)
    border_width = clamp(safe_int(request.args.get("border_width"), 1), 0, 10)
    border_color = normalize_color(request.args.get("border_color"), "#ffffff")
    embed = request.args.get("embed", "true").lower() != "false"

    custom_title = clean_text(request.args.get("custom_title", ""))[:MAX_TITLE_LENGTH].strip()
    title = custom_title or fetch_website_info(url)["title"]

    svg = generate_svg(
        title=title,
        image_url=build_screenshot_url(url),
        width=width,
        card_height=height,
        background_color="#000000",
        title_color=title_color,
        title_opacity=title_opacity,
        title_plate_opacity=plate_opacity,
        title_plate_color=plate_color,
        title_position=title_position,
        border_radius=radius,
        border_width=border_width,
        border_color=border_color,
        embed_thumbnail=embed,
        image_scale=image_scale,
        image_offset_x=image_offset_x,
        image_offset_y=image_offset_y,
    )
    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=60",
            "Access-Control-Allow-Origin": "*",
            "Content-Security-Policy": "default-src 'none'; img-src data: https:; style-src 'unsafe-inline'; sandbox",
        },
    )


@app.route("/info")
def info():
    url, error = _target_url()
    if error is not None:
        return error
    response = jsonify(fetch_website_info(url))
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "public, max-age=60"
    return response
