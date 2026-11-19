"""Draw a finding title chip, a section label, a reference chip and a text card as SVG. Pure functions: text in, SVG out."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generator"))
from chips import CHIP_TOP_PAD, ICONS, H, _font, _num, chip, lucide, pill, text_path  # noqa: E402

MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'
SANS = 'system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
LIGHT = {"bar": "#f6f8fa", "soft": "#eaeef2", "inner": "#e4e8ec", "chip": "#f4f4f4", "ink": "#1c1c1c", "muted": "#6e7781", "card": "#f6f8fa", "line": "#d0d7de", "text": "#1f2328", "idbg": "#e3e6ea", "edge": "#d0d4d9", "link": "#0969da"}
DARK = {"bar": "#21262d", "soft": "#21262d", "inner": "#30363d", "chip": "#3d3d3d", "ink": "#f4f4f4", "muted": "#9aa2ab", "card": "#161b22", "line": "#30363d", "text": "#e6edf3", "idbg": "#343a43", "edge": "#4b515a", "link": "#4493f8"}
LINK_ICONS = {"file": "file-text", "rule": "book-marked", "ticket": "clipboard-check", "web": "external-link", "pr": "git-pull-request"}
TITLE_SIZE = 12.5
BAR_HEIGHT, BAR_PAD, BAR_GAP = 36, 12, 6
BAR_MARGIN = 4                    # transparent rows above and below the bar, so stacked findings do not touch
BAR_TITLE_SIZE = 14
PILL_COLORS = {"red": "#ce2c31", "orange": "#e36209", "yellow": "#d4a72c", "brand": "#634fd1", "gray": "#3d3d3d"}
IMAGE_HEIGHT = H + CHIP_TOP_PAD   # same box as the static chips, so titles and labels line up with them
SECTION_ICONS = {"description": "text-align-start", "code": "code", "evidence": "search", "agent-prompt": "bot", "relevance": "info"}
PROSE_SIZE, CARD_PAD, CARD_LINE = 14, 16, 23
NAME_SIZE, NAME_PAD = 12.5, 5
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


def _run(text: str, x: float, weight: str, css_class: str, size: float = TITLE_SIZE) -> tuple[str, float]:
    """One run of label text: Inter outlines, or system text at an estimated width when Inter lacks a character."""
    try:
        d, w = text_path(text, size, x, weight)
        return f'<path d="{d}" class="{css_class}"/>', w
    except KeyError:
        w = len(text) * size * 0.58
        bold = ' font-weight="600"' if weight == "SemiBold" else ""
        return (f'<text x="{_num(x)}" y="{_num(H / 2 + size * 0.36)}" font-family=\'{SANS}\' font-size="{size}"{bold} '
                f'textLength="{_num(w)}" lengthAdjust="spacingAndGlyphs" class="{css_class}">{escape(text)}</text>'), w


def _chip_height_svg(width: float, body: str, pad_top: int = 0) -> str:
    """A chip-height image; `pad_top` adds transparent rows above it, which is how spacing is set inside a comment."""
    return _svg(width, IMAGE_HEIGHT + pad_top, f'<g transform="translate(0 {CHIP_TOP_PAD + pad_top})">{body}</g>')


def _namespaced(body: str, suffix: str) -> str:
    """Rename a chip's style classes, so several chips can share one SVG without their colours clashing."""
    body = re.sub(r"\.([a-z])\{", lambda m: f".{m.group(1)}{suffix}{{", body)
    return re.sub(r'class="([a-z])"', lambda m: f'class="{m.group(1)}{suffix}"', body)


def _inner_chip(spec: str, index: int) -> tuple[str, float]:
    """A chip drawn inside the title bar. spec: "pill|<colour>|<label>" or "chip|<icon>|<label>|<mono or color>"."""
    kind, _, rest = spec.partition("|")
    parts = rest.split("|")
    if kind == "pill" and len(parts) == 2 and parts[0] in PILL_COLORS:
        return pill(parts[1][:40], PILL_COLORS[parts[0]])
    if kind == "chip" and len(parts) == 3 and parts[0] in ICONS and parts[2] in ("mono", "color"):
        body, w = chip(parts[0], parts[1][:40], None, parts[2], "auto")
        fill = f".fx{index}{{{{fill:{{inner}}}}}}"
        override = f"<style>{fill.format(**LIGHT)}@media (prefers-color-scheme:dark){{{fill.format(**DARK)}}}</style>"
        return _namespaced(body, f"x{index}") + override, w
    raise ValueError(f"unknown chip: {spec}")


def render_title(title: str, number: str = "", chips: list[str] | None = None, width: int = 0) -> str:
    """The finding title as a bordered bar with its chips inside, on the right. `width` 0 fits the content."""
    inner = [_inner_chip(spec, index) for index, spec in enumerate(chips or [])]
    chips_w = sum(w for _, w in inner) + BAR_GAP * len(inner)
    x, body = float(BAR_PAD), ""
    if number:
        run, w = _run(f"{number}.", x, "Regular", "n", BAR_TITLE_SIZE)
        body, x = body + run, x + w + 6
    room = width - x - chips_w - BAR_PAD - 12 if width else 10 ** 6
    while len(title) > 4 and _run(title, x, "SemiBold", "t", BAR_TITLE_SIZE)[1] > room:
        title = title[:-2].rstrip() + "…"
    run, w = _run(title, x, "SemiBold", "t", BAR_TITLE_SIZE)
    width = width or round(x + w + 12 + chips_w + BAR_PAD)
    out = _css({"c": "fill:{bar};stroke:{line}", "n": "fill:{muted}", "t": "fill:{ink}"})
    out += f'<g transform="translate(0 {BAR_MARGIN})"><rect x="0.5" y="0.5" width="{width - 1}" height="{BAR_HEIGHT - 1}" rx="7.5" class="c"/>'
    out += f'<g transform="translate(0 {_num((BAR_HEIGHT - H) / 2)})">{body}{run}'
    cursor = width - BAR_PAD - chips_w + BAR_GAP
    for chip_body, chip_w in inner:
        out += f'<g transform="translate({_num(cursor)} 0)">{chip_body}</g>'
        cursor += chip_w + BAR_GAP
    return _svg(width, BAR_HEIGHT + 2 * BAR_MARGIN, out + "</g></g>")


def render_label(text: str, icon: str = "") -> str:
    """A section label, e.g. Description: an icon and a word on a filled chip, the height of the static chips."""
    x, body = 8.0, ""
    if icon in SECTION_ICONS:
        body, x = lucide(SECTION_ICONS[icon], x, 'class="s"', 12.5), x + 12.5 + 6
    run, w = _run(text, x, "SemiBold", "t")
    width = round(x + w + 10)
    frame = f'<rect width="{width}" height="{H}" rx="6" class="c"/>'
    return _chip_height_svg(width, _css({"c": "fill:{soft}", "s": "stroke:{muted}", "t": "fill:{ink}"}) + frame + body + run)


def render_note(text: str, pad_top: int = 0) -> str:
    """A quiet one-line note: an info icon and muted text, no frame."""
    body = lucide("info", 1, 'class="s"', 12)
    run, w = _run(text, 18, "Regular", "n", 11.5)
    return _chip_height_svg(round(18 + w + 2), _css({"s": "stroke:{muted}", "n": "fill:{muted}"}) + body + run, pad_top)


def render_link(text: str, icon: str = "", pad_top: int = 0) -> str:
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
    return _chip_height_svg(width, _css({"o": "stroke:{edge}", "s": "stroke:{link}", "t": "fill:{link}"}) + frame + body + run, pad_top)


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


def render_card(text: str, width: int = 760, pad_top: int = 0) -> str:
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
    out = _css({"k": "fill:{card}", "t": "fill:{text}", "b": "fill:{idbg}"})
    out += f'<defs>{"".join(glyphs_used.values())}</defs>'
    out += f'<rect width="{width}" height="{_num(height)}" rx="6" class="k"/>'
    return _svg(width, height + pad_top, f'<g transform="translate(0 {pad_top})">{out}{body}</g>')
