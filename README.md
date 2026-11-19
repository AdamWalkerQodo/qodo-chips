# qodo-chips

Image chips for Qodo's code review comments on GitHub, GitLab and Azure DevOps: finding type, category, severity, status, counters and group pills.

<p>
<img src="v1/chip/color/type/bugs/count-3.svg" height="21" align="top" alt="Bugs (3)">
<img src="v1/chip/color/type/rule-violations/count-12.svg" height="21" align="top" alt="Rule violations (12)">
<img src="v1/chip/scale/severity/action-required/legacy/label.svg" height="21" align="top" alt="Action required">
<img src="v1/chip/mono/category/correctness/label.svg" height="21" align="top" alt="Correctness">
<img src="v1/chip/mono/status/resolved/label.svg" height="21" align="top" alt="Resolved">
<img src="v1/chip/mono/type/bugs/label.svg" height="21" align="top" alt="Bug">
<img src="v1/pill/finding-type/bugs/brand-icon.svg" height="20" align="top" alt="Bugs">
</p>

> **Temporary host.** This repository serves the images while the feature is in development. The long-term host is still to be decided, so do not treat these URLs as permanent.

## Using a chip

Base URL:

```
https://raw.githubusercontent.com/AdamWalkerQodo/qodo-chips/main/v1
```

In a comment:

```html
<img src="{base}/chip/color/type/bugs/label.svg" height="21" align="top" alt="🐞 Bug">
```

- `height="21"` keeps a chip at its drawn size: 20px plus one transparent row on top, which lines its label up with 14px comment text. Group pills are 20px tall.
- `align="top"` pins the image to the top of the text line.
- `alt` should be the text chip it replaces, so the comment still reads correctly if the image fails to load.

## Colour

Colour is used sparingly. Icons are grey, with these exceptions:

- Finding type chips and their counters are always coloured.
- Source status icons are always coloured.
- The overall merge risk chip is always coloured: red, amber or green by level. Factor level chips use the same meter icon in grey.
- Severity chips look like the group badge: a solid pill in the badge's colouring (`brand`, `scale` or `grayscale`). Files ending in `-icon` add the bars icon, for when the group badge shows its icon.

## Light and dark

Every chip is one SVG that holds a light and a dark palette and picks one itself.

| Provider | What the chip follows |
|---|---|
| GitHub | GitHub's own theme |
| GitLab, Azure DevOps | The reader's browser or system light/dark setting |
| Bitbucket | Not supported: Bitbucket places every image on its own line, so chips cannot sit next to a finding title |

Group pills are a solid colour with white text and look the same in both themes.

## Layout

One folder per chip, holding all its forms:

```
v1/
  chip/{style}/{family}/{key}/
      label.svg                  icon and word
      icon.svg                   icon only
      text.svg                   word only (status chips)
      count-0.svg … count-20.svg, count-20plus.svg
  pill/{grouping}/{key}/
      {coloring}.svg, {coloring}-icon.svg
  card/suggestion/{tone}-{reason}.svg            merge suggestion card with its reason, 68px tall
  card/open-findings/count-{n}.svg        metric cards: one value each; they stretch to the width given
  card/merge-risk/{level}.svg
  card/blocking-rules/count-{n}.svg
  stat/{open|resolved|dismissed}/count-{n}.svg   resolution strip segments, 21px tall like chips, placed edge to edge
  title/qodo-logo.svg                  the Qodo logo (mark and name), used as a section title
  button/{native|straight}/{view-in-qodo|finding-summary|pr-overview}.svg   Qodo suggestion buttons in both button styles, 28px tall
  button/{key}.svg                          earlier, unstyled copies; Dismiss and View on findings
  divider/qodo-band-above.svg               thin line, purple at both ends, sitting just above Qodo's header row
  divider/qodo-band-below.svg               the same with space above the line, for under the row
manifest.json                    every file with its width and alt text
```

| Part | Values |
|---|---|
| `style` | `mono` (grey icon) for every chip except severity; `color` (coloured icon) only for `type`, `source` and `risk`; `brand`, `scale`, `grayscale` for `severity` |
| `family` | Review comments: `type`, `category`, `severity`, `relevance`, `status`, `flag`, `mode`, `source`, `note`. PR description: `pr-type`, `review-time`. Merge risk: `risk`, `risk-level`, `risk-blast-radius`, `risk-complexity`, `risk-damage` |
| `key` | the chip, for example `bugs`, `correctness`, `resolved`, `new`. Severity keys are `{level}/{wording}`, for example `action-required/p0-p1-p2` |
| `grouping` | `finding-type`, `finding-category`, `action-level`, `relevance` |
| `coloring` | `brand`, `grayscale`, and `scale` for `action-level` |

Counters exist for `type`, `category`, `severity`, `relevance`, `flag/new` and `risk-blast-radius/capabilities`. Counts above 20 use `count-20plus.svg`.

Examples:

```
v1/chip/color/type/bugs/label.svg
v1/chip/color/type/bugs/count-3.svg
v1/chip/scale/severity/action-required/p0-p1-p2/label.svg
v1/chip/brand/severity/action-required/p0-p1-p2/count-3-icon.svg
v1/pill/finding-type/bugs/brand-icon.svg
```

## Regenerating

The files under `v1/` and `manifest.json` are generated. Do not edit them by hand.

```bash
pip install -r generator/requirements.txt
```

```bash
python generator/make_package.py
```

| File | Purpose |
|---|---|
| `generator/chips.py` | Draws one chip or pill as SVG; holds the palettes and icon colours |
| `generator/make_package.py` | The list of every chip; writes `v1/` and `manifest.json` |
| `generator/extract_icons.mjs` | Copies icon shapes from an installed `lucide-react` into `generator/assets/icons.json` |
| `generator/assets/` | Inter font files and the icon shapes |

To add a chip, add it to the lists at the top of `make_package.py`, add its icon name to `extract_icons.mjs` if it is new, regenerate, and commit the generator change together with the new images.

Text is drawn as outlines from the Inter font, because an SVG shown as an image cannot load a font.

## Credits

- Icons: [Lucide](https://lucide.dev), ISC licence.
- Typeface: [Inter](https://rsms.me/inter/), SIL Open Font License 1.1.

## Image server (experimental)

`server/` draws images that depend on a finding's own text, which cannot be generated ahead of time: the finding title as a long chip, and a text card where `backticked` names are set in monospace on a rounded tint. It is stateless: the request carries the text and the response is its SVG; nothing is stored.

```bash
pip install -r generator/requirements.txt -r server/requirements.txt
```

```bash
server/run_local.sh
```

| Address | Draws |
|---|---|
| `/v1/title.svg?t={title}&n={number}&w={width}&c={chip}` | The title as a bordered bar, 36px tall with 4px of transparent space above and below. Each `c` adds a chip inside it, on the right: `pill\|{colour}\|{label}` or `chip\|{icon}\|{label}\|{mono or color}` |
| `/v1/label.svg?t={word}&i={icon}` | A section label: icon and word. Icons: `description`, `code`, `evidence`, `agent-prompt`, `relevance` |
| `/v1/link.svg?t={text}&i={icon}` | A reference chip to wrap in a link: file path, rule id, ticket. Icons: `file`, `rule`, `ticket`, `web`, `pr` |
| `/v1/note.svg?t={text}` | A quiet one-line note: info icon and muted text |
| `/v1/card.svg?t={text}&w={width}` | The text card, wrapped to `w` pixels (default 760) |

`link`, `note` and `card` take `pt={pixels}`: transparent rows above the image. A comment cannot carry CSS, so spacing between a section label and its content is set this way.

Either address also takes `z=` in place of `t=`: the text, zlib-compressed and then base64url-encoded, for shorter addresses.

On GitHub, wrap the title image in `<picture>` when it sits in a `<summary>`. A bare `<img>` is turned into a link to the image, so a click on the title would open the file and not fold the section.
