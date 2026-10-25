"""
Self-audit: sample N random leads and verify evidence + distribution rules.
"""
import argparse
import csv
import random
from collections import Counter

APPROVED = {"US", "CA", "GB", "IE", "AU", "NZ", "SG"}

CHECKS = [
    ("country_in_approved",     lambda r: r.get("country_iso2") in APPROVED),
    ("has_creator_name",        lambda r: bool((r.get("creator_name") or "").strip())),
    # Made URL check more flexible for real-world YouTube URLs (@handles, /c/, etc)
    ("has_profile_url",         lambda r: (r.get("profile_url") or "").startswith(("https://"))),
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
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames

    if not rows:
        print("No leads to audit.")
        return

    total_rows = len(rows)
    
    # 1. Duplicate Check (MUST be on stable_creator_id, not lead_id)
    creator_ids = [r.get("stable_creator_id") for r in rows if r.get("stable_creator_id")]
    duplicates = len(creator_ids) - len(set(creator_ids))

    # 2. Country Distribution
    countries = Counter(r.get("country_iso2") for r in rows if r.get("country_iso2"))
    total_countries = sum(countries.values())
    
    over_cap = {c: n for c, n in countries.items() if total_countries and 100 * n / total_countries > 60}
    approved_count = sum(n for c, n in countries.items() if c in APPROVED)
    approved_pct = (approved_count / total_countries) * 100 if total_countries else 0

    # 3. Priority A Count
    priorities = Counter(r.get("priority") for r in rows)
    a_count = priorities.get("A", 0)

    n = min(sample_size, total_rows)
    sample = random.sample(rows, n) if n < total_rows else rows[:]

    print(f"\n# Self-audit report\n- **Total leads:** {total_rows}\n- **Sampled:** {n}\n")
    print(f"- Duplicates (stable_creator_id): {duplicates} ({'PASS' if duplicates == 0 else 'FAIL'})")
    print(f"- Approved Countries (>=80%): {approved_pct:.1f}% ({'PASS' if approved_pct >= 80 else 'FAIL'})")
    print(f"- Distinct countries (>=3): {len(countries)} ({'PASS' if len(countries) >= 3 else 'FAIL'})")
    print(f"- Max Country Cap (<=60%): {len(over_cap)} countries over ({'PASS' if not over_cap else 'FAIL'})")
    print(f"- Priority A count (>=25): {a_count} ({'PASS' if a_count >= 25 else 'FAIL'})\n")

    totals = {name: 0 for name, _ in CHECKS}
    passes = 0

    print("| # | Creator | Status | Failures |")
    print("|---|---|---|---|")
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
        print(f"| {i} | {str(row.get('creator_name', '?'))[:30]} | {status} | {f_str} |")

    print(f"\n## Summary\n- **Lead-level pass rate (Audit Score):** {passes}/{n} = {100*passes/n:.1f}%")
    print("*(Target: 85%+ to survive IncuBrix's 20-lead random audit)*\n")
    
    print("Check-by-check success rate:")
    for name in totals:
        pct = 100 * totals[name] / n
        print(f"- {name}: {totals[name]}/{n} ({pct:.0f}%)")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/production_leads.csv")
    p.add_argument("--sample", type=int, default=20)
    args = p.parse_args()
    audit(args.csv, args.sample)