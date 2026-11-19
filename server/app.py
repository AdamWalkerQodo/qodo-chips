"""Stateless image server: the request carries the text, the response is its SVG. Nothing is stored.

Run:  uvicorn server.app:app --port 8095   (from the repository root)

  GET /v1/title.svg?t=<title>&n=<number>
  GET /v1/label.svg?t=<word>&i=<icon>
  GET /v1/card.svg?t=<text>&w=<width>
  Either endpoint also takes z=<text, zlib-compressed then base64url> in place of t, for shorter addresses.
"""
from __future__ import annotations

import base64
import binascii
import zlib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from server.render import SECTION_ICONS, render_card, render_label, render_title

MAX_TITLE, MAX_TEXT = 300, 8000
HEADERS = {
    # The image depends only on its address, so git hosts and browsers may keep it forever.
    "Cache-Control": "public, max-age=31536000, immutable",
    # Opened directly, the SVG may not run scripts or load anything.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}
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
def title(t: str | None = None, z: str | None = None, n: str = Query("", max_length=6, pattern=r"^\d*$")) -> Response:
    return _image(render_title(" ".join(_text(t, z, MAX_TITLE).split()), n))


@app.get("/v1/label.svg")
def label(t: str | None = None, z: str | None = None, i: str = Query("", max_length=20)) -> Response:
    if i and i not in SECTION_ICONS:
        raise HTTPException(400, f"unknown icon; use one of {sorted(SECTION_ICONS)}")
    return _image(render_label(" ".join(_text(t, z, 60).split()), i))


@app.get("/v1/card.svg")
def card(t: str | None = None, z: str | None = None, w: int = Query(760, ge=320, le=1200)) -> Response:
    return _image(render_card(_text(t, z, MAX_TEXT), w))
