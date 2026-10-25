import argparse
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from src.config import LOGS_DIR, BASE_DIR
from src.email_sender import send_test_email, get_smtp_connection

load_dotenv()

logger = logging.getLogger("incubrix.seed")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOGS_DIR / "seed_test.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(sh)

TRACKING_BASE = os.getenv("TRACKING_BASE_URL", "https://jafersathikbits.github.io/jsb-portfolio")
SENDER_NAME = os.getenv("SENDER_NAME", "Jafer Sathik B")
SENDER_EMAIL = os.getenv("SMTP_EMAIL", "test@example.com")

SEED_EMAIL_TO = os.getenv("SEED_EMAIL_TO", "")
SEED_LINKEDIN_HANDLE = os.getenv("SEED_LINKEDIN_HANDLE", "")
SEED_INSTAGRAM_HANDLE = os.getenv("SEED_INSTAGRAM_HANDLE", "")

OUTBOX_FILES = {
    "email": LOGS_DIR / "outbox_email.jsonl",
    "linkedin": LOGS_DIR / "outbox_linkedin.jsonl",
    "instagram": LOGS_DIR / "outbox_instagram.jsonl",
}
REPLY_LOG = LOGS_DIR / "replies.jsonl"

def _tracking_link(channel: str, lead_id: str, seq_step: int) -> str:
    # Returns just your portfolio link
    return TRACKING_BASE

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _extract_sequence_from_md(channel="email", segment_name="Segment 1"):
    md_file = f"{channel}_sequence.md"
    md_path = BASE_DIR / "outreach" / md_file
    if not md_path.exists():
        return None, []
    
    content = md_path.read_text(encoding="utf-8")
    segments = content.split("## ")
    target_segment = ""
    for seg in segments:
        if seg.startswith(segment_name):
            target_segment = seg
            break
            
    if not target_segment:
        return None, []

    subject = "IncuBrix Outreach"
    if channel == "email":
        subject_match = re.search(r"Subject:\s*(.*)", target_segment)
        if subject_match:
            subject = subject_match.group(1).strip()
    
    parts = re.split(r"\*\*(?:Message|Follow-up) \d.*?\*\*", target_segment)
    messages = []
    for p in parts[1:4]:
        clean_msg = p.strip()
        lines = clean_msg.split("\n")
        if lines and lines[0].startswith("Subject:"):
            clean_msg = "\n".join(lines[1:]).strip()
        if clean_msg:
            messages.append(clean_msg)
            
    return subject, messages

def _replace_placeholders(text):
    text = text.replace("{first_name}", "Test Inbox")
    text = text.replace("{recent_title}", "My Awesome Test Episode")
    text = text.replace("{specific_observation}", "This is a great test observation.")
    text = text.replace("{email}", SENDER_EMAIL)
    text = text.replace("{booking_link}", "https://www.linkedin.com/in/jafersathikbits/")
    return text

def _send_email(lead_id: str, step: int, subject: str, body: str, smtp_server=None) -> bool:
    if not SEED_EMAIL_TO:
        logger.error("SEED_EMAIL_TO not set in .env")
        return False
    
    ok, msg = send_test_email(SEED_EMAIL_TO, subject, body, server=smtp_server)
    record = {
        "ts": _now_iso(), "channel": "email", "lead_id": lead_id, "step": step,
        "to": SEED_EMAIL_TO, "tracking_link": _tracking_link("email", lead_id, step),
        "subject": subject, "ok": ok, "result": msg,
    }
    with OUTBOX_FILES["email"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"email step {step} -> {SEED_EMAIL_TO}: {'OK' if ok else 'FAIL'}")
    return ok

def _queue_manual(channel: str, lead_id: str, step: int, body: str):
    handle = SEED_LINKEDIN_HANDLE if channel == "linkedin" else SEED_INSTAGRAM_HANDLE
    if not handle:
        logger.error(f"SEED_{channel.upper()}_HANDLE not set in .env")
        return False
    
    record = {
        "ts": _now_iso(), "channel": channel, "lead_id": lead_id, "step": step,
        "to": handle, "tracking_link": _tracking_link(channel, lead_id, step),
        "body": body, "status": "queued_for_manual_send",
        "note": "Platform rules prohibit bulk automation. Send manually.",
    }
    with OUTBOX_FILES[channel].open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"{channel} step {step} queued for @{handle}")
    return True

def run_send(channels: list[str]):
    lead_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    start = datetime.now(timezone.utc)
    
    logger.info(f"=== SEED TEST START lead_id={lead_id} channels={channels} ===")
    
    for ch in channels:
        subject, messages = _extract_sequence_from_md(channel=ch, segment_name="Segment 1")
        
        if not messages or len(messages) < 3:
            logger.error(f"Could not extract 3 messages from {ch}_sequence.md")
            continue

        for i in range(len(messages)):
            messages[i] = _replace_placeholders(messages[i])
            # --- WE ADDED THIS BACK ---
            tracking = _tracking_link(ch, lead_id, i+1)
            messages[i] += f"\n\n[Tracking: {tracking}]"
            # --------------------------

        smtp_server = None
        if ch == "email":
            logger.info("Connecting to SMTP server...")
            smtp_server = get_smtp_connection()
            if not smtp_server:
                logger.error("Failed to connect to SMTP. Skipping email channel.")
                continue

        for step, body in enumerate(messages, 1):
            if ch == "email":
                step_subject = subject if step == 1 else f"Re: {subject}"
                _send_email(lead_id, step, step_subject, body, smtp_server)
            else:
                _queue_manual(ch, lead_id, step, body)
                
        if smtp_server:
            smtp_server.quit()

    logger.info(f"=== SEED TEST END lead_id={lead_id} ===")
    print(f"\nSeed test complete. lead_id={lead_id}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--send", action="store_true")
    p.add_argument("--channel", choices=["email", "linkedin", "instagram"])
    p.add_argument("--all", action="store_true")
    args = p.parse_args()

    if args.send:
        channels = ["email", "linkedin", "instagram"] if args.all else ([args.channel] if args.channel else [])
        if not channels:
            p.error("--send needs --channel or --all")
        run_send(channels)
    else:
        p.print_help()

if __name__ == "__main__":
    main()