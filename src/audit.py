"""
Self-audit: sample N random leads and verify evidence + distribution rules.
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
    ("has_profile_url",         lambda r: (r.get("profile_url") or "").startswith(("https://youtube.com/channel/", "https://podcasts.apple.com/"))),
    ("has_recent_content_url",  lambda r: bool((r.get("recent_content_url") or "").strip())),
    ("has_channel_handle",      lambda r: bool((r.get("channel_handle_or_url") or "").strip())),
    ("has_channel_evidence",    lambda r: bool((r.get("channel_evidence_url") or "").strip())),
    ("has_monetization",        lambda r: r.get("monetization_signal") not in (None, "", "None")),
    ("has_real_need",           lambda r: (r.get("incubrix_need") or "").lower().startswith(("high", "medium"))),
    ("active_30d_or_60d",       lambda r: (
        int(r.get("content_count_30d") or 0) >= 8
        or int(r.get("longform_count_60d") or 0) >= 2
    )),
    ("best_channel_valid",      lambda r: r.get("best_channel") in ("Email", "LinkedIn", "Instagram")),
    ("evidence_urls_not_empty", lambda r: (
        bool((r.get("monetization_evidence_url") or "").strip())
        and bool((r.get("need_evidence_url") or "").strip())
    )),
]

def audit(csv_path, sample_size=20):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No leads to audit.")
        return

    total_rows = len(rows)
    lead_ids = [r.get("lead_id") for r in rows]
    duplicates = total_rows - len(set(lead_ids))

    countries = Counter(r.get("country_iso2") for r in rows if r.get("country_iso2"))
    total_countries = sum(countries.values())
    over_cap = {c: n for c, n in countries.items() if total_countries and 100 * n / total_countries > 60}

    priorities = Counter(r.get("priority") for r in rows)
    a_count = priorities.get("A", 0)

    n = min(sample_size, total_rows)
    sample = random.sample(rows, n) if n < total_rows else rows[:]

    print(f"\n# Self-audit report\n- **Total leads:** {total_rows}\n- **Sampled:** {n}\n")
    print(f"- Duplicate lead_ids: {duplicates} ({'PASS' if duplicates == 0 else 'FAIL'})")
    print(f"- Distinct countries: {len(countries)} ({'PASS' if len(countries) >= 3 else 'FAIL'})")
    print(f"- Countries over 60%: {len(over_cap)} ({'PASS' if not over_cap else 'FAIL'})")
    print(f"- Priority A count: {a_count} ({'PASS' if a_count <= 250 else 'FAIL'})\n")

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
        print(f"| {i} | {row.get('creator_name', '?')[:30]} | {status} | {f_str} |")

    print(f"\n## Summary\n- **Lead-level pass rate:** {passes}/{n} = {100*passes/n:.1f}%")
    for name in totals:
        pct = 100 * totals[name] / n
        print(f"- {name}: {totals[name]}/{n} ({pct:.0f}%)")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/production_leads.csv")
    p.add_argument("--sample", type=int, default=20)
    args = p.parse_args()
    audit(args.csv, args.sample)