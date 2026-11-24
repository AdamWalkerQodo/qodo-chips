# Git UI v7: the agreed comment layout (reference build)

`build_stretch.py` writes the review comment posted on adamqodo-org/excalidraw#305, the design agreed on 2026-11-23. It is the
reference the engine renderer must reproduce.

```
python3 build_stretch.py out.md https://github.com/<owner>/<repo>/pull/<n>/files
```

- Reads the engine's sample findings from the `pr-agent-image-chips` worktree (`SAMPLES`), and draws images through the image server
  at `SERVER` in `comment_layout.py` (`https://chips.adamwalker.io/v1`, this repo's `server/`).
- `FILE_HEADER=image` (default) is the agreed file header; `filled` and `outlined` are the rejected alternatives, kept for comparison.
- `V` in `comment_layout.py` is the version tag on every image address; bump it whenever the server redraws a piece.

What the layout is, and why, is in the build handoff prompt (`git-ui-build-handoff.md` in this folder).
