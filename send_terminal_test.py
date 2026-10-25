import sqlite3
import os
from dotenv import load_dotenv
from src.config import DATA_DIR
from src.email_sender import send_test_email

load_dotenv()

def send_real_lead():
    db_path = DATA_DIR / "production.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the top Priority A lead from the database
    lead = cursor.execute("SELECT * FROM leads WHERE priority='A' ORDER BY lead_score DESC LIMIT 1").fetchone()
    conn.close()

    if not lead:
        print("No Priority A lead found. Run the engine first.")
        return

    lead_dict = dict(lead)
    print(f"--- SENDING TEST EMAIL FOR: {lead_dict['creator_name']} ---")
    print(f"Target Contact (Original): {lead_dict['channel_handle_or_url']}")
    
    # We send it to YOUR test email from .env, not the real creator
    to_email = os.getenv("SEED_EMAIL_TO", "test@example.com")
    print(f"Redirecting to YOUR test inbox: {to_email}\n")

    subject = f"IncuBrix Live Outreach Test: {lead_dict['creator_name']}"
    body = lead_dict['first_message']

    print(f"--- EMAIL BODY ---\n{body}\n------------------")

    success, msg = send_test_email(to_email, subject, body)
    if success:
        print(f"✅ SUCCESS! {msg}")
    else:
        print(f"❌ FAILED: {msg}")

if __name__ == "__main__":
    send_real_lead()