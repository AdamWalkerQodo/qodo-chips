"""Draw a finding title chip, a section label and a monospace text card as SVG. Pure functions: text in, SVG out."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generator"))
from chips import CHIP_TOP_PAD, H, _num, lucide, text_path  # noqa: E402

MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'
SANS = 'system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
LIGHT = {"chip": "#f4f4f4", "ink": "#1c1c1c", "muted": "#6e7781", "card": "#f6f8fa", "line": "#d0d7de", "text": "#1f2328", "idbg": "#e3e6ea", "edge": "#d0d4d9"}
DARK = {"chip": "#3d3d3d", "ink": "#f4f4f4", "muted": "#9aa2ab", "card": "#161b22", "line": "#30363d", "text": "#e6edf3", "idbg": "#343a43", "edge": "#4b515a"}
TITLE_SIZE = 12.5
IMAGE_HEIGHT = H + CHIP_TOP_PAD   # same box as the static chips, so titles and labels line up with them
SECTION_ICONS = {"description": "text-align-start", "code": "code", "evidence": "search", "agent-prompt": "bot", "relevance": "info"}
CARD_SIZE, CARD_PAD, CARD_LINE = 12.5, 16, 21
CHAR_W = CARD_SIZE * 0.6          # every monospace glyph is drawn at this width (textLength pins it)
_TOKEN = re.compile(r"`([^`\n]+)`|(\S+)")


def _css(rules: dict[str, str]) -> str:
    """rules: class -> "property:{palette key}". One stylesheet holding the light palette and a dark media query."""
    def block(pal: dict[str, str]) -> str:
        return "".join(f".{name}{{{rule.format(**pal)}}}" for name, rule in rules.items())
    return f"<style>{block(LIGHT)}@media (prefers-color-scheme:dark){{{block(DARK)}}}</style>"


def _svg(width: float, height: float, body: str) -> str:
    w, h = _num(width), _num(height)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def _run(text: str, x: float, weight: str, css_class: str) -> tuple[str, float]:
    """One run of label text: Inter outlines, or system text at an estimated width when Inter lacks a character."""
    try:
        d, w = text_path(text, TITLE_SIZE, x, weight)
        return f'<path d="{d}" class="{css_class}"/>', w
    except KeyError:
        w = len(text) * TITLE_SIZE * 0.58
        bold = ' font-weight="600"' if weight == "SemiBold" else ""
        return (f'<text x="{_num(x)}" y="{_num(H / 2 + TITLE_SIZE * 0.36)}" font-family=\'{SANS}\' font-size="{TITLE_SIZE}"{bold} '
                f'textLength="{_num(w)}" lengthAdjust="spacingAndGlyphs" class="{css_class}">{escape(text)}</text>'), w


def _chip_height_svg(width: float, body: str) -> str:
    return _svg(width, IMAGE_HEIGHT, f'<g transform="translate(0 {CHIP_TOP_PAD})">{body}</g>')


def render_title(title: str, number: str = "") -> str:
    """The finding title as an outlined chip the height of the static chips; `number` is drawn muted in front of it."""
    x, body = 9.0, ""
    if number:
        run, w = _run(f"{number}.", x, "Regular", "n")
        body, x = body + run, x + w + 5
    run, w = _run(title, x, "SemiBold", "t")
    width = round(x + w + 10)
    frame = f'<rect x="0.5" y="0.5" width="{width - 1}" height="{H - 1}" rx="5.5" fill="none" class="o"/>'
    return _chip_height_svg(width, _css({"o": "stroke:{edge}", "n": "fill:{muted}", "t": "fill:{ink}"}) + frame + body + run)


def render_label(text: str, icon: str = "") -> str:
    """A section label, e.g. Description: an icon and a word, no frame, the height of the static chips."""
    x, body = 1.0, ""
    if icon in SECTION_ICONS:
        body, x = lucide(SECTION_ICONS[icon], x, 'class="s"', 13), x + 13 + 6
    run, w = _run(text, x, "SemiBold", "t")
    return _chip_height_svg(round(x + w + 2), _css({"s": "stroke:{muted}", "t": "fill:{ink}"}) + body + run)


def _words(paragraph: str, max_cols: int) -> list[tuple[str, bool, bool]]:
    """(text, is highlighted name, glued to the previous word). Punctuation after a `name` stays attached to it."""
    out: list[tuple[str, bool, bool]] = []
    end = 0
    for match in _TOKEN.finditer(paragraph):
        word, is_name = match.group(1) or match.group(2), bool(match.group(1))
        glued = bool(out) and match.start() == end
        for start in range(0, len(word), max_cols):
            out.append((word[start:start + max_cols], is_name, glued and start == 0))
        end = match.end()
    return out


def _wrap(text: str, max_cols: int) -> list[list[tuple[int, str, bool]]]:
    """Lines of (column, word, is highlighted name). A blank line in the text gives an empty line."""
    lines: list[list[tuple[int, str, bool]]] = []
    for paragraph in text.replace("\r\n", "\n").split("\n"):
        line: list[tuple[int, str, bool]] = []
        col = 0
        for word, is_name, glued in _words(paragraph, max_cols):
            gap = 0 if glued or not line else 1
            if line and col + gap + len(word) > max_cols:
                lines.append(line)
                line, col, gap = [], 0, 0
            line.append((col + gap, word, is_name))
            col += gap + len(word)
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return lines or [[]]


def render_card(text: str, width: int = 760) -> str:
    """A monospace text card; `backticked` names are highlighted. Text is wrapped to `width` here, not by the reader's browser."""
    lines = _wrap(text, int((width - 2 * CARD_PAD) / CHAR_W))
    height = 2 * CARD_PAD + CARD_LINE * len(lines) - (CARD_LINE - CARD_SIZE) + 2
    out = _css({"k": "fill:{card};stroke:{line}", "t": "fill:{text}", "b": "fill:{idbg}"})
    out += f'<rect x="0.5" y="0.5" width="{width - 1}" height="{_num(height - 1)}" rx="8" class="k"/>'
    out += f'<g font-family=\'{MONO}\' font-size="{CARD_SIZE}">'
    for row, items in enumerate(lines):
        y = CARD_PAD + CARD_SIZE + row * CARD_LINE - 1
        for col, word, is_name in items:
            x, w = CARD_PAD + col * CHAR_W, len(word) * CHAR_W
            if is_name:
                out += f'<rect x="{_num(x - 4)}" y="{_num(y - CARD_SIZE - 1.5)}" width="{_num(w + 8)}" height="{_num(CARD_SIZE + 7)}" rx="7" class="b"/>'
            out += (f'<text x="{_num(x)}" y="{_num(y)}" textLength="{_num(w)}" lengthAdjust="spacingAndGlyphs" '
                    f'class="t"{" font-weight=\"600\"" if is_name else ""}>{escape(word)}</text>')
    return _svg(width, height, out + "</g>")
