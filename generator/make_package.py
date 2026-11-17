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

from chips import CHIP_TOP_PAD, H, _svg, chip, pill

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
RISK_FACTORS = [("complexity", "puzzle", "🧩", RISK_COMPLEXITY), ("damage", "bandage", "🩹", RISK_DAMAGE)]
COLOR_FAMILIES = {"type", "source", "severity"}   # every other chip exists in mono only; severity colour is used with colour-scale group badges
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
        label_chip("severity", level, f"sev:{i}", "", emoji, emoji, variants=("icon",))
        for term, words in TERMS.items():
            label_chip("severity", f"{level}/{term}", f"sev:{i}", words[i], f"{emoji} {words[i]}", emoji, variants=("",))
            counters("severity", f"{level}/{term}", f"sev:{i}", words[i], f"{emoji} {words[i]}")
    for key, label, n, circles in RELEVANCE:
        label_chip("relevance", key, f"rel:{n}", label, f"{circles} {label}", circles)
        counters("relevance", key, f"rel:{n}", label, f"{circles} {label}")
    for key, label, icon, glyph in STATUS:
        label_chip("status", key, icon, label, f"{glyph} {label}", glyph, variants=("", "icon", "text"))
    label_chip("flag", "new", "sparkles", "New", "⭐ New", "⭐")
    counters("flag", "new", "sparkles", "New", "⭐ New")
    label_chip("flag", "local-find", "computer", "Local find", "💻 Local find", "💻")
    for key, label, icon, emoji in MODES:
        label_chip("mode", key, icon, label, f"{emoji} {label}", emoji, variants=("",))
    label_chip("mode", "auto", "wand-sparkles", "Auto", "Auto:", "Auto:", variants=("",))   # sits before the chosen mode's chip
    label_chip("link", "dismiss", "x", "Dismiss", "Dismiss ↗", "Dismiss", variants=("",))
    label_chip("link", "view", "external-link", "View", "View ↗", "View", variants=("",))
    for key, label, icon, emoji in PR_TYPES:
        label_chip("pr-type", key, icon, label, f"{emoji} {label}".strip(), emoji or label, variants=("",))
    for key, label in REVIEW_TIMES:
        label_chip("review-time", key, "clock", label, f"🕐 {label}", "🕐", variants=("",))
    for key, label, bars, dot in RISK_LEVELS:
        label_chip("risk", key, f"risk:{key}", f"{label} risk", f"{bars} {label} risk", bars, variants=("",))
        label_chip("risk-level", key, f"dot:{key}", label, f"{dot} {label}", dot, variants=("",))
    label_chip("risk", "unavailable", "risk:none", "Risk unavailable", "⬜⬜⬜ Risk unavailable", "⬜⬜⬜", variants=("",))
    label_chip("risk-level", "not-assessed", "dot:none", "Not assessed", "⚪ Not assessed", "⚪", variants=("",))
    counters("risk-blast-radius", "capabilities", "bomb", "Capabilities", "💥 Capabilities")
    for factor, icon, emoji, labels in [("blast-radius", "bomb", "💥", [])] + RISK_FACTORS:
        for label in [*labels, "Assessed behavior", "Not assessed"]:
            label_chip(f"risk-{factor}", label.lower().replace(" ", "-"), icon, label, f"{emoji} {label}", emoji, variants=("",))
    for key, icon, alt in [("loaded", "circle-check", "✅"), ("error", "circle-x", "❌"), ("skipped", "triangle-alert", "⚠️"), ("superseded", "circle-minus", "⊖")]:
        label_chip("source", key, icon, "", alt, alt, variants=("icon",))

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
                body, w = pill(label, color, icon if with_icon else None)
                save(f"pill/{grouping}/{key}/{coloring}{'-icon' if with_icon else ''}", body, w,
                     family="pill", grouping=grouping, key=key, coloring=coloring, icon=with_icon, alt=alt)

    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    from collections import Counter
    by = Counter(("counters" if "count" in m else "pills" if m["family"] == "pill" else "label chips") for m in manifest)
    print(len(manifest), "images:", dict(by))


if __name__ == "__main__":
    main()
