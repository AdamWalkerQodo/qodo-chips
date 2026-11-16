"""Draw Qodo comment chips as SVG (text as outlines, Lucide icons) and PNG.

Themes: "dark" and "light" are fixed palettes; "auto" is one SVG that follows the page theme.
Styles: "mono" (grey icon) and "color" (icon tinted like today's emoji).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
ICONS = json.loads((HERE / "assets/icons.json").read_text())

H = 20                       # chip height
PALETTES = {
    "dark": {
        "fill": "#3d3d3d", "border": "#6e6e6e", "text": "#f4f4f4", "icon": "#dfdfdf", "divider": "#7d7d7d",
        "sev": ["#ff6b6b", "#ff9a4d", "#f2cc4d"],          # action_required, remediation_recommended, informational
        "tints": {
            "bug": "#ff6b6b", "book-marked": "#6cb6ff", "paperclip": "#c3c3c3", "monitor": "#8fb4d9", "palette": "#ff9a4d",
            "link": "#8fd3e8", "users": "#f5b83d", "scroll": "#d9b98a", "brain": "#f58fc4", "shield-plus": "#9db8ff",
            "menu": "#4ec2a4", "sun-dim": "#f2cc4d", "diamond": "#a8a1fd", "bolt": "#ff9a4d", "move-up-right": "#6cb6ff",
            "eye": "#8fd3e8", "clipboard-check": "#4ec2a4", "pen-tool": "#f58fc4", "triangle": "#d9b98a",
            "square-check": "#6cb6ff", "square-dot": "#a8a1fd", "check": "#4ec2a4", "x": "#ff6b6b",
            "circle-check": "#4ec2a4", "circle-x": "#ff6b6b", "triangle-alert": "#f2cc4d", "sparkles": "#f2cc4d",
            "arrow-big-left": "#f5b83d", "rocket": "#ff6b6b", "scale": "#f5b83d", "file-text": "#6cb6ff",
        },
    },
    "light": {
        "fill": "#f4f4f4", "border": "#d0d0d0", "text": "#1c1c1c", "icon": "#3d3d3d", "divider": "#c3c3c3",
        "sev": ["#cf222e", "#bc4c00", "#9a6700"],
        "tints": {
            "bug": "#cf222e", "book-marked": "#0969da", "paperclip": "#57606a", "monitor": "#4a6785", "palette": "#bc4c00",
            "link": "#1b7c83", "users": "#9a6700", "scroll": "#7d5a2c", "brain": "#bf3989", "shield-plus": "#4f5fd6",
            "menu": "#1a7f64", "sun-dim": "#9a6700", "diamond": "#6e56cf", "bolt": "#bc4c00", "move-up-right": "#0969da",
            "eye": "#1b7c83", "clipboard-check": "#1a7f64", "pen-tool": "#bf3989", "triangle": "#7d5a2c",
            "square-check": "#0969da", "square-dot": "#6e56cf", "check": "#1a7f64", "x": "#cf222e",
            "circle-check": "#1a7f64", "circle-x": "#cf222e", "triangle-alert": "#9a6700", "sparkles": "#9a6700",
            "arrow-big-left": "#9a6700", "rocket": "#cf222e", "scale": "#9a6700", "file-text": "#0969da",
        },
    },
}


def _tint(icon: str, style: str, pal: dict) -> str:
    kind, _, arg = icon.partition(":")
    if style != "color" or kind == "rel":
        return pal["icon"]
    return pal["sev"][int(arg)] if kind == "sev" else pal["tints"].get(icon, pal["icon"])


def _paint(theme: str, style: str, icon: str | None) -> dict:
    """Attribute strings for each chip part. "auto" uses classes plus a stylesheet that follows the page theme."""
    if theme != "auto":
        pal = PALETTES[theme]
        tint = _tint(icon, style, pal) if icon else pal["icon"]
        return {"frame": f'fill="{pal["fill"]}" stroke="{pal["border"]}"', "text": f'fill="{pal["text"]}"',
                "divider": f'fill="{pal["divider"]}"', "stroke": f'stroke="{tint}"', "solid": f'fill="{tint}"', "css": ""}
    def rules(pal):
        tint = _tint(icon, style, pal) if icon else pal["icon"]
        return (f'.f{{fill:{pal["fill"]};stroke:{pal["border"]}}}.t{{fill:{pal["text"]}}}.d{{fill:{pal["divider"]}}}'
                f'.i{{stroke:{tint}}}.b{{fill:{tint}}}')
    css = f'<style>{rules(PALETTES["light"])}@media (prefers-color-scheme:dark){{{rules(PALETTES["dark"])}}}</style>'
    return {"frame": 'class="f"', "text": 'class="t"', "divider": 'class="d"', "stroke": 'class="i"', "solid": 'class="b"', "css": css}


@lru_cache
def _font(weight: str):
    font = TTFont(HERE / f"assets/Inter-{weight}.woff2")
    return font, font.getGlyphSet(), font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm, font["OS/2"].sCapHeight


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def text_path(text: str, size: float, x: float, weight: str = "Regular", height: float = H) -> tuple[str, float]:
    """Return (path data, width) for `text` set in Inter, vertically centred on its capitals."""
    _, glyphs, cmap, hmtx, upm, cap = _font(weight)
    scale = size / upm
    baseline = (height + cap * scale) / 2
    pen, cursor = SVGPathPen(glyphs, ntos=_num), x
    for ch in text:
        name = cmap[ord(ch)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cursor, baseline)))
        cursor += hmtx[name][0] * scale
    return pen.getCommands(), cursor - x


def _attrs(a: dict) -> str:
    return " ".join(f'{k}="{v}"' for k, v in a.items())


def lucide(name: str, x: float, stroke: str, size: float = 12) -> str:
    shapes = "".join(f"<{tag} {_attrs(a)}/>" for tag, a in ICONS[name])
    return (f'<g transform="translate({_num(x)} {_num((H - size) / 2)}) scale({_num(size / 24)})" fill="none" '
            f'{stroke} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{shapes}</g>')


def severity_bars(level: int, x: float, solid: str) -> str:
    """The portal's three-bar mark: 3 bars filled for level 0, 2 for level 1, 1 for level 2."""
    filled, out = 3 - level, ""
    for i, (bx, bh) in enumerate([(0.75, 4), (4.75, 7), (8.75, 10)]):
        out += (f'<rect x="{_num(x + bx)}" y="{_num(4 + 11 - bh)}" width="2.5" height="{bh}" rx="1" {solid}'
                f'{"" if i < filled else " opacity=\"0.3\""}/>')
    return out


def relevance_dots(n: int, x: float, solid: str) -> str:
    return "".join(f'<circle cx="{_num(x + cx)}" cy="10" r="1.7" {solid}{"" if i < n else " opacity=\"0.25\""}/>'
                   for i, cx in enumerate([2, 6, 10]))


def _icon(icon: str | None, x: float, paint: dict) -> str:
    if not icon:
        return ""
    kind, _, arg = icon.partition(":")
    if kind == "sev":
        return severity_bars(int(arg), x, paint["solid"])
    if kind == "rel":
        return relevance_dots(int(arg), x, paint["solid"])
    return lucide(icon, x, paint["stroke"])


def _svg(width: float, body: str) -> str:
    w = _num(width)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" viewBox="0 0 {w} {H}">{body}</svg>'


def chip(icon: str | None, label: str | None, count: str | None = None, style: str = "mono", theme: str = "dark") -> tuple[str, float]:
    """A label chip; `count` adds a divided number cell. `theme` is dark, light or auto. Returns (svg body, width)."""
    paint, pad, x, body = _paint(theme, style, icon), 7, 7, ""
    if icon:
        body += _icon(icon, x, paint)
        x += 12
    if label:
        x += 4 if icon else 0
        d, w = text_path(label, 11.5, x)
        body += f'<path d="{d}" {paint["text"]}/>'
        x += w
    if count is not None:
        x += 5
        body += f'<rect x="{_num(x)}" y="4" width="1" height="12" {paint["divider"]}/>'
        x += 6
        d, w = text_path(count, 11.5, x, "SemiBold")
        body += f'<path d="{d}" {paint["text"]}/>'
        x += w
    width = round(x + pad)
    frame = f'<rect x="0.5" y="0.5" width="{width - 1}" height="{H - 1}" rx="5.5" {paint["frame"]}/>'
    return paint["css"] + frame + body, width


def pill(label: str, color: str, icon: str | None = None) -> tuple[str, float]:
    """A group pill: solid colour, white semibold label. Same on light and dark pages."""
    x, body = 8, ""
    if icon:
        body += _icon(icon, x, {"stroke": 'stroke="#ffffff"', "solid": 'fill="#ffffff"'})
        x += 12 + 6
    d, w = text_path(label, 12, x, "SemiBold")
    body += f'<path d="{d}" fill="#ffffff"/>'
    width = round(x + w + 8)
    return f'<rect width="{width}" height="{H}" rx="4" fill="{color}"/>' + body, width
