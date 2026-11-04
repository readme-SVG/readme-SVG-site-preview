"""SVG website card rendering and optional thumbnail embedding."""

import base64
import textwrap
from html import escape

from .cache import TTLCache
from .network import FetchError, fetch_public_bytes
from .validation import MAX_TITLE_LENGTH, clean_text

MAX_IMAGE_BYTES = 4 * 1024 * 1024
_IMAGE_CACHE = TTLCache[str, str](max_entries=32, ttl=60, max_bytes=24 * 1024 * 1024)
_SCREENSHOT_HOSTS = {"s0.wordpress.com", "s0.wp.com", "s1.wp.com", "s2.wp.com", "s3.wp.com"}


def fetch_image_as_base64(url: str) -> str | None:
    if not url:
        return None
    cached = _IMAGE_CACHE.get(url)
    if cached is not None:
        return cached
    try:
        resource = fetch_public_bytes(
            url,
            max_bytes=MAX_IMAGE_BYTES,
            timeout=8,
            allowed_hosts=_SCREENSHOT_HOSTS,
            raster_only=True,
        )
    except (FetchError, ValueError):
        return None
    encoded = base64.b64encode(resource.data).decode("ascii")
    result = f"data:{resource.content_type};base64,{encoded}"
    # Do not keep mshots loading placeholders for a full cache lifetime.
    ttl = 5 if resource.content_type == "image/gif" else None
    _IMAGE_CACHE.set(url, result, size=len(result), ttl=ttl)
    return result


def _wrap(title: str, max_chars: int, max_lines: int = 2) -> list[str]:
    lines = textwrap.wrap(clean_text(title), width=max(16, max_chars))
    return lines[:max_lines]


def _esc(text: str) -> str:
    return escape(clean_text(text), quote=True) if text else ""


def generate_svg(
    title: str,
    image_url: str,
    width: int = 320,
    card_height: int = 0,
    background_color: str = "#000000",
    title_color: str = "#ffffff",
    title_opacity: float = 1.0,
    title_plate_opacity: float = 0.78,
    title_plate_color: str = "#0f1117",
    title_position: str = "overlay_bottom",
    border_radius: int = 10,
    border_width: int = 1,
    border_color: str = "rgba(255,255,255,0.07)",
    embed_thumbnail: bool = True,
    image_scale: float = 1.0,
    image_offset_x: int = 0,
    image_offset_y: int = 0,
) -> str:
    title = clean_text(title)[:MAX_TITLE_LENGTH]
    thumb_src = image_url
    if embed_thumbnail and image_url:
        embedded = fetch_image_as_base64(image_url)
        if embedded:
            thumb_src = embedded

    title_lines = _wrap(title, max_chars=max(18, int(width / 8.0)), max_lines=2)
    line_h = 20
    pad_top = 11
    pad_bot = 11
    text_h = pad_top + len(title_lines) * line_h + pad_bot

    position_map = {
        "top": "overlay_top",
        "bottom": "overlay_bottom",
        "overlay_top": "overlay_top",
        "overlay_bottom": "overlay_bottom",
        "outside_top": "outside_top",
        "outside_bottom": "outside_bottom",
    }
    position = position_map.get(title_position, "overlay_bottom")
    is_outside = position in {"outside_top", "outside_bottom"}

    if card_height > 0:
        card_h = card_height
        thumb_height = max(0, card_h - text_h if is_outside else card_h)
    else:
        thumb_height = int(width * 9 / 16)
        card_h = thumb_height + (text_h if is_outside else 0)

    thumb_y = text_h if position == "outside_top" else 0
    if position == "overlay_top":
        plate_y = 0
    elif position == "overlay_bottom":
        plate_y = thumb_y + thumb_height - text_h
    elif position == "outside_top":
        plate_y = 0
    else:
        plate_y = thumb_height

    thumb_clip = (
        '<clipPath id="tc">'
        f'<rect x="0" y="0" width="{width}" height="{card_h}" rx="{border_radius}"/>'
        "</clipPath>"
    )
    title_parts = []
    for index, line in enumerate(title_lines):
        y = plate_y + pad_top + (index + 1) * line_h - 3
        title_parts.append(
            f'<text x="14" y="{y}" fill="{_esc(title_color)}" '
            f'fill-opacity="{title_opacity:.2f}" font-size="13.5" font-weight="600" '
            "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\" "
            f'letter-spacing="-0.01em">{_esc(line)}</text>'
        )
    title_svg = "\n  ".join(title_parts)

    img_w = width * image_scale
    img_h = thumb_height * image_scale
    img_x = (width - img_w) / 2 + image_offset_x
    img_y = thumb_y + (thumb_height - img_h) / 2 + image_offset_y
    if thumb_src:
        image_svg = (
            f'<image href="{_esc(thumb_src)}" x="{img_x:g}" y="{img_y:g}" '
            f'width="{img_w:g}" height="{img_h:g}" '
            'preserveAspectRatio="xMidYMid slice" clip-path="url(#tc)"/>'
        )
    else:
        image_svg = (
            f'<rect x="0" y="{thumb_y}" width="{width}" height="{thumb_height}" '
            'fill="#2a2a2a" clip-path="url(#tc)"/>'
            f'<text x="{width // 2}" y="{thumb_y + thumb_height // 2}" fill="#666" '
            'font-size="14" text-anchor="middle" font-family="sans-serif">No Image</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{card_h}" viewBox="0 0 {width} {card_h}"
     role="img" aria-label="{_esc(title)}">
  <defs>
    {thumb_clip}
  </defs>
  <rect width="{width}" height="{card_h}" rx="{border_radius}" fill="{_esc(background_color)}"/>
  {image_svg}
  <rect x="0" y="{plate_y}" width="{width}" height="{text_h}"
        fill="{_esc(title_plate_color)}" fill-opacity="{title_plate_opacity:.2f}"
        clip-path="url(#tc)"/>
  {title_svg}
  <rect width="{width}" height="{card_h}" rx="{border_radius}" fill="none"
        stroke="{_esc(border_color)}" stroke-width="{border_width}"/>
</svg>"""
