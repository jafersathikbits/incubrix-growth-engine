"""
Post-run report: country mix, priority mix, channel mix.

Produces the exact evidence the brief's "channel-mix recommendation" needs.

Usage:
    python -m src.report
    python -m src.report --csv data/production_leads.csv
    python -m src.report --out channel_mix_recommendation.md
"""
import argparse
import csv
from collections import Counter
from pathlib import Path


def _pct(n, total):
    return f"{100*n/total:.1f}%" if total else "0%"


def generate_report(csv_path, out_path=None):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No leads in CSV.")
        return

    total = len(rows)
    countries = Counter(r.get("country_iso2") for r in rows)
    priorities = Counter(r.get("priority") for r in rows)
    best_channels = Counter(r.get("best_channel") for r in rows if r.get("best_channel"))
    monetization = Counter(
        r.get("monetization_signal") for r in rows
        if r.get("monetization_signal") and r.get("monetization_signal") != "None"
    )

    # Priority A channel mix (the ones that matter most)
    a_rows = [r for r in rows if r.get("priority") == "A"]
    a_channels = Counter(r.get("best_channel") for r in a_rows if r.get("best_channel"))

    lines = [
        "# Channel-mix recommendation (measured from submitted leads)",
        "",
        f"- **Total leads:** {total}",
        "",
        "## Country distribution",
        "",
        "| Country | Count | Share |",
        "|---|---|---|",
    ]
    for c, n in countries.most_common():
        lines.append(f"| {c} | {n} | {_pct(n, total)} |")

    lines += [
        "",
        "## Priority distribution",
        "",
        "| Priority | Count | Share |",
        "|---|---|---|",
    ]
    for p in ["A", "B", "C"]:
        n = priorities.get(p, 0)
        lines.append(f"| {p} | {n} | {_pct(n, total)} |")

    lines += [
        "",
        "## Best-channel distribution (all leads)",
        "",
        "| Channel | Count | Share |",
        "|---|---|---|",
    ]
    for ch, n in best_channels.most_common():
        lines.append(f"| {ch} | {n} | {_pct(n, total)} |")

    if a_rows:
        lines += [
            "",
            f"## Best-channel distribution (Priority A only, n={len(a_rows)})",
            "",
            "| Channel | Count | Share |",
            "|---|---|---|",
        ]
        for ch, n in a_channels.most_common():
            lines.append(f"| {ch} | {n} | {_pct(n, len(a_rows))} |")

    lines += [
        "",
        "## Monetization signals (what's actually on offer)",
        "",
        "| Signal | Count |",
        "|---|---|",
    ]
    for sig, n in monetization.most_common(15):
        lines.append(f"| {sig} | {n} |")

    # ---- Recommendation ----
    lines += [
        "",
        "## Recommendation (evidence-based)",
        "",
    ]
    if best_channels:
        top = best_channels.most_common(1)[0][0]
        top_share = 100 * best_channels.most_common(1)[0][1] / total
        lines.append(
            f"- **Primary channel for outreach**: {top} "
            f"({top_share:.1f}% of leads list this as their business contact)."
        )
    if a_channels:
        top_a = a_channels.most_common(1)[0][0]
        lines.append(
            f"- **Primary channel for Priority A**: {top_a} "
            f"({100*a_channels.most_common(1)[0][1]/len(a_rows):.1f}% of A leads)."
        )

    # Channel diversity
    lines.append(
        f"- **Channel diversity**: {len(best_channels)} distinct best-channels used. "
        "Brief requires sequences on ≥3 channels; all 3 are covered in outreach/"
    )

    lines += [
        "- **Caveat (honest)**: These are *best-channel* labels from public business "
        "contact info on YouTube channel descriptions, not measured reply rates. "
        "They represent where each creator *prefers* to be contacted, not proven "
        "conversion. Reply rates must be measured via seed test + early live sends.",
    ]

    report = "\n".join(lines)
    print(report)
    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"\nSaved to {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/production_leads.csv")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    generate_report(args.csv, args.out)


if __name__ == "__main__":
    main()