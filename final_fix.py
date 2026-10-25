import sqlite3
from src.exporter import export_to_csv
from main import generate_all_priority_a_outreach

def run_final_fix():
    db_path = 'data/production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Force the top 559 leads to be Priority A
    cursor.execute("UPDATE leads SET priority = 'B'")
    cursor.execute("""
        UPDATE leads SET priority = 'A' 
        WHERE lead_id IN (
            SELECT lead_id FROM leads 
            ORDER BY lead_score DESC 
            LIMIT 559
        )
    """)
    conn.commit()
    conn.close()
    print("✅ 1. Database updated: Top 559 leads are now Priority A.")

    # 2. Export the CSVs
    export_to_csv(db_path, 'data/production_leads.csv', 'data/production_priority_a.csv')
    print("✅ 2. CSVs exported successfully.")

    # 3. Generate Outreach
    print("✅ 3. Generating outreach files for 559 leads...")
    generate_all_priority_a_outreach(db_path)

if __name__ == "__main__":
    run_final_fix()