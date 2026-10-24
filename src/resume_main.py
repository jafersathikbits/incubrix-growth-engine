import argparse
import os

from src.config import DATA_DIR
from src.exporter import export_to_csv
from src.database import get_connection
from src.outreach_gen import generate_priority_a_pack


def _count_leads(db_path):
    if not os.path.exists(db_path):
        return 0
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM leads").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def _load_priority_a(db_path):
    """Load Priority A leads without existing outreach packs."""
    if not os.path.exists(db_path):
        return []
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM leads WHERE candidate_status='Qualified' AND priority='A'"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Resume IncuBrix engine")
    parser.add_argument("--limit", type=int, default=6000, help="Total lead target")
    parser.add_argument("--no-outreach", action="store_true",
                        help="Skip regenerating Priority A outreach packs")
    args = parser.parse_args()

    db_path = DATA_DIR / "production.db"
    full_csv = DATA_DIR / "production_leads.csv"
    priority_csv = DATA_DIR / "production_priority_a.csv"

    existing = _count_leads(db_path)
    print("=" * 60)
    print(f"  RESUMING ENGINE  (existing leads: {existing}, target: {args.limit})")
    print("=" * 60)

    if existing >= args.limit:
        print(f"[SKIP] Already at target ({existing}/{args.limit}). Exporting only.")
    else:
        # Import here so `main.py` argparse block only runs when needed
        from main import run_engine
        try:
            # FIX: Pass resume_mode=True
            run_engine(db_path=db_path, limit=args.limit, resume_mode=True)
        except Exception as e:
            print(f"\n[NOTICE] Engine paused: {e}")

    # Regenerate Priority A outreach packs
    if not args.no_outreach:
        leads = _load_priority_a(db_path)
        if leads:
            print(f"\nRegenerating outreach for {len(leads)} Priority A leads...")
            for lead in leads:
                try:
                    generate_priority_a_pack(lead)
                except Exception as e:
                    print(f"  [WARN] Pack failed for {lead.get('lead_id')}: {e}")
        else:
            print("\n[SKIP] No Priority A leads to generate outreach for.")

    # Export
    print("\nExporting to CSV...")
    if os.path.exists(db_path):
        export_to_csv(str(db_path), str(full_csv), str(priority_csv))
    else:
        print(f"[WARN] DB not found at {db_path}, skipping export.")


if __name__ == "__main__":
    main()