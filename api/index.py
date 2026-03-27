import json
import os
import urllib.parse
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request, send_file
from .card import generate_svg

app = Flask(__name__)

def safe_int(val, default=0):
    try:
        return int(val) if val else default
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def fetch_website_info(url: str) -> dict:
    try:
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        title = "Website Link"
        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                title_tag = soup.find('title')
                if title_tag and title_tag.text:
                    title = title_tag.text.strip()[:100]
        except Exception:
            pass

        encoded_url = urllib.parse.quote(url, safe='')
        screenshot_url = f"https://s0.wordpress.com/mshots/v1/{encoded_url}?w=1200&h=630"

        return {
            "title": title,
            "image_url": screenshot_url,
            "url": url
        }
    except Exception as e:
        return {
            "title": "Error fetching info",
            "image_url": "",
            "url": url
        }

@app.route("/")
def index():
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    return send_file(os.path.abspath(html_path))

@app.route("/styles.css")
def styles():
    css_path = os.path.join(os.path.dirname(__file__), "..", "styles.css")
    return send_file(os.path.abspath(css_path), mimetype="text/css")

@app.route("/app.js")
def script():
    js_path = os.path.join(os.path.dirname(__file__), "..", "app.js")
    return send_file(os.path.abspath(js_path), mimetype="application/javascript")

@app.route("/badge")
def badge():
    url_param = request.args.get("url")
    if not url_param:
        return Response("Missing 'url' parameter", status=400)

    width = min(max(safe_int(request.args.get("width"), 320), 200), 1000)
    height = max(safe_int(request.args.get("height"), 0), 0)
    radius = min(max(safe_int(request.args.get("radius"), 10)), 0), 30)
    bg = "#" + request.args.get("bg", "0f1117").lstrip("#")
    title_color = "#" + request.args.get("title_color", "ffffff").lstrip("#")
    title_opacity = min(max(safe_float(request.args.get("title_opacity"), 1.0), 0.0), 1.0)
    plate_color = "#" + request.args.get("plate_color", "0f1117").lstrip("#")
    plate_opacity = min(max(safe_float(request.args.get("plate_opacity"), 0.78), 0.0), 1.0)
    title_position = request.args.get("title_position", "overlay_bottom").lower()
    
    image_scale = max(safe_float(request.args.get("image_scale"), 1.0), 0.1)
    image_offset_x = safe_int(request.args.get("image_offset_x"), 0)
    image_offset_y = safe_int(request.args.get("image_offset_y"), 0)

    title_position_aliases = {
        "top": "overlay_top", "bottom": "overlay_bottom",
        "overlay_top": "overlay_top", "overlay_bottom": "overlay_bottom",
        "outside_top": "outside_top", "outside_bottom": "outside_bottom",
    }
    title_position = title_position_aliases.get(title_position, "overlay_bottom")
    border_width = min(max(safe_int(request.args.get("border_width"), 1), 0), 10)
    border_color = "#" + request.args.get("border_color", "ffffff").lstrip("#")
    embed = request.args.get("embed", "true").lower() != "false"

    info = fetch_website_info(url_param)
    
    custom_title = request.args.get("custom_title")
    final_title = custom_title if custom_title and custom_title.strip() else info["title"]

    svg = generate_svg(
        title=final_title,
        image_url=info["image_url"],
        width=width,
        card_height=height,
        background_color=bg,
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
        image_offset_y=image_offset_y
    )

    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=60",
            "Access-Control-Allow-Origin": "*",
        },
    )

@app.route("/info")
def info():
    url_param = request.args.get("url")
    if not url_param:
        return Response("Missing 'url' parameter", status=400)

    info_data = fetch_website_info(url_param)
    return Response(
        json.dumps(info_data),
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )
