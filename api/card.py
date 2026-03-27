import base64
import textwrap
import urllib.request
from typing import Optional

def fetch_image_as_base64(url: str) -> Optional[str]:
    if not url: return None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; sitebadge/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
            encoded = base64.b64encode(data).decode("utf-8")
            return f"data:{ct};base64,{encoded}"
    except Exception:
        return None

def _wrap(title: str, max_chars: int, max_lines: int = 2) -> list[str]:
    lines = textwrap.wrap(title, width=max(16, max_chars))
    return lines[:max_lines]

def _esc(text: str) -> str:
    if not text: return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )

def generate_svg(
    title: str,
    image_url: str,
    width: int = 320,
    card_height: int = 0,
    background_color: str = "#0f1117",
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

    r = border_radius
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
        if is_outside:
            thumb_height = card_h - text_h
        else:
            thumb_height = card_h
        thumb_height = max(0, thumb_height)
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
        f'<clipPath id="tc">'
        f'<rect x="0" y="0" width="{width}" height="{card_h}" rx="{r}"/>'
        f'</clipPath>'
    )

    title_svg = ""
    for i, line in enumerate(title_lines):
        y = plate_y + pad_top + (i + 1) * line_h - 3
        title_svg += (
            f'<text x="14" y="{y}" '
            f'fill="{_esc(title_color)}" '
            f'fill-opacity="{title_opacity:.2f}" '
            f'font-size="13.5" font-weight="600" '
            f'font-family="\'Segoe UI\',\'Helvetica Neue\',Arial,sans-serif" '
            f'letter-spacing="-0.01em">{_esc(line)}</text>\n  '
        )

    img_w = width * image_scale
    img_h = thumb_height * image_scale
    img_x = (width - img_w) / 2 + image_offset_x
    img_y = thumb_y + (thumb_height - img_h) / 2 + image_offset_y

    image_svg = ""
    if thumb_src:
        image_svg = f'<image href="{thumb_src}" x="{img_x}" y="{img_y}" width="{img_w}" height="{img_h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#tc)"/>'
    else:
        image_svg = f'<rect x="0" y="{thumb_y}" width="{width}" height="{thumb_height}" fill="#2a2a2a" clip-path="url(#tc)"/><text x="{width//2}" y="{thumb_y + thumb_height//2}" fill="#666" font-size="14" text-anchor="middle" font-family="sans-serif">No Image</text>'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{card_h}" viewBox="0 0 {width} {card_h}"
     role="img" aria-label="{_esc(title)}">
  <defs>
    {thumb_clip}
  </defs>
  <rect width="{width}" height="{card_h}" rx="{r}" fill="{_esc(background_color)}"/>
  {image_svg}
  <rect x="0" y="{plate_y}" width="{width}" height="{text_h}"
        fill="{_esc(title_plate_color)}" fill-opacity="{title_plate_opacity:.2f}"
        clip-path="url(#tc)"/>
  {title_svg}
  <rect width="{width}" height="{card_h}" rx="{r}" fill="none"
        stroke="{_esc(border_color)}" stroke-width="{border_width}"/>
</svg>"""
