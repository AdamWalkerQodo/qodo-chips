"""Draw Qodo comment chips as SVG (text as outlines, Lucide icons) and PNG.

Themes: "dark" and "light" are fixed palettes; "auto" is one SVG that follows the page theme.
Styles: "mono" (grey icon) and "color" (icon tinted like today's emoji).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
ICONS = json.loads((HERE / "assets/icons.json").read_text())

H = 20                       # chip height
CHIP_TOP_PAD = 1              # transparent rows above a chip, so its label lines up with 14px comment text
PALETTES = {
    "dark": {
        "fill": "#3d3d3d", "text": "#f4f4f4", "icon": "#dfdfdf", "divider": "#7d7d7d",
        "sev": ["#ff4d4f", "#ff8a2a", "#ffd21f"],          # action_required, remediation_recommended, informational
        "tints": {
            "bug": "#ff4d4f", "book-marked": "#4da3ff", "paperclip": "#c3c3c3", "monitor": "#7ab8f5", "palette": "#ff8a2a",
            "link": "#3fc8e4", "users": "#ffb020", "scroll": "#e6ae62", "brain": "#ff6fb5", "shield-plus": "#7c9dff",
            "menu": "#2fd0a5", "sun-dim": "#ffd21f", "diamond": "#9b8cff", "bolt": "#ff8a2a", "move-up-right": "#4da3ff",
            "eye": "#3fc8e4", "clipboard-check": "#2fd0a5", "pen-tool": "#ff6fb5", "triangle": "#e6ae62",
            "square-check": "#4da3ff", "square-dot": "#9b8cff", "check": "#2fd0a5", "x": "#ff4d4f",
            "circle-check": "#2fd0a5", "circle-x": "#ff4d4f", "triangle-alert": "#ffd21f", "sparkles": "#ffd21f",
            "laptop": "#ffb020", "rocket": "#ff4d4f", "scale": "#ffb020", "file-text": "#4da3ff",
            "flask-conical": "#2fd0a5", "trending-up": "#9b8cff", "settings": "#c3c3c3", "refresh-cw": "#3fc8e4",
            "clock": "#7ab8f5", "bomb": "#ff8a2a", "waypoints": "#9b8cff", "flame": "#ff6fb5",
        },
        "risk": {"high": "#ff4d4f", "medium": "#ffd21f", "low": "#2fd0a5"},
    },
    "light": {
        "fill": "#f4f4f4", "text": "#1c1c1c", "icon": "#3d3d3d", "divider": "#c3c3c3",
        "sev": ["#dc2626", "#d9480f", "#b7791f"],
        "tints": {
            "bug": "#dc2626", "book-marked": "#0b6bdf", "paperclip": "#57606a", "monitor": "#3b6ea5", "palette": "#d9480f",
            "link": "#0e8a92", "users": "#b7791f", "scroll": "#8a5a1c", "brain": "#d6247f", "shield-plus": "#4350e0",
            "menu": "#0f8a66", "sun-dim": "#b7791f", "diamond": "#6741d9", "bolt": "#d9480f", "move-up-right": "#0b6bdf",
            "eye": "#0e8a92", "clipboard-check": "#0f8a66", "pen-tool": "#d6247f", "triangle": "#8a5a1c",
            "square-check": "#0b6bdf", "square-dot": "#6741d9", "check": "#0f8a66", "x": "#dc2626",
            "circle-check": "#0f8a66", "circle-x": "#dc2626", "triangle-alert": "#b7791f", "sparkles": "#b7791f",
            "laptop": "#b7791f", "rocket": "#dc2626", "scale": "#b7791f", "file-text": "#0b6bdf",
            "flask-conical": "#0f8a66", "trending-up": "#6741d9", "settings": "#57606a", "refresh-cw": "#0e8a92",
            "clock": "#3b6ea5", "bomb": "#d9480f", "waypoints": "#6741d9", "flame": "#d6247f",
        },
        "risk": {"high": "#dc2626", "medium": "#b7791f", "low": "#0f8a66"},
    },
}


def _tint(icon: str, style: str, pal: dict) -> str:
    kind, _, arg = icon.partition(":")
    if style != "color" or kind == "rel":
        return pal["icon"]
    if kind == "risk":
        return pal["risk"].get(arg, pal["icon"])
    return pal["sev"][int(arg)] if kind == "sev" else pal["tints"].get(icon, pal["icon"])


def _paint(theme: str, style: str, icon: str | None) -> dict:
    """Attribute strings for each chip part. "auto" uses classes plus a stylesheet that follows the page theme."""
    if theme != "auto":
        pal = PALETTES[theme]
        tint = _tint(icon, style, pal) if icon else pal["icon"]
        return {"frame": f'fill="{pal["fill"]}"', "text": f'fill="{pal["text"]}"',
                "divider": f'fill="{pal["divider"]}"', "stroke": f'stroke="{tint}"', "solid": f'fill="{tint}"', "css": ""}
    def rules(pal):
        tint = _tint(icon, style, pal) if icon else pal["icon"]
        return (f'.f{{fill:{pal["fill"]}}}.t{{fill:{pal["text"]}}}.d{{fill:{pal["divider"]}}}'
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


RISK_SEGMENTS = {"high": 3, "medium": 2, "low": 1}


def risk_meter(level: str, x: float, solid: str) -> str:
    """Overall merge risk: three blocks in a row, filled left to right (3 high, 2 medium, 1 low, 0 unavailable)."""
    return "".join(f'<rect x="{_num(x + bx)}" y="7" width="3.3" height="6" rx="1.2" {solid}'
                   f'{"" if i < RISK_SEGMENTS.get(level, 0) else " opacity=\"0.3\""}/>' for i, bx in enumerate([0, 4.35, 8.7]))


def _icon(icon: str | None, x: float, paint: dict) -> str:
    if not icon:
        return ""
    kind, _, arg = icon.partition(":")
    if kind == "sev":
        return severity_bars(int(arg), x, paint["solid"])
    if kind == "rel":
        return relevance_dots(int(arg), x, paint["solid"])
    if kind == "risk":
        return risk_meter(arg, x, paint["solid"])
    return lucide(icon, x, paint["stroke"])


def _svg(width: float, body: str, top_pad: int = 0) -> str:
    w, h = _num(width), H + top_pad
    if top_pad:
        body = f'<g transform="translate(0 {top_pad})">{body}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


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
    frame = f'<rect width="{width}" height="{H}" rx="6" {paint["frame"]}/>'
    return paint["css"] + frame + body, width


def pill(label: str | None, color: str, icon: str | None = None, count: str | None = None, icon_color: str = "#ffffff") -> tuple[str, float]:
    """A group pill: solid colour, white semibold label, optional icon and counter cell. Same on light and dark pages."""
    x, body = 8, ""
    if icon:
        body += _icon(icon, x, {"stroke": f'stroke="{icon_color}"', "solid": f'fill="{icon_color}"'})
        x += 12
    if label:
        x += 6 if icon else 0
        d, w = text_path(label, 12, x, "SemiBold")
        body += f'<path d="{d}" fill="#ffffff"/>'
        x += w
    if count is not None:
        x += 6
        body += f'<rect x="{_num(x)}" y="4" width="1" height="12" fill="#ffffff" opacity="0.5"/>'
        x += 7
        d, w = text_path(count, 12, x, "SemiBold")
        body += f'<path d="{d}" fill="#ffffff"/>'
        x += w
    width = round(x + 8)
    return f'<rect width="{width}" height="{H}" rx="4" fill="{color}"/>' + body, width


BUTTON_H = 28


def button(label: str, icon: str, primary: bool = False) -> tuple[str, float]:
    """A button image, 28px tall: brand fill with white ink when primary, else an outline with no fill that follows the page theme."""
    if primary:
        css, frame_w = "", f'fill="#634fd1"'
        frame = lambda w: f'<rect width="{w}" height="{BUTTON_H}" rx="6" {frame_w}/>'  # noqa: E731
        ink_fill, ink_stroke = 'fill="#ffffff"', 'stroke="#ffffff"'
    else:
        # Muted ink and a quiet outline, so the outlined buttons sit behind the primary one.
        css = ('<style>.o{stroke:#d0d4d9}.t{fill:#57606a}.i{stroke:#6e7781}'
               '@media (prefers-color-scheme:dark){.o{stroke:#4b515a}.t{fill:#aab1ba}.i{stroke:#8b939c}}</style>')
        frame = lambda w: f'<rect x="0.5" y="0.5" width="{w - 1}" height="{BUTTON_H - 1}" rx="5.5" fill="none" class="o"/>'  # noqa: E731
        ink_fill, ink_stroke = 'class="t"', 'class="i"'
    shapes = "".join(f"<{tag} {_attrs(a)}/>" for tag, a in ICONS[icon])
    body = (f'<g transform="translate(10 7.5) scale({_num(13 / 24)})" fill="none" {ink_stroke} stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{shapes}</g>')
    d, w = text_path(label, 12.5, 29, "SemiBold", BUTTON_H)
    body += f'<path d="{d}" {ink_fill}/>'
    width = round(29 + w + 12)
    return css + frame(width) + body, width


def dotted_divider(width: int = 1200) -> str:
    """A full-width dotted line that follows the page theme."""
    dots = "".join(f'<circle cx="{x}" cy="3" r="1.2"/>' for x in range(3, width, 8))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="6" viewBox="0 0 {width} 6">'
            f'<style>g{{fill:#c3c3c3}}@media (prefers-color-scheme:dark){{g{{fill:#5a5a5a}}}}</style><g>{dots}</g></svg>')


CARD_H = 68
CARD_GAP = 8   # every metric card starts with this much empty space, so cards placed edge to edge look separated
SUGGESTION_TONES = {   # light (fill, text, icon), dark (fill, text, icon): a faint tint, near-black or near-white text, a toned icon
    "not-safe": (("#fdeceb", "#5f1410", "#c5281f"), ("#3a1c1c", "#ffe9e6", "#ff8379")),
    "consider": (("#fff4dc", "#4a3200", "#a66b00"), ("#33290f", "#fff3d6", "#f0b840")),
    "safe": (("#e6f6ee", "#0b3d2e", "#12805d"), ("#12301f", "#e2f8ec", "#5fd69f")),
}
VALUE_INKS = {"red": ("#c5281f", "#ff8379"), "amber": ("#a66b00", "#f0b840"), "green": ("#12805d", "#5fd69f"), "neutral": ("#1f2328", "#f0f6fc")}


def _card_icon(icon: str, x: float, y: float, size: float) -> str:
    shapes = "".join(f"<{tag} {_attrs(a)}/>" for tag, a in ICONS[icon])
    return (f'<g transform="translate({_num(x)} {_num(y)}) scale({_num(size / 24)})" fill="none" class="i" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{shapes}</g>')


def suggestion_card(label: str, detail: str, icon: str, tone: str) -> str:
    """The merge suggestion card: a faint tint with a label and its reason. Like every card it has no viewBox and a
    100% width, so the fill stretches to the width the page gives the image while the content keeps its drawn size."""
    (light_fill, light_text, light_icon), (dark_fill, dark_text, dark_icon) = SUGGESTION_TONES[tone]
    css = (f"<style>.f{{fill:{light_fill}}}.t{{fill:{light_text}}}.i{{stroke:{light_icon}}}"
           f"@media (prefers-color-scheme:dark){{.f{{fill:{dark_fill}}}.t{{fill:{dark_text}}}.i{{stroke:{dark_icon}}}}}</style>")
    title, _ = text_path(label, 15, 42, "SemiBold", CARD_H)
    sub, _ = text_path(detail, 12, 42, "Regular", CARD_H)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{CARD_H}">{css}<rect width="100%" height="{CARD_H}" rx="8" class="f"/>'
            f'{_card_icon(icon, 14, (CARD_H - 20) / 2, 20)}'
            f'<path d="{title}" class="t" transform="translate(0 -9.5)"/><path d="{sub}" class="t" transform="translate(0 10)"/></svg>')


def metric_card(label: str, value: str, icon: str, tone: str = "neutral") -> str:
    """A metric card: a small label over one large value. It starts with CARD_GAP of empty space."""
    light_ink, dark_ink = VALUE_INKS[tone]
    css = (f"<style>.f{{x:{CARD_GAP}px;width:calc(100% - {CARD_GAP}px);fill:#f3f4f6}}.l{{fill:#59636e}}.v{{fill:{light_ink}}}.i{{stroke:#59636e}}"
           f"@media (prefers-color-scheme:dark){{.f{{fill:#1c2128}}.l{{fill:#9198a1}}.v{{fill:{dark_ink}}}.i{{stroke:#9198a1}}}}</style>")
    left = CARD_GAP + 14
    name, _ = text_path(label, 11.5, left + 20, "Regular", CARD_H)
    number, _ = text_path(value, 20, left, "SemiBold", CARD_H)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{CARD_H}">{css}<rect width="100%" height="{CARD_H}" rx="8" class="f"/>'
            f'{_card_icon(icon, left, 11.5, 14)}'
            f'<path d="{name}" class="l" transform="translate(0 -15.5)"/><path d="{number}" class="v" transform="translate(0 10)"/></svg>')
