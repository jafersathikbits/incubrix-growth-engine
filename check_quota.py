import json
from datetime import datetime, timezone
from pathlib import Path

QUOTA_FILE = Path("logs/quota_usage.json")
DAILY_QUOTA = 10_000
NUM_KEYS = 12


def _bar(used, total, width=40):
    filled = int(used / total * width) if total else 0
    return "#" * filled + "." * (width - filled)


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not QUOTA_FILE.exists():
        print("No usage tracked yet. Run `python main.py` first.")
        return

    try:
        data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Could not read {QUOTA_FILE}: {e}")
        return

    file_date = data.get("date", "?")
    usage = data.get("usage", {})

    if file_date != today:
        print(f"Usage file is from {file_date}, not today ({today}).")
        print("Quota resets at UTC midnight — all keys should have fresh quota.")
        return

    print(f"\nQuota usage for {today} (estimated):\n")
    print(f"  {'Key':<6} {'Used':>6}/{DAILY_QUOTA}  {'Bar':<42} {'Left':>6}  Status")
    print(f"  {'-'*6} {'-'*16}  {'-'*42} {'-'*6}  {'-'*6}")

    total_used = 0
    dead_count = 0
    low_count = 0

    for i in range(NUM_KEYS):
        used = usage.get(str(i), 0)
        total_used += used
        remaining = DAILY_QUOTA - used

        if remaining <= 0:
            status = "DEAD"
            dead_count += 1
        elif remaining < 500:
            status = "LOW"
            low_count += 1
        else:
            status = "OK"

        print(f"  {i+1:<6} {used:>6}      {_bar(used, DAILY_QUOTA):<42} {remaining:>6}  {status}")

    total_capacity = NUM_KEYS * DAILY_QUOTA
    total_remaining = total_capacity - total_used

    print()
    print(f"  Total used:      {total_used:>7,} / {total_capacity:,}  ({100*total_used/total_capacity:.1f}%)")
    print(f"  Total remaining: {total_remaining:>7,}")
    print(f"  Dead keys:       {dead_count}/{NUM_KEYS}")
    print(f"  Low keys:        {low_count}/{NUM_KEYS}")

    # Rough capacity estimate
    # search.list = 100 units; ~102 units per 50-channel page
    # ~3-5% pass rate → 50 channels → ~2 leads per page → ~50 units per lead
    if total_remaining > 0:
        est_leads = int(total_remaining / 50)
        print(f"\n  Rough remaining capacity: ~{est_leads:,} more leads")


if __name__ == "__main__":
    main()