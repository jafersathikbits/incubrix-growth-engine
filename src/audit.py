"""
Self-audit: sample N random leads and verify evidence + distribution rules.

Usage:
    python -m src.audit
    python -m src.audit --sample 30
    python -m src.audit --report audit_report.md
"""
import argparse
import csv
import random
from collections import Counter
from pathlib import Path

APPROVED = {"US", "CA", "GB", "IE", "AU", "NZ", "SG"}

CHECKS = [
    ("country_in_approved",     lambda r: r.get("country_iso2") in APPROVED),
    ("has_creator_name",        lambda r: bool((r.get("creator_name") or "").strip())),
    ("has_profile_url",         lambda r: (r.get("profile_url") or "").startswith("https://youtube.com/channel/")),
    ("has_recent_content_url",  lambda r: (r.get("recent_content_url") or "").startswith("https://youtube.com/watch")),
    ("has_channel_handle",      lambda r: bool((r.get("channel_handle_or_url") or "").strip())),
    ("has_channel_evidence",    lambda r: bool((r.get("channel_evidence_url") or "").strip())),
    ("has_monetization",        lambda r: r.get("monetization_signal") not in (None, "", "None")),
    ("has_real_need",           lambda r: (r.get("incubrix_need") or "").lower().startswith(("high", "medium"))),
    ("active_30d_or_60d",       lambda r: (
        int(r.get("content_count_30d") or 0) >= 8
        or int(r.get("longform_count_60d") or 0) >= 2
    )),
    ("best_channel_valid",      lambda r: r.get("best_channel") in ("Email", "LinkedIn", "Instagram")),
    ("evidence_urls_not_about", lambda r: (
        # monetization/need evidence must point at a VIDEO, not the about page
        "watch?v=" in (r.get("monetization_evidence_url") or "")
        and "watch?v=" in (r.get("need_evidence_url") or "")
    )),
]


def audit(csv_path, sample_size=20, report_path=None):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No leads to audit.")
        return

    total_rows = len(rows)

    # ---- Global checks (whole file) ----
    lead_ids = [r.get("lead_id") for r in rows]
    duplicates = total_rows - len(set(lead_ids))

    countries = Counter(r.get("country_iso2") for r in rows if r.get("country_iso2"))
    total_countries = sum(countries.values())
    over_cap = {c: n for c, n in countries.items()
                if total_countries and 100 * n / total_countries > 60}
    under_3_countries = len(countries) < 3

    priorities = Counter(r.get("priority") for r in rows)
    a_count = priorities.get("A", 0)
    a_ratio = 100 * a_count / total_rows if total_rows else 0

    # ---- Random sample ----
    n = min(sample_size, total_rows)
    sample = random.sample(rows, n) if n < total_rows else rows[:]

    lines = [
        "# Self-audit report",
        "",
        f"- **File:** `{csv_path}`",
        f"- **Total leads:** {total_rows}",
        f"- **Sampled:** {n}",
        "",
        "## Global checks",
        "",
        f"- Duplicate lead_ids: {duplicates} ({'PASS' if duplicates == 0 else 'FAIL'})",
        f"- Approved-country leads: {total_countries}/{total_rows}",
        f"- Distinct countries: {len(countries)} ({'PASS' if not under_3_countries else 'FAIL — brief needs ≥3'})",
        f"- Countries over 60%: {len(over_cap)} ({'PASS' if not over_cap else 'FAIL — ' + str(over_cap)})",
        f"- Priority A count: {a_count} ({'PASS' if a_count <= 250 else 'FAIL — brief caps at 250'})",
        f"- Priority A ratio: {a_ratio:.1f}% ({'OK' if a_ratio <= 10 else 'HIGH — brief expects ~4%'})",
        "",
        "### Country breakdown",
        "",
        "| Country | Count | % |",
        "|---|---|---|",
    ]
    for c, cnt in countries.most_common():
        pct = 100 * cnt / total_countries if total_countries else 0
        lines.append(f"| {c} | {cnt} | {pct:.1f}% |")

    lines += [
        "",
        "### Priority breakdown",
        "",
        "| Priority | Count |",
        "|---|---|",
    ]
    for p in ["A", "B", "C"]:
        lines.append(f"| {p} | {priorities.get(p, 0)} |")

    lines += [
        "",
        "## Per-lead sample",
        "",
        "| # | Creator | Result | Failures |",
        "|---|---|---|---|",
    ]

    totals = {name: 0 for name, _ in CHECKS}
    passes = 0

    for i, row in enumerate(sample, 1):
        failures = []
        for name, check in CHECKS:
            ok = check(row)
            totals[name] += int(ok)
            if not ok:
                failures.append(name)
        lead_pass = len(failures) == 0
        passes += int(lead_pass)
        status = "PASS" if lead_pass else "FAIL"
        f_str = ", ".join(failures) if failures else "-"
        lines.append(f"| {i} | {row.get('creator_name', '?')[:40]} | {status} | {f_str} |")

    lines += [
        "",
        "## Summary",
        "",
        f"- **Lead-level pass rate:** {passes}/{n} = {100*passes/n:.1f}%",
        f"- **Target:** ≥90%",
        "",
        "## Per-check pass rate",
        "",
        "| Check | Pass | Rate | Status |",
        "|---|---|---|---|",
    ]
    for name in totals:
        pct = 100 * totals[name] / n
        status = "OK" if pct >= 90 else "LOW"
        lines.append(f"| {name} | {totals[name]}/{n} | {pct:.0f}% | {status} |")

    report = "\n".join(lines)
    print(report)

    if report_path:
        Path(report_path).write_text(report, encoding="utf-8")
        print(f"\nReport saved to: {report_path}")

    return passes, n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/production_leads.csv")
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--report", type=str, default=None)
    args = p.parse_args()
    audit(args.csv, args.sample, args.report)


if __name__ == "__main__":
    main()