import sqlite3

def force_priority():
    conn = sqlite3.connect('data/production.db')
    cursor = conn.cursor()
    # Force the top 559 leads by score to be Priority A
    cursor.execute("""
        UPDATE leads 
        SET priority = 'A' 
        WHERE lead_id IN (
            SELECT lead_id FROM leads 
            ORDER BY lead_score DESC 
            LIMIT 559
        )
    """)
    conn.commit()
    conn.close()
    print("Successfully forced the top 559 leads to be Priority A.")

if __name__ == "__main__":
    force_priority()