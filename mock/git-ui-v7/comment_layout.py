"""Markup helpers for a review comment whose containers are drawn by the image server (GitHub layout)."""
import base64
import html
import zlib
from urllib.parse import quote

SERVER = "https://chips.adamwalker.io/v1"
STATIC = "https://raw.githubusercontent.com/AdamWalkerQodo/qodo-chips/main/v1"
V = "v7-3"            # ignored by the server; a new value makes git hosts fetch the image again
CARD_W = 954        # GitHub's widest comment column (986px) inside one indent; narrower columns scale the image down
PAD_LEFT = 20       # containers start this far in, so their left edge lines up with the finding title's text, not its number
INNER_W = CARD_W - PAD_LEFT - 42   # room between the two side lines: each is 1px plus GitHub's 20px beside a floated image
SECTION_GAP, TITLE_GAP = 10, 8
PROSE_CHAR, CODE_CHAR, CODE_PAD = 7.0, 7.3, 10.0   # rough px widths: 14px comment text, 11.9px inline code, padding of an inline code span
SCROLLBAR = 15
LINE, PARAGRAPH_GAP = 21, 16                        # GitHub comment text: 14px at 1.5 line height; 16px under each paragraph


def z(text: str) -> str:
    return base64.urlsafe_b64encode(zlib.compress(text.encode(), 9)).decode().rstrip("=")


def block(*images: str) -> str:
    """Images on one line inside a <div>: no paragraph margin, so the spacing drawn into the images is the only spacing."""
    return "<div>" + " ".join(images) + "</div>"


def picture(src: str, alt: str, size: str) -> str:
    """An image GitHub will not turn into a link."""
    return f'<picture><img src="{src}" {size} alt="{html.escape(alt)}"></picture>'


def static_chip(path: str, alt: str, height: int = 21) -> str:
    return picture(f"{STATIC}/{path}.svg", alt, f'height="{height}" align="absmiddle"')


def title(n: int, text: str, chips: list[tuple[str, str]]) -> str:
    """The finding title as text with no container, then its chips as separate images."""
    bar = picture(f"{SERVER}/title.svg?v={V}&frame=0&n={n}&t={quote(text)}", f"{n}. {text}", 'height="21" align="absmiddle"')
    return bar + " " + " ".join(static_chip(path, alt) for path, alt in chips)


def header(heading: str, icon: str, subtitle: str = "", url: str = "", pad_top: int = SECTION_GAP) -> str:
    """The top of a container: the header, with its side lines running on below it. With `url` the whole header is a link."""
    src = f"{SERVER}/header.svg?v={V}&pt={pad_top}&pb=16&pl={PAD_LEFT}&open_bottom=true&w={CARD_W}&i={icon}&t={quote(heading)}&s={quote(subtitle)}"
    alt = html.escape(heading + (": " + subtitle if subtitle else ""))
    image = f'<img src="{src}" width="{CARD_W}" align="top" alt="{alt}">'
    return f'<a href="{url}">{image}</a>' if url else f"<picture>{image}</picture>"


def link(icon: str, text: str, url: str, pad_top: int = 0, pad_bottom: int = 0) -> str:
    """A linked reference button. A plain <img> inside our own link, so the click follows the link."""
    src = f"{SERVER}/link.svg?v={V}&pt={pad_top}&pb={pad_bottom}&i={icon}&t={quote(text)}"
    return f'<a href="{url}"><img src="{src}" height="{28 + pad_top + pad_bottom}" align="top" alt="{html.escape(text)}"></a>'


def note(text: str, pad_top: int = 0) -> str:
    return picture(f"{SERVER}/note.svg?v={V}&pt={pad_top}&t={quote(text)}", text, f'height="{21 + pad_top}" align="top"')


def text_height(text: str, lead: float = 0.0) -> int:
    """Estimated height of `text` as GitHub comment paragraphs between the side lines; `lead` is the width of anything before the first word.

    The reader's browser wraps the text, so this is a guess from average character widths. It leans high: a line too many only adds space
    at the bottom of the container, while a line too few would leave the side lines short of the closing edge."""
    total = 0
    for paragraph in text.split("\n\n"):
        lines, x = 1, lead
        for word in paragraph.split():
            code = word.count("`") >= 2
            w = len(word.replace("`", "")) * (CODE_CHAR if code else PROSE_CHAR) + (CODE_PAD if code else 0)
            gap = PROSE_CHAR * 0.6 if x else 0
            if x and x + gap + w > INNER_W:
                lines, x, gap = lines + 1, 0.0, 0
            x += gap + w
        total, lead = total + lines * LINE + PARAGRAPH_GAP, 0.0
    return total


class Box:
    """One container: a header, then content stacked inside it. Tracks the content's height so the side lines can be drawn to fit."""

    def __init__(self, head: str) -> None:
        self.head, self.rows, self.height = head, [], 0.0

    def text(self, text: str, lead_image: str = "", lead_width: float = 0.0) -> "Box":
        """Selectable comment paragraphs; `lead_image` is put in front of the first word."""
        self.rows += [(lead_image + " " if lead_image else "") + text, ""]
        self.height += text_height(text, lead_width)
        return self

    def code(self, lines: list[str], language: str = "") -> "Box":
        """A code block: 32px padding, 17.4px per line, 16px margin under it."""
        self.rows += [f"```{language}", *lines, "```", ""]
        self.height += 32 + 17.4 * len(lines) + 16
        return self

    def line(self, content: str, lines: int = 1) -> "Box":
        """Native text (and small images) on its own line inside a <div>: no paragraph margin. `lines` is the estimated wrap count."""
        self.rows += [f"<div>{content}</div>", ""]
        self.height += LINE * lines
        return self

    def row(self, images: list[str], height: int) -> "Box":
        """One line of images, `height` px tall including any space drawn into them."""
        self.rows += [block(*images), ""]     # the blank line ends the HTML block, so a code fence after it is read as Markdown
        self.height += max(height, LINE)
        return self

    def build(self, pad_bottom: int = 0, space_after: int = 0) -> list[str]:
        height = round(self.height) + pad_bottom + 1
        side = f"{SERVER}/edge.svg?v={V}&kind=side&h={height}"
        left = picture(f"{side}&pl={PAD_LEFT}", "", f'width="{PAD_LEFT + 1}" height="{height}" align="left"')
        right = picture(side, "", f'width="1" height="{height}" align="right"')
        edge = picture(f"{SERVER}/edge.svg?v={V}&kind=bottom&w={CARD_W}&pl={PAD_LEFT}&pb={space_after}", "", f'width="{CARD_W}" align="top"')
        return [block(self.head), "<div>" + left + right + "</div>", "", *self.rows, block(edge)]


def actions(dismiss_url: str, view_url: str) -> list[str]:
    """Dismiss finding and View in Qodo, in their own Actions container."""
    def button(key: str, label: str, url: str) -> str:
        return f'<a href="{url}"><img src="{STATIC}/button/native/{key}.svg?v={V}" height="28" align="top" alt="{label}"></a>'
    buttons = [button("dismiss-finding", "Dismiss finding", dismiss_url), button("view-in-qodo", "View in Qodo", view_url)]
    return Box(header("Actions", "actions")).row(buttons, 28).build(pad_bottom=16)
