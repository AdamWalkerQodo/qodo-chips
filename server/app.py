"""Stateless image server: the request carries the text, the response is its SVG. Nothing is stored.

Run:  uvicorn server.app:app --port 8095   (from the repository root)

  GET /v1/title.svg?t=<title>&n=<number>&frame=0                      text only, no container
  GET /v1/title.svg?t=<title>&n=<number>&w=<width>&c=<chip>&c=<chip>   chip: pill|<colour>|<label> or chip|<icon>|<label>|<mono or color>
  GET /v1/label.svg?t=<word>&i=<icon>
  GET /v1/link.svg?t=<text>&i=<icon>&pt=<space above>&square=<true for the outlined square style>
  GET /v1/filebar.svg?t=<path>&w=<width>     the title strip that sits on top of a code block
  GET /v1/header.svg?t=<title>&i=<icon>&s=<subtitle>&w=<width>&pt=<space above>&pb=<space below>&middle=&hang=<px continued below>&bh=<band height>&top=<line above>
  GET /v1/edge.svg?kind=<side, rside, bottom, close, gap, fill, rule, space or divider>&w=<width>&h=<height>&pb=<space below>&pl=<space left>&pr=<space right>   border pieces around a code block
  GET /v1/note.svg?t=<text>&pt=<space above>
  GET /v1/card.svg?t=<text>&w=<width>&pt=<space above>&h=<heading>&i=<icon>   h turns the card into a panel with a title row
  Either endpoint also takes z=<text, zlib-compressed then base64url> in place of t, for shorter addresses.
"""
from __future__ import annotations

import base64
import binascii
import zlib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from server.render import (
    LINK_ICONS, SECTION_ICONS, render_card, render_edge, render_filebar, render_fluid_band, render_fluid_edge, render_header, render_label,
    render_link, render_note, render_plain_title, render_title,
)

MAX_TITLE, MAX_TEXT = 300, 8000
HEADERS = {
    # The image depends only on its address, so git hosts and browsers may keep it forever.
    "Cache-Control": "public, max-age=31536000, immutable",
    # Opened directly, the SVG may not run scripts or load anything.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}
PAD_TOP = Query(0, ge=0, le=32)   # transparent rows above the image: the only way to set spacing inside a comment
app = FastAPI(title="qodo-chips image server", docs_url=None, redoc_url=None, openapi_url=None)


def _text(t: str | None, z: str | None, limit: int) -> str:
    if z:
        try:
            raw = zlib.decompressobj().decompress(base64.urlsafe_b64decode(z + "=" * (-len(z) % 4)), limit * 4 + 1)
            t = raw.decode("utf-8")
        except (binascii.Error, zlib.error, UnicodeDecodeError) as error:
            raise HTTPException(400, "z is not zlib-compressed base64url text") from error
    if not t or not t.strip():
        raise HTTPException(400, "missing text: pass t or z")
    if len(t) > limit:
        raise HTTPException(413, f"text is longer than {limit} characters")
    return t.strip()


def _image(svg: str) -> Response:
    return Response(svg, media_type="image/svg+xml", headers=HEADERS)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/title.svg")
def title(
    t: str | None = None, z: str | None = None, n: str = Query("", max_length=6, pattern=r"^\d*$"),
    c: list[str] = Query([], max_length=8), w: int = Query(0, ge=0, le=1200), frame: bool = True,
) -> Response:
    text = " ".join(_text(t, z, MAX_TITLE).split())
    if not frame:
        return _image(render_plain_title(text, n))
    try:
        return _image(render_title(text, n, c, w))
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/v1/label.svg")
def label(t: str | None = None, z: str | None = None, i: str = Query("", max_length=20)) -> Response:
    if i and i not in SECTION_ICONS:
        raise HTTPException(400, f"unknown icon; use one of {sorted(SECTION_ICONS)}")
    return _image(render_label(" ".join(_text(t, z, 60).split()), i))


@app.get("/v1/link.svg")
def link(
    t: str | None = None, z: str | None = None, i: str = Query("", max_length=20), pt: int = PAD_TOP, pb: int = Query(0, ge=0, le=32),
    square: bool = False,
) -> Response:
    if i and i not in LINK_ICONS:
        raise HTTPException(400, f"unknown icon; use one of {sorted(LINK_ICONS)}")
    return _image(render_link(" ".join(_text(t, z, 160).split()), i, pt, pb, square))


@app.get("/v1/filebar.svg")
def filebar(t: str | None = None, z: str | None = None, w: int = Query(760, ge=120, le=1200), i: str = Query("file", max_length=20)) -> Response:
    return _image(render_filebar(" ".join(_text(t, z, 200).split()), w, i))


@app.get("/v1/header.svg")
def header(
    t: str | None = None, z: str | None = None, i: str = Query("", max_length=20), s: str = Query("", max_length=160),
    w: int = Query(760, ge=320, le=1200), pt: int = PAD_TOP, pb: int = Query(0, ge=0, le=32), open_bottom: bool = False,
    pl: int = Query(0, ge=0, le=64), middle: bool = False, c: list[str] = Query([], max_length=4), bare: bool = False,
    hang: int = Query(0, ge=0, le=32), bh: int = Query(0, ge=0, le=64), top: bool = True, fluid: bool = False,
) -> Response:
    if i and i not in SECTION_ICONS:
        raise HTTPException(400, f"unknown icon; use one of {sorted(SECTION_ICONS)}")
    try:
        if fluid:
            return _image(render_fluid_band(" ".join(_text(t, z, 60).split()), i, " ".join(s.split()), c, bh or 36, hang, top, pt))
        return _image(render_header(" ".join(_text(t, z, 60).split()), i, " ".join(s.split()), w, pt, pb, open_bottom, pl, middle, c, bare, hang, bh, top))
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/v1/edge.svg")
def edge(
    kind: str = Query("side", pattern="^(side|rside|lside|bottom|rule|space|divider|close|gap|fill)$"), w: int = Query(760, ge=320, le=1200), h: int = Query(8, ge=7, le=4000),
    pb: int = Query(0, ge=0, le=32), pl: int = Query(0, ge=0, le=64), pr: int = Query(0, ge=0, le=64),
    fluid: bool = False, lp: float = Query(0, ge=0, le=100), pt: int = PAD_TOP,
) -> Response:
    if fluid:
        return _image(render_fluid_edge(kind, h, lp, pt))
    return _image(render_edge(kind, w, h, pb, pl, pr))


@app.get("/v1/note.svg")
def note(t: str | None = None, z: str | None = None, pt: int = PAD_TOP) -> Response:
    return _image(render_note(" ".join(_text(t, z, 200).split()), pt))


@app.get("/v1/card.svg")
def card(
    t: str | None = None, z: str | None = None, w: int = Query(760, ge=320, le=1200), pt: int = PAD_TOP,
    h: str = Query("", max_length=60), i: str = Query("", max_length=20), open_bottom: bool = False,
) -> Response:
    if i and i not in SECTION_ICONS:
        raise HTTPException(400, f"unknown icon; use one of {sorted(SECTION_ICONS)}")
    return _image(render_card(_text(t, z, MAX_TEXT), w, pt, " ".join(h.split()), i, open_bottom))
