"""Draw a finding title chip, a section label, a reference chip and a text card as SVG. Pure functions: text in, SVG out."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generator"))
from chips import CHIP_TOP_PAD, H, _font, _num, lucide, text_path  # noqa: E402

MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'
SANS = 'system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
LIGHT = {"chip": "#f4f4f4", "ink": "#1c1c1c", "muted": "#6e7781", "card": "#f6f8fa", "line": "#d0d7de", "text": "#1f2328", "idbg": "#e3e6ea", "edge": "#d0d4d9", "link": "#0969da"}
DARK = {"chip": "#3d3d3d", "ink": "#f4f4f4", "muted": "#9aa2ab", "card": "#161b22", "line": "#30363d", "text": "#e6edf3", "idbg": "#343a43", "edge": "#4b515a", "link": "#4493f8"}
LINK_ICONS = {"file": "file-text", "rule": "book-marked", "ticket": "clipboard-check", "web": "external-link", "pr": "git-pull-request"}
TITLE_SIZE = 12.5
IMAGE_HEIGHT = H + CHIP_TOP_PAD   # same box as the static chips, so titles and labels line up with them
SECTION_ICONS = {"description": "text-align-start", "code": "code", "evidence": "search", "agent-prompt": "bot", "relevance": "info"}
PROSE_SIZE, CARD_PAD, CARD_LINE = 13, 16, 22
NAME_SIZE, NAME_PAD = 12, 5
NAME_CHAR_W = NAME_SIZE * 0.6     # every monospace glyph is drawn at this width (textLength pins it)
MAX_WORD = 60                     # longer words are split so they cannot overflow the card
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


def render_link(text: str, icon: str = "") -> str:
    """A reference chip, e.g. a file path or a rule id: outlined, link-coloured icon and text. Wrap it in a link."""
    x, body = 8.0, ""
    if icon in LINK_ICONS:
        body, x = lucide(LINK_ICONS[icon], x, 'class="s"', 12), x + 12 + 5
    try:
        d, w = text_path(text, 11.5, x)
        run = f'<path d="{d}" class="t"/>'
    except KeyError:
        w = len(text) * 11.5 * 0.58
        run = (f'<text x="{_num(x)}" y="{_num(H / 2 + 4.1)}" font-family=\'{SANS}\' font-size="11.5" textLength="{_num(w)}" '
               f'lengthAdjust="spacingAndGlyphs" class="t">{escape(text)}</text>')
    width = round(x + w + 9)
    frame = f'<rect x="0.5" y="0.5" width="{width - 1}" height="{H - 1}" rx="5.5" fill="none" class="o"/>'
    return _chip_height_svg(width, _css({"o": "stroke:{edge}", "s": "stroke:{link}", "t": "fill:{link}"}) + frame + body + run)


def _prose_word(word: str, x: float, y: float, glyphs_used: dict[str, str]) -> tuple[str, float]:
    """One prose word in Inter. Each glyph shape is defined once and reused, which keeps a long card small."""
    _, glyphs, cmap, hmtx, upm, _ = _font("Regular")
    scale = PROSE_SIZE / upm
    if any(ord(ch) not in cmap for ch in word):
        w = len(word) * PROSE_SIZE * 0.56
        return (f'<text x="{_num(x)}" y="{_num(y)}" font-family=\'{SANS}\' font-size="{PROSE_SIZE}" textLength="{_num(w)}" '
                f'lengthAdjust="spacingAndGlyphs" class="t">{escape(word)}</text>'), w
    out, cursor = "", x
    for ch in word:
        name = cmap[ord(ch)]
        if name not in glyphs_used:
            pen = SVGPathPen(glyphs, ntos=_num)
            glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, 0, 0)))
            glyphs_used[name] = f'<path id="g{len(glyphs_used)}" d="{pen.getCommands()}"/>'
        glyph_id = glyphs_used[name].split('"', 2)[1]
        out += f'<use href="#{glyph_id}" x="{_num(cursor)}" y="{_num(y)}"/>'
        cursor += hmtx[name][0] * scale
    return f'<g class="t">{out}</g>', cursor - x


def _tokens(paragraph: str) -> list[tuple[str, bool, bool]]:
    """(text, is highlighted name, glued to the previous token). Punctuation after a `name` stays attached to it."""
    out: list[tuple[str, bool, bool]] = []
    end = 0
    for match in _TOKEN.finditer(paragraph):
        out.append((match.group(1) or match.group(2), bool(match.group(1)), bool(out) and match.start() == end))
        end = match.end()
    return out


def render_card(text: str, width: int = 760) -> str:
    """A text card: prose in Inter, `backticked` names in monospace on a rounded tint. Text is wrapped to `width` here, not by the reader's browser."""
    _, _, cmap, hmtx, upm, _ = _font("Regular")
    space = hmtx[cmap[ord(" ")]][0] * PROSE_SIZE / upm
    limit, glyphs_used, body = width - CARD_PAD, {}, ""
    x, row = float(CARD_PAD), 0
    for paragraph in text.replace("\r\n", "\n").strip("\n").split("\n"):
        for word, is_name, glued in _tokens(paragraph):
            for start in range(0, len(word), MAX_WORD):
                piece = word[start:start + MAX_WORD]
                w = len(piece) * NAME_CHAR_W + 2 * NAME_PAD if is_name else _prose_word(piece, 0, 0, {})[1]
                gap = 0 if x == CARD_PAD or (glued and start == 0) else space
                if x > CARD_PAD and x + gap + w > limit:
                    x, row, gap = float(CARD_PAD), row + 1, 0
                x += gap
                y = CARD_PAD + PROSE_SIZE + row * CARD_LINE - 1.5
                if is_name:
                    body += (f'<rect x="{_num(x)}" y="{_num(y - NAME_SIZE - 2.5)}" width="{_num(w)}" height="{_num(NAME_SIZE + 8)}" rx="6" class="b"/>'
                             f'<text x="{_num(x + NAME_PAD)}" y="{_num(y - 0.3)}" font-family=\'{MONO}\' font-size="{NAME_SIZE}" '
                             f'font-weight="600" textLength="{_num(w - 2 * NAME_PAD)}" lengthAdjust="spacingAndGlyphs" class="t">{escape(piece)}</text>')
                else:
                    body += _prose_word(piece, x, y, glyphs_used)[0]
                x += w
        x, row = float(CARD_PAD), row + 1
    height = 2 * CARD_PAD + CARD_LINE * row - (CARD_LINE - PROSE_SIZE) + 1
    out = _css({"k": "fill:{card};stroke:{line}", "t": "fill:{text}", "b": "fill:{idbg}"})
    out += f'<defs>{"".join(glyphs_used.values())}</defs>'
    out += f'<rect x="0.5" y="0.5" width="{width - 1}" height="{_num(height - 1)}" rx="8" class="k"/>'
    return _svg(width, height, out + body)
