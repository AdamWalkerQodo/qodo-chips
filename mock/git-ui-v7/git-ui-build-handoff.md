# Handoff: build the Git UI v7 review comment for production

You are taking over the "Git UI" work for Qodo review comments (owner: Adam). The look is final and agreed. Your job is to
make the engine produce it for real, and to get the image hosting built. Read this whole file before starting.

## 1. What is agreed (do not redesign)

The live reference is the first Qodo comment on https://github.com/adamqodo-org/excalidraw/pull/305 (comment 7100714272),
built by `build_stretch.py` in this folder (`qodo-chips/mock/git-ui-v7/`). Reproduce it exactly; ask Adam before trading any
part of the look for robustness.

Per finding, on GitHub only:

- **Finding title**: native bold text `1. <title>` in the `<summary>`, then the severity/type/category chips (static images).
- **Container**: one bordered box per finding, sections fold (Description open, the rest folded): Description, Code,
  Evidence, Relevance (when present), Agent prompt, then a footer with "Dismiss finding" and "View in Qodo" buttons.
- **Section band**: a drawn header image per section (icon, section name, fixed Qodo subtitle, Relevance strength chip).
- **Stretches with the window**: every width is a percentage of the comment column, so it fits windows from ~900px up.
  GitHub's signed-in comment column = window width - 450px, capped at 986px (from a 1,436px window); below ~1,000px it is
  window - 370px. Signed-out GitHub serves an older, narrower page.
- **File header on a code block**: a drawn filled bar (rounded top, file icon, the generic text "View file", arrow on the
  right), linked to the file, flush on the code block (0px gap). The real path is the code block's first line:
  `diff --git a/<path> b/<path>` for diff blocks (GitHub renders it blue; no line range, the `@@` hunk line under it has it),
  then a blank line. Non-diff excerpts (Evidence citations) keep a plain `<path> [<range>]` first line.
- **References**: rules and tickets are native lines (icon image + linked name). Past PRs in Relevance are drawn square
  buttons `PR-#6798` (PR numbers are not sensitive).

## 2. Security rule that shaped the design

No customer text inside images. Images may carry only fixed Qodo text, icons, borders, sizes, counts and PR numbers. File
paths, finding titles, rule names and ticket names stay native comment text. (Reason: images are stored outside the
customer's git host, in a bucket readable by anyone holding the address.)

## 3. Layout mechanics (the hard-won part; keep these exactly)

Constants (in `build_stretch.py`): `LP = 3.0` (% of column where the container starts; the room left of it holds the fold
arrow, >= 15px at the narrowest column), `SIDE_W = 3.1` (% width of the left side-line image), `FIT_W = 530` (column the
side-line heights are estimated for, a ~900px window), `BAND_H = 36`, `HANG = 16`, `TITLE_SPACE = 10`, `PAD = 16`, `SLACK = 4`,
`FILEBAR_H = 32`, `PARAGRAPH_GAP = 16`.

- Sections sit in `<div align="right">`, each section's content in `<div align="left">`; no `<dl><dd>` indent. The band is
  `width="{100-LP}%"`, so the fold arrow and the band share one line whatever the arrow's width (12-15px by display).
- A 16px `edge kind=fill` strip hangs out of each `<summary>` into the 16px GitHub leaves under every `<details>`.
- Side lines are floats sized from a text-height estimate at `FIT_W` (so they never stop short; wider windows get spare room).
  Content is split into parts (`Parts` class): a part's rows run between one pair of side lines; a file header bar is an
  in-flow full-width image (`filebar.svg?fluid=true&lp=..&bl=..`) that starts a new part.
- Ending an open section: a FULL-WIDTH IN-FLOW image (`edge kind=gap h=21`, it cannot sit beside the side-line floats, so the
  next fold starts below every float and its arrow stays on its band) followed by the floated 16px `close` strip. When the
  section ends with a paragraph, put both inside that paragraph (saves its 16px margin). `<br clear="all">` was tried and
  adds a 17px line; don't use it.
- Every image has width AND height. Keep the alt text on bands (Adam's decision: accessibility over robustness), even though
  Chrome ignores the size of a failed image that has alt text.
- Verified on #305 with no breaks, no separated arrows and 0px joins at 900, 1,150 and 1,706px windows (measured in the
  app's built-in browser with viewport emulation; the measurement script compares float bottoms, joins and summary heights).

## 4. Hosting decision (agreed 2026-11-23)

- The engine (pr-agent backend) draws the SVGs itself, uploads them to a Google Cloud bucket, and puts the bucket URL in the
  comment. Name each object by a hash of its SVG content (e.g. `review-images/<sha256>.svg`), upload only if missing, set
  `Cache-Control: public, max-age=31536000, immutable`. Content names replace the `v=` version tags: a redraw is a new address.
- Bucket: a NEW private bucket, served through the EXISTING get.qodo.ai load balancer/CDN under `/review-images/` (Adam chose
  "new bucket, same CDN"). No new IP, certificate or DNS. Do not reuse `qodo-cli-public` (it ships install.sh).
- Environments that get this: multi-tenant, single-tenant, pentest. On-prem and air-gapped do not (no bucket configured →
  findings keep the standard layout).
- Open, confirm with Adam before writing infra: one bucket with per-environment folders vs one bucket per environment on
  the same load balancer; how single-tenant AWS tenants upload (cross-cloud credentials).

### Infra facts (Codium-ai/codium-infrastructure, Terragrunt, CI-only plan/apply, PR + human review)

- Read `CLAUDE.md` and `.claude/skills/authoring-a-terragrunt-unit` first. House rules: terse comments, prefer community
  modules, pin latest versions, group with `for_each`, never push to main.
- Pattern to copy: bucket `codium/production/codium-production/us-central1/infra/gcs-buckets/qodo-cli-public/terragrunt.hcl`
  (private, `public_access_prevention = "enforced"`, Private Bucket Access for
  `serviceAccount:service-67590289846@https-lb.iam.gserviceaccount.com`), LB
  `codium/production/codium-production/us-central1/workload/get-qodo-lb` + `modules/get-qodo-lb` (one backend bucket with
  Cloud CDN, `cache_mode = USE_ORIGIN_HEADERS`; resource names are hardcoded, so add a second `google_compute_backend_bucket`
  and a path matcher for `/review-images/*` rather than duplicating the module).
- Security standard `qodo-security-standards/rules/storage-buckets-must-block-public-access.yaml` (severity error): never
  bind `allUsers`; the CDN pattern complies.
- Writers need `roles/storage.objectCreator` (ideally scoped to a managed folder, like the `repo-wiki` tenant bucket in
  `codium/saas/gcp/gcp-tenant/infra/gcs-buckets/repo-wiki`). Tenants: `codium/saas/gcp/tenants.yaml`,
  `codium/saas/aws/tenants.yaml`; pentest project `gcp-org/org/projects/qodo-saas-merge-pentest-1`.

## 5. Engine work (pr-agent-pro)

State: branch `feat/git-ui-foldable-findings`, worktree `PR-Agent/.claude/worktrees/pr-agent-git-ui`, LOCAL only (no push, no
PR), last commit `dd5199fe0`. It has the 22 November layout (`pr_agent/algo/agents/ux/finding_containers.py`, fixed pixels,
image server URL setting `review_agent_ux.image_server_url`, `finding_layout = "containers"`), not v7. Run it with
`PYTHONPATH=. ../pr-agent-image-chips/.venv/bin/python` (no venv of its own). Fetch Qodo rules (qodo-get-rules) before coding.

To do:
1. Port v7's markup from `build_stretch.py` into `finding_containers.py` (parts, in-flow closing, filebar with "View file",
   `diff --git` first line, native references, PR buttons, footer). Keep `containers_to_text` round-tripping so
   `convert_markdown_to_findings` still parses the comment (hidden `<!--qodo:classic ...-->` lines).
2. Port the renderer: `qodo-chips/server/render.py` + `qodo-chips/generator/chips.py` (Inter woff2 fonts, `assets/icons.json`,
   needs `fonttools` + `brotli`). Pieces used by v7: `header.svg?fluid=true` (band), `edge.svg?fluid=true` kinds
   fill/gap/close/lside, `edge.svg kind=side`, `filebar.svg?fluid=true`, `link.svg?square=true` (PR buttons), `icon.svg`.
3. Static vs dynamic: borders, bands, buttons, chips are parametric but customer-free; counters and PR buttons are dynamic.
   Counters today are static files `v1/chip/color/type/<type>/count-0..20plus.svg` on raw.githubusercontent (personal repo
   AdamWalkerQodo/qodo-chips): draw them dynamically with no 20 cap. Move every static image off raw.githubusercontent.
4. Upload + URL injection with `google-cloud-storage` (already a dependency; client setup pattern in
   `pr_agent/secret_providers/google_cloud_storage_secret_provider.py`). New settings for bucket name and public base URL,
   empty by default; GitHub only.
5. Size: ~62k characters for 6 findings; GitHub accepted a 72k comment, but check the engine's own trimming limits.

## 6. Pitfalls already found

- GitHub's image proxy (camo) caches every address for a year (`immutable`). A browser can keep a cut-off copy of one
  address even after clearing its cache; only a new address fixes it. Content-hash names make every redraw a new address.
- Chrome ignores width/height of a failed image that has alt text (it shows the alt text instead).
- GitLab breaks this layout: it removes `<picture>`, wraps every image in a link to itself, and the SVGs' colors follow the
  computer's dark mode, not the site theme. Keep containers GitHub-only.
- GitHub paints no background behind native text and keeps 16px under its own `<pre>` box; that is why the file header is an
  image with generic text.
- Rejected, don't retry: tables (alternating row colors, width follows content), fixed-pixel containers (only fit one column
  width), percentage v4 that changed the approved look, text-in-image file headers.

## 7. Test setup

- Test repo adamqodo-org/excalidraw (public: never post private pr-agent-pro code or findings there). Post with
  `GH_TEST_PR_PAT` from `~/.config/qodo-local-dev/github-app.env` (don't print it).
- Dummy engine review: `~/.claude/skills/dummy-review-prs/scripts/post_dummy_review.py --provider github --pr-url <PR>
  --visible 6 --runs 0 --skip-inline --no-platform-config` with `REVIEW_AGENT_UX__CHIP_STYLE=images
  REVIEW_AGENT_UX__FINDING_LAYOUT=containers` (+ the new bucket settings). It edits the first "Code Review by Qodo" comment
  on the PR, so post reference comments after it.
- The prototype image server runs locally on :8095 behind the Cloudflare tunnel `chips` (https://chips.adamwalker.io);
  restart with `server/run_local.sh` from qodo-chips (see its README). It goes away once the engine draws images itself.
- Comparison comments on #305 (labs): 7100940683, 7101555557, 7101717278, 7101729410.
