import pandas as pd
import sqlite3
from src.config import DATA_DIR

def export_to_csv():
    conn = sqlite3.connect(DATA_DIR / "leads.db")
    
    # Exact column names required by IncuBrix
    query = """
    SELECT 
        lead_id, creator_name, 'Podcaster' as creator_segment, country_iso2, 'en' as primary_language,
        primary_platform, profile_url, stable_creator_id, followers_or_subscribers, last_content_date,
        recent_content_url, content_count_30d, longform_count_60d, monetization_signal,
        monetization_evidence_url, incubrix_need, need_evidence_url, best_channel,
        channel_handle_or_url, channel_evidence_url, backup_channel, personalization_hook,
        first_message, checked_date, priority, lead_score, candidate_status, rejection_reason,
        duplicate_check, completeness_check
    FROM leads
    WHERE candidate_status = 'Qualified'
    ORDER BY lead_score DESC
    """
    
    df = pd.read_sql_query(query, conn)
    df.to_csv(DATA_DIR / "leads.csv", index=False, encoding='utf-8')
    print(f"Exported {len(df)} qualified leads to data/leads.csv")
    
    conn.close()