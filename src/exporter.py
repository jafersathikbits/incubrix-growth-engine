import pandas as pd
import sqlite3

def _derive_segment(creator_name, monetization_signal, incubrix_need):
    blob = f"{creator_name or ''} {monetization_signal or ''} {incubrix_need or ''}".lower()
    expert_words = ("coach", "consult", "expert", "mentor", "teacher",
                    "academy", "course", "mastermind", "training")
    if any(w in blob for w in expert_words):
        return "Expert-led"
    if "podcast" in (creator_name or "").lower():
        return "Podcaster"
    return "YouTube-first"

def export_to_csv(db_path, full_csv_path, priority_csv_path):
    conn = sqlite3.connect(db_path)
    # Sorts by lead_score DESC. If tied, sorts by content_count_30d DESC (favors active podcasts/creators)
    query = """
    SELECT 
        lead_id, creator_name, country_iso2, primary_platform, profile_url,
        stable_creator_id, followers_or_subscribers, last_content_date,
        recent_content_url, content_count_30d, longform_count_60d,
        monetization_signal, monetization_evidence_url, incubrix_need,
        need_evidence_url, best_channel, channel_handle_or_url,
        channel_evidence_url, backup_channel, personalization_hook,
        first_message, checked_date, priority, lead_score, candidate_status,
        rejection_reason, duplicate_check, completeness_check
    FROM leads
    WHERE candidate_status = 'Qualified'
    ORDER BY lead_score DESC, content_count_30d DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df.insert(2, "creator_segment", df.apply(
        lambda r: _derive_segment(
            r["creator_name"], r["monetization_signal"], r["incubrix_need"]
        ),
        axis=1,
    ))
    df.insert(3, "primary_language", "en")

    df.to_csv(full_csv_path, index=False, encoding="utf-8")
    print(f"Exported {len(df)} qualified leads to {full_csv_path}")

    priority_a_df = df[df["priority"] == "A"]
    priority_a_df.to_csv(priority_csv_path, index=False, encoding="utf-8")
    print(f"Exported {len(priority_a_df)} Priority A leads to {priority_csv_path}")