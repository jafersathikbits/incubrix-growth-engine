import sqlite3
import hashlib
from src.config import DATA_DIR

DB_PATH = DATA_DIR / "leads.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        lead_id TEXT PRIMARY KEY,
        stable_creator_id TEXT UNIQUE,
        creator_name TEXT,
        country_iso2 TEXT,
        primary_platform TEXT,
        profile_url TEXT,
        followers_or_subscribers INTEGER,
        last_content_date TEXT,
        recent_content_url TEXT,
        content_count_30d INTEGER,
        longform_count_60d INTEGER,
        monetization_signal TEXT,
        monetization_evidence_url TEXT,
        incubrix_need TEXT,
        need_evidence_url TEXT,
        best_channel TEXT,
        channel_handle_or_url TEXT,
        channel_evidence_url TEXT,
        backup_channel TEXT,
        personalization_hook TEXT,
        first_message TEXT,
        checked_date TEXT,
        priority TEXT,
        lead_score INTEGER,
        candidate_status TEXT,
        rejection_reason TEXT,
        duplicate_check TEXT,
        completeness_check TEXT
    )
    """)
    conn.commit()
    conn.close()

def generate_lead_id(channel_id):
    return hashlib.sha256(channel_id.encode('utf-8')).hexdigest()

def is_duplicate(channel_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leads WHERE stable_creator_id = ?", (channel_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_lead(data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    data_dict['lead_id'] = generate_lead_id(data_dict['stable_creator_id'])
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?'] * len(data_dict))
    sql = f"INSERT OR IGNORE INTO leads ({columns}) VALUES ({placeholders})"
    try:
        cursor.execute(sql, tuple(data_dict.values()))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()