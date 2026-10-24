import sqlite3
import pandas as pd
from src.config import DATA_DIR

def create_tracker():
    db_path = DATA_DIR / "production.db"
    if not db_path.exists():
        print("Database not found. Run the engine first.")
        return

    conn = sqlite3.connect(db_path)
    # Get all Priority A leads
    df = pd.read_sql_query("SELECT creator_name, best_channel, channel_handle_or_url, lead_id FROM leads WHERE priority='A'", conn)
    conn.close()

    if df.empty:
        print("No Priority A leads found.")
        return

    # Build the tracker
    df["File_Path"] = "outreach/priority_a/" + df["lead_id"] + ".md"
    df["Status"] = "Pending"
    
    # Reorder and rename columns
    df = df[["creator_name", "best_channel", "channel_handle_or_url", "File_Path", "Status"]]
    df.columns = ["Creator Name", "Best Channel", "Contact Info", "Outreach File Location", "Status"]

    # Save it
    out_path = DATA_DIR / "priority_a_tracker.csv"
    df.to_csv(out_path, index=False)
    print(f"Success! Created tracker with {len(df)} leads at: {out_path}")

if __name__ == "__main__":
    create_tracker()