"""v7: v5 (no customer text in images) with pieces that stretch with the comment column, so it fits windows down to ~1,050px.

Widths are percentages of the column; side-line heights are estimated for the narrowest column (FIT_W), so wider windows get
spare room under the text instead of borders that stop short. Uses the engine's sample findings, like build_real_findings.py."""
import html
import json
import math
import os
import re
import sys
from urllib.parse import quote

import comment_layout
from comment_layout import LINE, PROSE_CHAR, SERVER, STATIC, V, Box, block, picture, static_chip

SAMPLES = "/Users/adamwalker/Developer/Qodo Features/PR-Agent/.claude/worktrees/pr-agent-image-chips/pr_agent/algo/agents/ux/mocks/findings/mock_findings.json"
SEV = {"action_required": ("action-required", "High"), "remediation_recommended": ("remediation-recommended", "Medium"), "informational": ("informational", "Low")}
TYPE = {"IssueFinding": ("bugs", "Bug"), "ComplianceRule": ("rule-violations", "Rule violation")}
STRENGTH = {"yes": ("strong", "Strong"), "maybe": ("moderate", "Moderate"), "no": ("weak", "Weak")}
PICK = [0, 1, 3, 6, 7, 10]


FLOAT_PAD = 20  # GitHub pads a floated image by this much on its inner side
LP = 3.0        # where the container starts, in percent of the column; the room left of it holds the fold arrow (>= 15px at FIT_W)
SIDE_W = 3.1    # width of the left side line's image in percent: the line sits LP percent in
FIT_W = 530     # narrowest comment column the side-line heights are estimated for (a ~900px window)
BAND_H = 36     # height of a band's own image; the band continues HANG px below it
HANG = 16       # the empty space GitHub leaves under every fold. A strip this tall hangs out of the <summary> and fills it
TITLE_SPACE = 10  # space between the finding title and the first band
PAD = 16        # space above unfolded content
SLACK = 4       # how far the side lines run past the estimated end of the content, so a low estimate does not leave them short
PARAGRAPH_GAP = 16  # under every paragraph; when the closing pieces sit inside the last paragraph, its gap comes after them
TAB_TOP = 8     # the drawn top of a code block's title tab; the title is a native line under it
INNER = FIT_W - round(FIT_W * SIDE_W / 100) - FLOAT_PAD - (1 + FLOAT_PAD)   # room between the side lines in the narrowest column
comment_layout.INNER_W = INNER      # text height is estimated for this width
# The sections sit in a right-aligned block: the fold arrow and the band share a line that is pushed against the right edge,
# so the band lands in the same place whatever the width of the arrow (12px to 15px, by browser and display).
RIGHT, LEFT, END = '<div align="right">', '<div align="left">', "</div>"


def band(heading: str, icon: str, subtitle: str = "", first: bool = False, chip: str = "") -> str:
    """A section's header band: the fold's clickable title, on one line with the fold arrow to its left.

    Only the first band draws a line above itself; every other line between sections comes from the piece that ends the section
    before. The image hangs from the bottom of its text line (absbottom), which puts the arrow level with the band's title."""
    extra = f"&c={quote(chip)}" if chip else ""
    top = TITLE_SPACE if first else 0
    src = (f"{SERVER}/header.svg?v={V}&fluid=true&hang={HANG}&bh={BAND_H}&top={'true' if first else 'false'}&pt={top}{extra}"
           f"&i={icon}&t={quote(heading)}&s={quote(subtitle)}")
    return picture(src, heading + (": " + subtitle if subtitle else ""), f'width="{100 - LP}%" height="{BAND_H + top}" align="absbottom"')


def edge(kind: str, height: int, **params: float) -> str:
    extra = "".join(f"&{key}={value}" for key, value in params.items())
    return f"{SERVER}/edge.svg?v={V}&fluid=true&kind={kind}&h={height}{extra}"


def strip(kind: str, height: int) -> str:
    """A full-width piece of the container, floated. Nothing fits beside it, so it lands under whatever came before, and whatever
    comes next lands under it: the pieces join exactly, with no line of text (21px) forcing a minimum height."""
    return picture(edge(kind, height, lp=LP), "", f'width="100%" height="{height}" align="left"')


def closing() -> str:
    """The end of an unfolded section: a full-width image in the text flow, which cannot sit beside the side lines, so it lands
    under them and the next fold starts below every float (its arrow stays on its band); it carries the side lines for one line.
    Then the closing edge, floated, hangs into the 16px GitHub leaves under the fold, where the next band starts."""
    return picture(edge("gap", 21, lp=LP), "", 'width="100%" height="21" align="top"') + strip("close", HANG)


def side_lines(height: int) -> str:
    """The container's two side lines as images floated left and right."""
    left = picture(edge("lside", height, lp=round(100 * LP / SIDE_W, 2)), "", f'width="{SIDE_W}%" height="{height}" align="left"')
    return left + picture(f"{SERVER}/edge.svg?v={V}&kind=side&h={height}", "", f'width="1" height="{height}" align="right"')


ICON_W = 16 + 4   # an icon image and the space after it


def icon(name: str) -> str:
    """A reference icon with no text, in front of a native link."""
    return picture(f"{SERVER}/icon.svg?v={V}&i={name}", "", 'width="16" height="21" align="top"')


def lines_for(width: float) -> int:
    return max(1, math.ceil(width / INNER))


def native_title(n: int, text: str, chips: list[tuple[str, str]]) -> str:
    """The finding title as comment text, then its chips."""
    return f"<b>{n}. {html.escape(text)}</b> " + " ".join(static_chip(path, alt) for path, alt in chips)


class Parts(Box):
    """A section's content in parts: rows that run between one pair of side lines, and title tabs that carry their own borders."""

    def __init__(self, head: str) -> None:
        super().__init__(head)
        self.parts: list[tuple[str, list[str], float]] = []

    def bar(self, markup: str) -> "Parts":
        self.flush()
        self.parts.append(("bar", [markup], 0.0))
        return self

    def flush(self) -> None:
        if self.rows:
            self.parts.append(("rows", self.rows, self.height))
        self.rows, self.height = [], 0.0


def tab_side(align: str) -> str:
    return picture(f"{SERVER}/edge.svg?v={V}&kind=side&h={LINE}", "", f'width="1" height="{LINE}" align="{align}"')


def file_line(box: Parts, label: str, url: str) -> Parts:
    """A code excerpt's file and line range as a tab on top of the block: the tab's top is drawn, its title is a native line between
    the container's side lines and the tab's own 1px sides, and the code block starts right under it."""
    match = re.match(r"^(.*?)\s*\[(.+)\]$", label)
    path, span = (match.group(1), match.group(2)) if match else (label, "")
    room = int((INNER - (1 + FLOAT_PAD) - (34 + FLOAT_PAD) - ICON_W) / 8) - len(span) - 3   # one line in the narrowest column, leaning short
    path = path if len(path) <= room else "…" + path[-(room - 1):]
    top = picture(edge("tab", TAB_TOP, lp=LP, bl=SIDE_W), "", f'width="100%" height="{TAB_TOP}" align="left"')
    left = picture(edge("lside", LINE, lp=round(100 * LP / SIDE_W, 2)), "", f'width="{SIDE_W}%" height="{LINE}" align="left"')
    right = picture(f"{SERVER}/edge.svg?v={V}&kind=side&h={LINE}", "", f'width="1" height="{LINE}" align="right"')
    title = f'{icon("file")} <a href="{url}">{html.escape(path)}{" [" + html.escape(span) + "]" if span else ""}</a>'
    end = f'<a href="{url}">' + picture(f"{SERVER}/edge.svg?v={V}&kind=tabend&h={LINE}", "Open file", f'width="34" height="{LINE}" align="right"') + "</a>"
    bottom = picture(edge("tabbottom", TAB_TOP, lp=LP, bl=SIDE_W), "", f'width="100%" height="{TAB_TOP}" align="left"')
    # One block, in this order: floats cannot start above an earlier float, so the title line lands under the tab's top and the
    # tab's bottom under the title line; the code block, which keeps clear of floats, starts under that.
    return box.bar(f"<div>{top}{left}{tab_side('left')}{right}{end}{title}{bottom}</div>")


FILE_HEADER = os.environ.get("FILE_HEADER", "image")   # "image": drawn bar with generic text; "filled": GitHub's <pre> box; "outlined": drawn tab
FILEBAR_H = 32


def excerpt(box: Parts, label: str, url: str, lines: list[str], language: str = "") -> Parts:
    """A code excerpt under a file header, in the style FILE_HEADER picks."""
    if FILE_HEADER == "image":
        if language == "diff":   # git's own file header; the hunk line under it already gives the line range
            path = re.sub(r"\s*\[[^\]]*\]$", "", label)
            label = f"diff --git a/{path} b/{path}"
        return image_file_line(box, label, url).code([label, "", *lines], language)   # a blank line sets the file line apart
    return (filled_file_line if FILE_HEADER == "filled" else file_line)(box, label, url).code(lines, language)


def image_file_line(box: Parts, label: str, url: str) -> Parts:
    """The drawn title strip on top of a code block, with only "View file" in it, so no customer text is drawn; the file and
    line range are the code block's first line instead. It is a full-width image that carries the container's borders, in the
    text flow, so it lands under whatever side lines run before it and the code block starts right under it."""
    src = f"{SERVER}/filebar.svg?v={V}&fluid=true&lp={LP}&bl={SIDE_W}&t={quote('View file')}"
    image = f'<img src="{src}" width="100%" height="{FILEBAR_H}" align="top" alt="View file">'
    return box.bar(f'<div><a href="{url}">{image}</a></div>')


FILLED_H = 32 + LINE + 16   # the <pre> box: 16px padding above and below one line, then its 16px bottom margin


def filled_file_line(box: Parts, label: str, url: str) -> Parts:
    """A code excerpt's file and line range in a filled bar: GitHub's own <pre> box, the only native element that paints a
    background behind text. It takes the code block's color, and GitHub keeps 16px between it and the code."""
    match = re.match(r"^(.*?)\s*\[(.+)\]$", label)
    path, span = (match.group(1), match.group(2)) if match else (label, "")
    room = int((INNER - 32 - ICON_W - 16 - FLOAT_PAD) / 8) - len(span) - 3
    path = path if len(path) <= room else "…" + path[-(room - 1):]
    arrow = f'<a href="{url}">' + picture(f"{SERVER}/icon.svg?v={V}&i=open", "Open file", f'width="16" height="{LINE}" align="right"') + "</a>"
    title = f'{icon("file")} <a href="{url}">{html.escape(path)}{" [" + html.escape(span) + "]" if span else ""}</a>'
    box.rows += [f"<pre>{arrow}{title}</pre>", ""]
    box.height += FILLED_H
    return box


def pr_button(number: int, url: str) -> str:
    """A past PR in the suggestion panel's outlined square button style; a PR number is not sensitive, so it can be drawn."""
    src = f"{SERVER}/link.svg?v={V}&square=true&i=pr&t={quote(f'PR-#{number}')}"
    return f'<a href="{url}"><img src="{src}" height="28" align="top" alt="PR-#{number}"></a>'


def ref_line(box: Parts, kind: str, text: str, url: str) -> Parts:
    """A rule or ticket as a native line: icon, then the linked name."""
    return box.line(f'{icon(kind)} <a href="{url}">{html.escape(text)}</a>', lines_for(ICON_W + len(text) * PROSE_CHAR))


def section(box: Box, tail: str = "margin", is_open: bool = False) -> list[str]:
    """One foldable section inside the container, with no gap before the next one.

    GitHub puts 16px of empty space under every fold. A strip of the band's fill hangs out of the <summary> into that space, so a folded
    section is one solid band that touches the next. Unfolded content sits between floated side lines and ends with a closing piece.
    The next band starts 16px under the content unless the closing piece reaches further down and pushes it, so the piece must reach
    at least that far. How tall that makes it depends on what the content ends with (`tail`, see CLOSE)."""
    box.flush()
    out = [f'<details{" open" if is_open else ""}><summary>{box.head}{strip("fill", HANG)}</summary>', "", LEFT, ""]
    for index, (kind, rows, height) in enumerate(box.parts):
        gap = strip("gap", PAD) if index == 0 else ""
        if kind == "bar":
            out += ([f"<div>{gap}</div>", ""] if gap else []) + [rows[0], ""]
            continue
        rows, last = list(rows), index == len(box.parts) - 1
        if last and rows and not rows[-2].startswith(("```", "<div")):
            rows[-2] += " " + closing()      # inside the last paragraph: its bottom margin then falls under the closing edge
            height -= PARAGRAPH_GAP
        elif last:
            rows += ["<div>" + closing() + "</div>", ""]
        out += ["<div>" + gap + side_lines(round(height) + SLACK) + "</div>", "", *rows]
    if box.parts and box.parts[-1][0] == "bar":
        out += ["<div>" + closing() + "</div>", ""]
    return out + [END, "", "</details>", ""]


def footer(dismiss_url: str, view_url: str) -> list[str]:
    """The bottom of the container: the two actions in the suggestion panel's square button style, then the closing edge."""
    def button(key: str, label: str, url: str) -> str:
        return f'<a href="{url}"><img src="{STATIC}/button/straight/{key}.svg?v={V}" height="28" align="top" alt="{label}"></a>'
    buttons = [button("dismiss-finding", "Dismiss finding", dismiss_url), button("view-in-qodo", "View in Qodo", view_url)]
    close = picture(edge("close", 21, lp=LP), "", 'width="100%" height="21" align="top"')   # 21px: a line of text is that tall
    return ["<div>" + strip("gap", PAD) + side_lines(29) + "</div>", "", block(*buttons), "", block(close)]


def finding(n: int, f: dict, files_url: str) -> list[str]:
    sev, sev_word = SEV[f["severity_level"]]
    kind, kind_word = TYPE[f["finding_source"]]
    category = f["category"].title()
    chips = [(f"chip/scale/severity/{sev}/high-medium-low/label", sev_word), (f"chip/color/type/{kind}/label", kind_word),
             (f"chip/mono/category/{category.lower()}/label", category)]
    out = [f"<details><summary>{native_title(n, f['finding_title'], chips)}</summary>", "", RIGHT, ""]

    out += section(Parts(band("Description", "description", first=True)).text(f["description"]), is_open=True)

    pointers = f.get("diff_pointer") or []
    pointers = pointers if isinstance(pointers, list) else [pointers]
    spans = [p.get("new_span") or p.get("old_span") or ({"start_line": p["start_line"], "end_line": p["end_line"]} if "start_line" in p else None) for p in pointers]
    ranges = [f"[{s['start_line']}-{s['end_line']}]" if s else "" for s in spans]
    code = Parts(band("Code", "code"))
    for index, snippet in enumerate(f["code_snippets"]):
        label = (f["file_path"] + " " + (ranges[index] if index < len(ranges) else "")).strip()
        excerpt(code, label, files_url, snippet.split("\n"), "diff")
    out += section(code)

    evidence = Parts(band("Evidence", "evidence")).text(f["evidence"])
    for label, excerpt_text in f.get("pr_branch_file_citations") or []:
        excerpt(evidence, label, files_url, excerpt_text.split("\n"))
    refs = [("rule", c[1], c[0] if c[0].startswith("http") else "https://docs.qodo.ai") for c in f.get("rule_citations") or []]
    refs += [("ticket", c[1], c[0]) for c in f.get("ticket_citations") or []]
    for kind, text, url in refs:
        ref_line(evidence, kind, text, url)
    out += section(evidence, "row" if refs else "plain" if f.get("pr_branch_file_citations") else "margin")

    if f.get("conversion_label"):
        key, word = STRENGTH[f["conversion_label"]]
        arcs = {"strong": 3, "moderate": 2, "weak": 1}[key]
        box = Parts(band("Relevance", "relevance", "Recommendations generated based on similar findings in past PRs", chip=f"chip|rel:{arcs}|{word}|mono"))
        box.text(f["conversion_reason"])
        prs = [pr_button(pr, f"https://github.com/adamqodo-org/excalidraw/pull/{pr}") for pr in f.get("conversion_reference_prs") or []]
        if prs:
            box.row(prs, 28)
        out += section(box, "row" if prs else "margin")

    out += section(Parts(band("Agent prompt", "agent-prompt", "Copy this prompt into your AI coding tool")).code(f["recommended_fix"].split("\n")), "plain")
    out += [END, ""] + footer(f"https://example.com/dismiss/{n}", f"https://example.com/view/{n}")
    return out + ["", "</details>", ""]


files_url = sys.argv[2] if len(sys.argv) > 2 else "https://github.com/adamqodo-org/excalidraw/pulls"
samples = json.load(open(SAMPLES))
body = ["### Code Review by Qodo", "", "Experiment (v7): v5 with pieces that stretch with the window, fitted to windows down to about 1,050px wide.", ""]
for n, index in enumerate(PICK, 1):
    body += finding(n, samples[index], files_url)
text = "\n".join(body)
open(sys.argv[1], "w").write(text)
print(len(text), "chars")
