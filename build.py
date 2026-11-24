#!/usr/bin/env python3
"""Build the news-image-20261124 front page.

Reads stories.json (42 verified stories for Tuesday 24 November 2026) and
land-110m.json (Natural Earth, public domain), writes page.html (1024x1024).
A separate shot step screenshots page.html to entry.png.

Layout (frozen spec): margin 16, gutter 6.
  masthead 140 | hero 178 (4 cols) | cards 238 (2 rows x 6) |
  figure strip 48 (5 cells) | map+panel 200 (map 560 + panel 426) |
  index 112 (4 cols) | footer 40.  Total: 1024.
Typography: Noto Serif bold (masthead + headlines), Noto Sans (labels).
Colours: ink #12395b, paper #f7f5ef, teal #0f766e, amber #d97706, red #b91c1c.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = 1024
MARGIN = 16
GUT = 6
CW = W - 2 * MARGIN  # 992 content width

INK = "#12395b"
PAPER = "#f7f5ef"
TEAL = "#0f766e"
AMBER = "#d97706"
RED = "#b91c1c"
GREY = "#5b6770"
LINE = "#d8d2c4"

# ---------------------------------------------------------------- data
def load_stories():
    with open(os.path.join(HERE, "stories.json"), encoding="utf-8") as f:
        return json.load(f)


def load_land():
    with open(os.path.join(HERE, "land-110m.json"), encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------- topojson -> svg paths
def topo_to_paths(topo, width, height, lat_clip=60.0):
    """Decode TopoJSON land arcs to SVG path strings (equirectangular)."""
    transform = topo["transform"]
    sx, sy = transform["scale"]
    tx, ty = transform["translate"]
    arcs = topo["arcs"]
    decoded = []
    for arc in arcs:
        x, y = 0, 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        decoded.append(pts)

    def project(lon, lat):
        lat = max(-lat_clip, min(lat_clip, lat))
        px = (lon + 180.0) / 360.0 * width
        py = (lat_clip - lat) / (2 * lat_clip) * height
        return px, py

    paths = []
    for geom in topo["objects"]["land"]["geometries"]:
        for poly in geom["arcs"]:
            rings = []
            for ring in poly:
                pts = []
                for ai in ring:
                    arc = decoded[ai] if ai >= 0 else list(reversed(decoded[~ai]))
                    pts.extend(arc)
                # convert lon/lat to x/y
                xy = [project(lon, lat) for lon, lat in pts]
                rings.append(xy)
            d = ""
            for ring in rings:
                if not ring:
                    continue
                d += "M%.1f,%.1f" % ring[0]
                for px, py in ring[1:]:
                    d += "L%.1f,%.1f" % (px, py)
                d += "Z"
            if d:
                paths.append(d)
    return paths


def lonlat_to_xy(lon, lat, width, height, lat_clip=60.0):
    lat = max(-lat_clip, min(lat_clip, lat))
    px = (lon + 180.0) / 360.0 * width
    py = (lat_clip - lat) / (2 * lat_clip) * height
    return px, py


# ------------------------------------------------------------- art motifs
# Small editorial SVG illustrations: 2-3 bold colours each, no real faces.
# Each motif is drawn in a viewBox of its own; caller scales it.
def art_svg(kind, w, h, bg):
    inner = {
        "globe": '<circle cx="50" cy="42" r="30" fill="#0f766e"/><path d="M20,42 Q50,22 80,42 Q50,62 20,42 Z" fill="#f7f5ef"/><path d="M50,12 L50,72 M28,20 Q50,42 72,20 M28,64 Q50,42 72,64" stroke="#f7f5ef" stroke-width="2" fill="none"/>',
        "flag": '<rect x="30" y="12" width="4" height="60" fill="#12395b"/><path d="M34,14 L78,14 L70,28 L78,42 L34,42 Z" fill="#b91c1c"/>',
        "chart": '<rect x="18" y="48" width="12" height="24" fill="#0f766e"/><rect x="38" y="36" width="12" height="36" fill="#d97706"/><rect x="58" y="22" width="12" height="50" fill="#12395b"/><polyline points="14,30 40,22 66,12 86,6" stroke="#b91c1c" stroke-width="3" fill="none"/>',
        "chip": '<rect x="28" y="22" width="44" height="44" rx="4" fill="#12395b"/><rect x="40" y="34" width="20" height="20" fill="#d97706"/><path d="M32,22 V12 M48,22 V12 M64,22 V12 M32,66 V76 M48,66 V76 M64,66 V76 M28,32 H18 M28,48 H18 M28,62 H18 M72,32 H82 M72,48 H82 M72,62 H82" stroke="#12395b" stroke-width="3"/>',
        "trophy": '<path d="M38,14 H62 L60,44 Q60,56 50,56 Q40,56 40,44 Z" fill="#d97706"/><path d="M38,18 Q22,18 24,32 Q26,42 38,40 M62,18 Q78,18 76,32 Q74,42 62,40" stroke="#d97706" stroke-width="4" fill="none"/><rect x="46" y="56" width="8" height="8" fill="#12395b"/><rect x="38" y="64" width="24" height="5" fill="#12395b"/>',
        "ball": '<circle cx="50" cy="44" r="30" fill="#f7f5ef" stroke="#12395b" stroke-width="2"/><path d="M50,26 L62,38 L58,54 L42,54 L38,38 Z" fill="#12395b"/><path d="M50,26 L50,14 M62,38 L76,32 M58,54 L66,66 M42,54 L34,66 M38,38 L24,32" stroke="#12395b" stroke-width="2"/>',
        "flask": '<path d="M44,12 H56 V36 L74,64 Q76,70 70,70 H30 Q24,70 26,64 L44,36 Z" fill="#0f766e"/><circle cx="44" cy="56" r="4" fill="#f7f5ef"/><circle cx="56" cy="62" r="3" fill="#f7f5ef"/>',
        "rocket": '<path d="M50,8 Q66,26 62,48 L58,58 L42,58 L38,48 Q34,26 50,8 Z" fill="#b91c1c"/><circle cx="50" cy="34" r="7" fill="#f7f5ef"/><path d="M42,58 L36,70 L46,64 M58,58 L64,70 L54,64" fill="#d97706"/><path d="M50,58 L50,72" stroke="#d97706" stroke-width="3"/>',
        "leaf": '<path d="M50,12 Q82,28 78,58 Q74,76 50,78 Q26,76 22,58 Q18,28 50,12 Z" fill="#0f766e"/><path d="M50,20 L50,74 M50,40 L66,30 M50,40 L34,30 M50,56 L68,46 M50,56 L32,46" stroke="#f7f5ef" stroke-width="2" fill="none"/>',
        "quake": '<path d="M10,70 L28,52 L38,62 L52,40 L64,52 L76,30 L90,44" stroke="#b91c1c" stroke-width="4" fill="none"/><path d="M10,70 L90,70" stroke="#12395b" stroke-width="3"/>',
        "gavel": '<rect x="24" y="30" width="40" height="14" rx="3" fill="#12395b" transform="rotate(-30 44 37)"/><rect x="58" y="46" width="6" height="26" fill="#12395b" transform="rotate(-30 61 59)"/><rect x="20" y="66" width="60" height="6" rx="3" fill="#d97706"/>',
        "mask": '<path d="M30,20 Q50,12 70,20 Q74,44 60,58 Q50,64 40,58 Q26,44 30,20 Z" fill="#d97706"/><circle cx="42" cy="36" r="4" fill="#12395b"/><circle cx="58" cy="36" r="4" fill="#12395b"/><path d="M44,50 Q50,54 56,50" stroke="#12395b" stroke-width="2" fill="none"/>',
        "health": '<circle cx="50" cy="44" r="30" fill="#f7f5ef" stroke="#0f766e" stroke-width="3"/><rect x="46" y="28" width="8" height="32" fill="#0f766e"/><rect x="34" y="40" width="32" height="8" fill="#0f766e"/>',
        "shield": '<path d="M50,10 L78,20 V44 Q78,64 50,74 Q22,64 22,44 V20 Z" fill="#12395b"/><path d="M38,44 L48,54 L64,32" stroke="#f7f5ef" stroke-width="4" fill="none"/>',
        "bolt": '<path d="M56,8 L28,48 H46 L40,76 L72,34 H52 Z" fill="#d97706"/>',
        "book": '<path d="M22,18 Q36,12 50,18 Q64,12 78,18 V66 Q64,60 50,66 Q36,60 22,66 Z" fill="#0f766e"/><path d="M50,18 V66" stroke="#f7f5ef" stroke-width="2"/><path d="M28,26 H44 M28,34 H44 M56,26 H72 M56,34 H72" stroke="#f7f5ef" stroke-width="2"/>',
        "volcano": '<path d="M50,12 L80,72 L20,72 Z" fill="#6b4a2f"/><path d="M50,12 L58,26 L50,22 L44,30 L50,12 Z" fill="#b91c1c"/><path d="M47,32 L53,32 L56,72 L44,72 Z" fill="#d97706"/>',
    }.get(kind, '<circle cx="50" cy="44" r="26" fill="#0f766e"/>')
    return ('<svg width="%d" height="%d" viewBox="0 0 100 84" '
            'xmlns="http://www.w3.org/2000/svg"><rect width="100" height="84" '
            'fill="%s"/>%s</svg>' % (w, h, bg, inner))


CAT_COLOR = {
    "politics": INK, "conflict": RED, "markets": TEAL, "tech": AMBER,
    "sports": TEAL, "culture": AMBER, "science": INK, "climate": TEAL,
    "health": RED, "regional": INK, "space": INK, "energy": AMBER,
}

ART_BG = ["#dcebe8", "#fbeed3", "#f3ddd8", "#dbe4ee"]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))

# ------------------------------------------------------- section builders
def css():
    return """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1024px;height:1024px;background:%s;font-family:'Noto Sans',sans-serif;color:%s;overflow:hidden}
.page{width:1024px;height:1024px;padding:16px 16px 0 16px}
.rule{height:2px;background:%s;margin:8px 0 0 0}
.masthead{height:140px}
.mast-name{font-family:'Noto Serif',serif;font-weight:700;font-size:22px;letter-spacing:6px;color:%s}
.mast-date{font-family:'Noto Serif',serif;font-weight:700;font-size:52px;line-height:1.02;color:%s;margin-top:4px}
.mast-sub{font-size:11px;letter-spacing:2px;color:%s;margin-top:6px}
.hero{height:178px;display:flex;gap:6px;margin-top:6px}
.hero-cell{flex:1;border-top:3px solid %s;padding-top:6px;position:relative}
.hero-num{position:absolute;top:6px;right:0;font-family:'Noto Serif',serif;font-weight:700;font-size:20px;color:%s}
.hero-kick{font-size:9.5px;font-weight:700;letter-spacing:1.5px;color:%s;text-transform:uppercase}
.hero-art{margin-top:5px}
.hero-head{font-family:'Noto Serif',serif;font-weight:700;font-size:22px;line-height:1.08;margin-top:5px}
.hero-sub{font-size:11px;line-height:1.25;color:%s;margin-top:3px}
.cards{height:238px;margin-top:6px}
.card-row{display:flex;gap:6px}
.card-row + .card-row{margin-top:6px}
.card{flex:1;border-top:2px solid %s;padding-top:5px}
.card-kick{font-size:8.5px;font-weight:700;letter-spacing:1px;color:%s;text-transform:uppercase}
.card-head{font-family:'Noto Serif',serif;font-weight:700;font-size:15px;line-height:1.12;margin-top:3px}
.card-sub{font-size:9.5px;line-height:1.25;color:%s;margin-top:2px}
.strip{height:48px;margin-top:6px;display:flex;gap:6px}
.strip-cell{flex:1;background:%s;color:%s;text-align:center;padding-top:5px}
.strip-val{font-family:'Noto Serif',serif;font-weight:700;font-size:24px;line-height:1}
.strip-lab{font-size:9px;font-weight:700;letter-spacing:1px;margin-top:2px}
.maprow{height:200px;margin-top:6px;display:flex;gap:6px}
.mapbox{width:560px;height:200px;background:#e8eef2;position:relative;border:1px solid %s}
.map-title{position:absolute;top:6px;left:8px;font-size:9px;font-weight:700;letter-spacing:1.5px;color:%s}
.pin{position:absolute;width:16px;height:16px;border-radius:50%%;background:%s;color:#fff;font-size:9px;font-weight:700;text-align:center;line-height:16px;transform:translate(-50%%,-50%%)}
.panel{flex:1;background:%s;padding:10px 12px;color:#f7f5ef}
.panel h3{font-family:'Noto Serif',serif;font-size:15px;margin-bottom:6px}
.panel p{font-size:10.5px;line-height:1.45;margin-bottom:5px}
.panel b{color:#f5c86b}
.index{height:112px;margin-top:6px}
.index h3{font-size:11px;font-weight:700;letter-spacing:2px;color:%s;margin-bottom:4px}
.index-cols{display:flex;gap:6px}
.index-col{flex:1}
.index-item{font-size:10.5px;line-height:1.28;color:%s;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.index-item b{color:%s}
.footer{height:40px;margin-top:6px;border-top:2px solid %s;display:flex;align-items:center;justify-content:center}
.footer span{font-size:11px;font-weight:700;letter-spacing:1.5px;color:%s}
""" % (PAPER, INK, INK, INK, INK, GREY, INK, INK, TEAL, GREY, INK, TEAL,
        GREY, INK, PAPER, LINE, INK, RED, INK, INK, INK, TEAL, INK, INK)


def masthead_html():
    return """
<div class="masthead">
  <div class="mast-name">THE WORLD IN ONE DAY</div>
  <div class="mast-date">TUESDAY, 24 NOVEMBER 2026</div>
  <div class="mast-sub">FORTY-TWO VERIFIED STORIES FROM ONE DAY &middot; ALL TIMES WIB / UTC</div>
  <div class="rule"></div>
</div>"""


def hero_html(heroes):
    cells = []
    for i, s in enumerate(heroes):
        col = CAT_COLOR.get(s.get("cat", "politics"), INK)
        bg = ART_BG[i % len(ART_BG)]
        cells.append("""
  <div class="hero-cell" style="border-top-color:%s">
    <div class="hero-num">%d</div>
    <div class="hero-kick" style="color:%s">%s</div>
    <div class="hero-art">%s</div>
    <div class="hero-head">%s</div>
    <div class="hero-sub">%s</div>
  </div>""" % (col, s["n"], col, esc(s["kick"]), art_svg(s.get("art", "globe"), 242, 62, bg),
               esc(s["title"]), esc(s["sub"])))
    return '<div class="hero">' + "".join(cells) + "</div>"


def cards_html(cards):
    rows = []
    for r in range(2):
        cells = []
        for s in cards[r * 6:(r + 1) * 6]:
            col = CAT_COLOR.get(s.get("cat", "politics"), INK)
            cells.append("""
    <div class="card" style="border-top-color:%s">
      <div class="card-kick" style="color:%s">%d &middot; %s</div>
      <div class="card-head">%s</div>
      <div class="card-sub">%s</div>
    </div>""" % (col, col, s["n"], esc(s["kick"]), esc(s["title"]), esc(s["sub"])))
        rows.append('<div class="card-row">' + "".join(cells) + "</div>")
    return '<div class="cards">' + "".join(rows) + "</div>"


def strip_html(figures):
    cells = []
    for f in figures:
        cells.append("""
  <div class="strip-cell">
    <div class="strip-val">%s</div>
    <div class="strip-lab">%s</div>
  </div>""" % (esc(f["value"]), esc(f["label"])))
    return '<div class="strip">' + "".join(cells) + "</div>"


def map_html(stories, land_paths):
    land = "".join('<path d="%s" fill="#b9c9d4" stroke="#f7f5ef" stroke-width="0.5"/>' % p
                   for p in land_paths)
    pins = []
    for s in stories:
        if s.get("lat") is None or s.get("lon") is None:
            continue
        x, y = lonlat_to_xy(s["lon"], s["lat"], 560, 200)
        pins.append('<div class="pin" style="left:%.1fpx;top:%.1fpx">%d</div>'
                    % (x, y, s["n"]))
    svg = ('<svg width="560" height="200" viewBox="0 0 560 200" '
           'xmlns="http://www.w3.org/2000/svg">%s</svg>' % land)
    return ('<div class="maprow"><div class="mapbox"><div class="map-title">'
            'WHERE IT HAPPENED &mdash; NUMBERED BY STORY</div>%s%s</div>'
            % (svg, "".join(pins)))


def panel_html(brief):
    items = "".join("<p><b>%s</b> %s</p>" % (esc(b), esc(t)) for b, t in brief)
    return ('<div class="panel"><h3>The day in brief</h3>%s</div></div>'
            % items)


def index_html(index_items):
    cols = []
    per = 7
    for c in range(4):
        chunk = index_items[c * per:(c + 1) * per]
        items = "".join(
            '<div class="index-item"><b>%d.</b> %s</div>' % (s["n"], esc(s["title"]))
            for s in chunk)
        cols.append('<div class="index-col">' + items + "</div>")
    return ('<div class="index"><h3>ALSO TODAY</h3><div class="index-cols">'
            + "".join(cols) + "</div></div>")


def footer_html():
    return ('<div class="footer"><span>DATE CHECK &mdash; EVERY STORY DATED '
            '24 NOVEMBER 2026 OR REPORTED THAT DAY</span></div>')


def build_page(data):
    land = load_land()
    paths = topo_to_paths(land, 560, 200)
    heroes = data["hero"]
    cards = data["cards"]
    figures = data["figures"]
    index_items = data["index"]
    all_stories = heroes + cards + index_items
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style>"
            "</head><body><div class='page'>%s%s%s%s%s%s%s%s</div></body></html>"
            % (css(), masthead_html(), hero_html(heroes), cards_html(cards),
               strip_html(figures), map_html(all_stories, paths),
               panel_html(data["brief"]), index_html(index_items),
               footer_html()))
    return html


def main():
    data = load_stories()
    html = build_page(data)
    with open(os.path.join(HERE, "page.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("page.html written:", len(html), "bytes")


if __name__ == "__main__":
    main()
