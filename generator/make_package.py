"""Generate every chip image into ../v1/ and write ../manifest.json.

Each image is one SVG that carries a light and a dark palette and picks one from the reader's theme.
Layout (one folder per chip, holding all its forms):
  v1/chip/{style}/{family}/{key}/label.svg | icon.svg | text.svg | count-{n}.svg     (n = 0..20, 20plus)
  v1/pill/{grouping}/{key}/{coloring}.svg | {coloring}-icon.svg
Severity keys are {level}/{wording}, e.g. severity/action-required/p0-p1-p2/label.svg.
"""
import json
import shutil
from pathlib import Path

from chips import BUTTON_H, CARD_H, STAT_H, CHIP_TOP_PAD, H, PALETTES, _svg, _tint, button, chip, hairline, metric_card, pill, qodo_band, stat_segment, suggestion_card

ROOT = Path(__file__).parent.parent   # repository root
OUT = ROOT
COUNTS = [str(n) for n in range(21)] + ["20+"]

# key, singular, plural, icon, today's emoji
TYPES = [("bugs", "Bug", "Bugs", "bug", "🐞"), ("rule-violations", "Rule violation", "Rule violations", "book-marked", "📘"),
         ("requirements-gap", "Requirement gap", "Requirement gaps", "paperclip", "📎"), ("ui-issues", "UI issue", "UI issues", "monitor", "🖥"),
         ("ux-issue", "UX issue", "UX issues", "palette", "🎨"), ("cross-repo", "Cross-repo conflict", "Cross-repo conflicts", "link", "🔗"),
         ("team-insights", "Team insight", "Team insights", "users", "🧑"), ("skill-insights", "Skill insight", "Skill insights", "scroll", "📜"),
         ("memory-insights", "Memory", "Memories", "brain", "🧠"), ("security-issues", "Security issue", "Security issues", "shield-plus", "🛡")]
# key, label, icon, today's symbol
CATEGORIES = [("correctness", "Correctness", "menu", "≡"), ("reliability", "Reliability", "sun-dim", "☼"), ("security", "Security", "shield-plus", "⛨"),
              ("quality", "Quality", "diamond", "✧"), ("maintainability", "Maintainability", "bolt", "⚙"), ("performance", "Performance", "move-up-right", "➹"),
              ("observability", "Observability", "eye", "◔"), ("compliance", "Compliance", "clipboard-check", "§"), ("design", "Design", "pen-tool", "❖"),
              ("architecture", "Architecture", "triangle", "⌂"), ("accessibility", "Accessibility", "square-check", "☑"), ("testability", "Testability", "square-dot", "▣"),
              ("documentation", "Documentation", "file-text", "¶"), ("other", "Other", "circle-ellipsis", "✨️")]
LEVELS = [("action-required", "🔴"), ("remediation-recommended", "🟠"), ("informational", "🟡")]
PR_TYPES = [("bug-fix", "Bug fix", "bug", "🐞"), ("tests", "Tests", "flask-conical", "🧪"), ("enhancement", "Enhancement", "trending-up", "✨"),
            ("documentation", "Documentation", "file-text", "📝"), ("configuration-changes", "Configuration changes", "settings", "⚙️"),
            ("refactor", "Refactor", "refresh-cw", ""), ("other", "Other", "circle-ellipsis", "")]
REVIEW_TIMES = [("under-5", "Less than 5 minutes"), ("under-10", "Less than 10 minutes"), ("10-20", "10-20 Minutes"),
                ("20-40", "20-40 Minutes"), ("over-40", "40+ Minutes")]
RISK_LEVELS = [("high", "High", "🟥🟥🟥", "🔴"), ("medium", "Medium", "🟨🟨⬜", "🟡"), ("low", "Low", "🟩⬜⬜", "🟢")]
RISK_COMPLEXITY = ["Straightforward", "Interacting branches", "Data transformation", "Compatibility cases", "Coordinated invariants",
                   "Concurrent ordering", "Subtle algorithm", "State transitions", "Multiple interactions"]
RISK_DAMAGE = ["Cosmetic", "Reversible", "Recoverable", "Incorrect results", "Temporary loss", "Confidentiality", "Integrity",
               "Financial error", "Data loss", "Critical loss"]
RISK_FACTORS = [("complexity", "waypoints", "🧩", RISK_COMPLEXITY), ("damage", "flame", "🩹", RISK_DAMAGE)]
# Merge suggestion cards: (tone, reason key, label, detail line, icon). The engine picks one by suggestion and main reason.
SUGGESTIONS = [   # copy is kept short so it is not cut off when the card is narrow
    ("not-safe", "high-findings", "Not ready", "High findings", "circle-x"),
    ("not-safe", "high-risk-findings", "Not ready", "High risk, findings", "circle-x"),
    ("consider", "medium-findings", "Needs review", "Medium findings", "triangle-alert"),
    ("consider", "security-findings", "Needs review", "Security findings", "triangle-alert"),
    ("consider", "high-risk", "Needs review", "High risk", "triangle-alert"),
    ("consider", "medium-risk", "Needs review", "Medium risk", "triangle-alert"),
    ("safe", "clear", "Looks ready", "Nothing blocking", "circle-check"),
]
NOTES = [("copy-prompt", "Copy this prompt and use it to remediate the issue with your preferred AI generation tools"),
         ("past-prs", "Recommendations generated based on similar findings in past PRs")]
COLOR_FAMILIES = {"type", "source", "risk"}   # every other chip exists in mono only; severity chips use the group badge colourings instead
TERMS = {"legacy": ["Action required", "Review recommended", "Optional"], "high-medium-low": ["High", "Medium", "Low"],
         "critical-warning-informational": ["Critical", "Warning", "Informational"],
         "required-recommended-optional": ["Required", "Recommended", "Optional"], "p0-p1-p2": ["P0", "P1", "P2"]}
RELEVANCE = [("strong", "Strong", 3, "●●●"), ("moderate", "Moderate", 2, "●●"), ("weak", "Weak", 1, "●")]
STATUS = [("resolved", "Resolved", "check", "✓"), ("dismissed", "Dismissed", "x", "✗"), ("outdated", "Outdated", "circle-slash", "⊘")]
MODES = [("fast", "Fast", "rocket", "🚀"), ("balanced", "Balanced", "scale", "⚖️"), ("deep", "Deep", "brain", "🧠"), ("skipped", "Skipped", "skip-forward", "⏭️")]
BRAND, GRAY, SCALE = "#634fd1", "#3d3d3d", ["#ce2c31", "#e36209", "#d4a72c"]

manifest, seen = [], set()


def save(path: str, body: str, width: float, top_pad: int = 0, **meta) -> None:
    assert path not in seen, path
    seen.add(path)
    target = OUT / "v1" / f"{path}.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_svg(width, body, top_pad))
    manifest.append({"file": f"v1/{path}.svg", "width": width, "height": H + top_pad, **meta})


def label_chip(family: str, key: str, icon: str | None, label: str, alt: str, alt_icon: str, variants=("", "icon"), count=None) -> None:
    """One chip in mono, plus color for the families that use it. variants: "" = icon + label, "icon" = icon only, "text" = label only."""
    for variant in variants:
        for style in ("mono", "color") if family in COLOR_FAMILIES else ("mono",):
            body, w = chip(None if variant == "text" else icon, None if variant == "icon" else label, count, style, "auto")
            form = f"count-{count.replace('+', 'plus')}" if count else variant or "label"
            text = alt_icon if variant == "icon" else label if variant == "text" else alt
            save(f"chip/{style}/{family}/{key}/{form}", body, w, CHIP_TOP_PAD, family=family, key=key, form=form, style=style,
                 alt=f"{text} ({count})" if count else text, **({"count": count} if count else {}))


def grayscale_icon_color(coloring: str, icon: str | None, grouping: str = "action-level") -> str:
    """Grayscale badges keep a coloured icon for severity and finding type; every other badge icon is white."""
    if coloring != "grayscale" or not icon or grouping not in ("action-level", "finding-type"):
        return "#ffffff"
    return _tint(icon, "color", PALETTES["dark"])


def severity_chip(coloring: str, color: str, key: str, form: str, label: str | None, icon: str | None, count: str | None, alt: str) -> None:
    """Severity chips look like the group badge: a solid pill in the badge's colouring, in place of the mono/color styles."""
    body, w = pill(label, color, icon, count, grayscale_icon_color(coloring, icon))
    save(f"chip/{coloring}/severity/{key}/{form}", body, w, CHIP_TOP_PAD, family="severity", key=key, form=form, style=coloring, alt=alt,
         **({"count": count} if count else {}))


def counters(family: str, key: str, icon: str, label: str, alt: str) -> None:
    for count in COUNTS:
        label_chip(family, key, icon, label, alt, alt, variants=("",), count=count)


def main() -> None:
    shutil.rmtree(OUT / "v1", ignore_errors=True)
    for key, singular, plural, icon, emoji in TYPES:
        label_chip("type", key, icon, singular, f"{emoji} {singular}", emoji)
        counters("type", key, icon, plural, f"{emoji} {plural}")
    for key, label, icon, symbol in CATEGORIES:
        label_chip("category", key, icon, label, f"{symbol} {label}", symbol)
        counters("category", key, icon, label, f"{symbol} {label}")
    for i, (level, emoji) in enumerate(LEVELS):
        for coloring, color in [("brand", BRAND), ("grayscale", GRAY), ("scale", SCALE[i])]:
            severity_chip(coloring, color, level, "icon", None, f"sev:{i}", None, emoji)
            for term, words in TERMS.items():
                for icon, suffix in [(None, ""), (f"sev:{i}", "-icon")]:
                    severity_chip(coloring, color, f"{level}/{term}", f"label{suffix}", words[i], icon, None, f"{emoji} {words[i]}")
                    for count in COUNTS:
                        severity_chip(coloring, color, f"{level}/{term}", f"count-{count.replace('+', 'plus')}{suffix}", words[i], icon, count,
                                      f"{emoji} {words[i]} ({count})")
    for key, label, n, circles in RELEVANCE:
        label_chip("relevance", key, f"rel:{n}", label, f"{circles} {label}", circles)
        counters("relevance", key, f"rel:{n}", label, f"{circles} {label}")
    for key, label, icon, glyph in STATUS:
        label_chip("status", key, icon, label, f"{glyph} {label}", glyph, variants=("", "icon", "text"))
    # Resolution strip above the findings: three outlined segments that sit edge to edge. Design still being iterated on.
    for key, label, position in [("open", "Open", "first"), ("resolved", "Resolved", "middle"), ("dismissed", "Dismissed", "last")]:
        for count in COUNTS:
            body, w = stat_segment(label, count, position)
            form = f"count-{count.replace('+', 'plus')}"
            target = OUT / "v1" / "stat" / key / f"{form}.svg"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{STAT_H}" viewBox="0 0 {w} {STAT_H}">{body}</svg>')
            manifest.append({"file": f"v1/stat/{key}/{form}.svg", "width": w, "height": STAT_H, "family": "stat", "key": key, "form": form,
                             "count": count, "alt": f"{label}: {count}"})
    label_chip("flag", "new", "sparkles", "New", "⭐ New", "⭐")
    counters("flag", "new", "sparkles", "New", "⭐ New")
    label_chip("flag", "local-find", "laptop", "Local find", "💻 Local find", "💻")
    for key, label, icon, emoji in MODES:
        label_chip("mode", key, icon, label, f"{emoji} {label}", emoji, variants=("",))
    label_chip("mode", "auto", "wand-sparkles", "Auto", "Auto:", "Auto:", variants=("",))   # sits before the chosen mode's chip
    for key, label, icon, emoji in PR_TYPES:
        label_chip("pr-type", key, icon, label, f"{emoji} {label}".strip(), emoji or label, variants=("",))
    for key, label in REVIEW_TIMES:
        label_chip("review-time", key, "clock", label, f"🕐 {label}", "🕐", variants=("",))
    for key, label, bars, dot in RISK_LEVELS:
        label_chip("risk", key, f"risk:{key}", f"{label} risk", f"{bars} {label} risk", bars, variants=("",))
        label_chip("risk-level", key, f"risk:{key}", label, f"{dot} {label}", dot, variants=("",))
    label_chip("risk", "unavailable", "risk:none", "Risk unavailable", "⬜⬜⬜ Risk unavailable", "⬜⬜⬜", variants=("",))
    label_chip("risk-level", "not-assessed", "risk:none", "Not assessed", "⚪ Not assessed", "⚪", variants=("",))
    counters("risk-blast-radius", "capabilities", "bomb", "Capabilities", "💥 Capabilities")
    for factor, icon, emoji, labels in [("blast-radius", "bomb", "💥", [])] + RISK_FACTORS:
        for label in [*labels, "Assessed behavior", "Not assessed"]:
            label_chip(f"risk-{factor}", label.lower().replace(" ", "-"), icon, label, f"{emoji} {label}", emoji, variants=("",))
    for key, text in NOTES:
        label_chip("note", key, "info", text, f"ⓘ {text}", "ⓘ", variants=("",))
    for key, icon, alt in [("loaded", "circle-check", "✅"), ("error", "circle-x", "❌"), ("skipped", "triangle-alert", "⚠️"), ("superseded", "circle-minus", "⊖")]:
        label_chip("source", key, icon, "", alt, alt, variants=("icon",))

    # Merge verdict section of the PR description: verdict badges, placeholder buttons and the dotted divider.
    # Cards of the Qodo suggestion row: the merge suggestion with its reason, then one card per metric.
    def card(path: str, svg: str, alt: str) -> None:
        target = OUT / "v1" / "card" / f"{path}.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg)
        manifest.append({"file": f"v1/card/{path}.svg", "width": "100%", "height": CARD_H, "family": "card", "key": path, "alt": alt})

    for tone, reason, label, detail, icon in SUGGESTIONS:
        card(f"suggestion/{tone}-{reason}", suggestion_card(label, detail, icon, tone), f"{label}: {detail}")
    for count in COUNTS:
        form = f"count-{count.replace('+', 'plus')}"
        for tone in ("red", "amber", "neutral"):
            card(f"open-findings/{tone}/{form}", metric_card("Open findings", count, "clipboard-check", tone), f"Open findings: {count}")
        for tone in ("amber", "neutral"):
            card(f"blocking-rules/{tone}/{form}", metric_card("Blocking rules", count, "shield-plus", tone), f"Blocking rules: {count}")
    for level, value, tone in [("high", "High", "red"), ("medium", "Medium", "amber"), ("low", "Low", "green"), ("unavailable", "Unknown", "neutral")]:
        card(f"merge-risk/{level}", metric_card("Merge risk", value, "triangle-alert", tone), f"Merge risk: {value}")
    (OUT / "v1" / "title").mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).parent / "assets" / "qodo-logo.svg", OUT / "v1" / "title" / "qodo-logo.svg")
    manifest.append({"file": "v1/title/qodo-logo.svg", "width": 135, "height": 46, "family": "title", "key": "qodo-logo", "alt": "Qodo"})
    for key, label, icon, primary in [("view-in-qodo", "View in Qodo", "external-link", True),
                                     ("finding-summary", "Finding summary", "clipboard-check", False), ("pr-overview", "PR overview", "git-pull-request", False),
                                     ("dismiss", "Dismiss", "x", False), ("view", "View", "external-link", False)]:
        body, w = button(label, icon, primary)
        target = OUT / "v1" / "button" / f"{key}.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{BUTTON_H}" viewBox="0 0 {w} {BUTTON_H}">{body}</svg>')
        manifest.append({"file": f"v1/button/{key}.svg", "width": w, "height": BUTTON_H, "family": "button", "key": key, "alt": label})
    (OUT / "v1" / "divider").mkdir(parents=True, exist_ok=True)
    for name, svg, height in [("qodo-band", qodo_band(), 14), ("hairline", hairline(), 1)]:
        (OUT / "v1" / "divider" / f"{name}.svg").write_text(svg)
        manifest.append({"file": f"v1/divider/{name}.svg", "width": "100%", "height": height, "family": "divider", "key": name, "alt": ""})

    # Group pills. alt for severity keeps the keywords the comment parsers look for.
    groups = [("finding-type", key, plural, icon, plural) for key, _, plural, icon, _ in TYPES]
    groups += [("finding-category", key, label, icon, label) for key, label, icon, _ in CATEGORIES]
    groups += [("relevance", key, label, f"rel:{n}", label) for key, label, n, _ in RELEVANCE]
    sev_alt = ["Action required", "Remediation recommended", "Informational"]
    for i, (level, _) in enumerate(LEVELS):
        for term, words in TERMS.items():
            groups.append(("action-level", f"{level}/{term}", words[i], f"sev:{i}", sev_alt[i]))
    for grouping, key, label, icon, alt in groups:
        colorings = [("brand", BRAND), ("grayscale", GRAY)]
        if grouping == "action-level":
            colorings.append(("scale", SCALE[[lv for lv, _ in LEVELS].index(key.split("/")[0])]))
        for coloring, color in colorings:
            for with_icon in (False, True):
                body, w = pill(label, color, icon if with_icon else None, icon_color=grayscale_icon_color(coloring, icon, grouping))
                save(f"pill/{grouping}/{key}/{coloring}{'-icon' if with_icon else ''}", body, w,
                     family="pill", grouping=grouping, key=key, coloring=coloring, icon=with_icon, alt=alt)

    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    from collections import Counter
    by = Counter(("counters" if "count" in m else "pills" if m["family"] == "pill" else "label chips") for m in manifest)
    print(len(manifest), "images:", dict(by))


if __name__ == "__main__":
    main()
