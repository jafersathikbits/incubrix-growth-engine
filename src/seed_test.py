import argparse
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from src.config import LOGS_DIR
from src.email_sender import send_test_email

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

TRACKING_BASE = os.getenv("TRACKING_BASE_URL", "https://incubrix.example.com/r")
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
    return f"{TRACKING_BASE}/{channel}/{lead_id}?step={seq_step}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schedule_followups(start: datetime):
    return {
        1: start.isoformat(),
        2: (start + timedelta(days=3)).isoformat(),
        3: (start + timedelta(days=7)).isoformat(),
    }


def _message_body(channel: str, lead_id: str, step: int) -> tuple[str, str]:
    """Returns (subject, body) for a seed test message."""
    link = _tracking_link(channel, lead_id, step)
    optout = "Reply STOP to opt out." if channel == "email" else "Reply STOP to opt out."
    if channel == "email":
        subject = f"[SEED TEST] Step {step} - IncuBrix growth engine"
        body = (
            f"Hi (test inbox),\n\n"
            f"This is a seed-test message from {SENDER_NAME} (IncuBrix candidate). "
            f"Step {step} of 3.\n\n"
            f"Tracking link: {link}\n\n"
            f"- {SENDER_NAME}\n{SENDER_EMAIL}\n{optout}\n"
        )
        return subject, body
    elif channel == "linkedin":
        body = (
            f"Hi (LinkedIn seed test), {SENDER_NAME} here. Step {step} of 3. "
            f"Tracking: {link}. {optout}"
        )
        return "", body
    else:
        body = (
            f"Hey (Instagram seed test)! {SENDER_NAME} - step {step} of 3. "
            f"{link}. {optout}"
        )
        return "", body


def _send_email(lead_id: str, step: int) -> bool:
    if not SEED_EMAIL_TO:
        logger.error("SEED_EMAIL_TO not set in .env")
        return False
    subject, body = _message_body("email", lead_id, step)
    ok, msg = send_test_email(SEED_EMAIL_TO, subject, body)
    record = {
        "ts": _now_iso(),
        "channel": "email",
        "lead_id": lead_id,
        "step": step,
        "to": SEED_EMAIL_TO,
        "tracking_link": _tracking_link("email", lead_id, step),
        "subject": subject,
        "ok": ok,
        "result": msg,
    }
    with OUTBOX_FILES["email"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"email step {step} -> {SEED_EMAIL_TO}: {'OK' if ok else 'FAIL'} {msg}")
    return ok


def _queue_manual(channel: str, lead_id: str, step: int):
    handle = SEED_LINKEDIN_HANDLE if channel == "linkedin" else SEED_INSTAGRAM_HANDLE
    if not handle:
        logger.error(f"SEED_{channel.upper()}_HANDLE not set in .env")
        return False
    _, body = _message_body(channel, lead_id, step)
    record = {
        "ts": _now_iso(),
        "channel": channel,
        "lead_id": lead_id,
        "step": step,
        "to": handle,
        "tracking_link": _tracking_link(channel, lead_id, step),
        "body": body,
        "status": "queued_for_manual_send",
        "note": "Platform rules prohibit bulk automation. Send manually from your test account.",
    }
    with OUTBOX_FILES[channel].open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"{channel} step {step} queued for @{handle}")
    return True


def run_send(channels: list[str]):
    lead_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    start = datetime.now(timezone.utc)
    schedule = _schedule_followups(start)
    logger.info(f"=== SEED TEST START lead_id={lead_id} channels={channels} ===")
    logger.info(f"Follow-up schedule: {schedule}")
    for ch in channels:
        for step in (1, 2, 3):
            if ch == "email":
                _send_email(lead_id, step)
            else:
                _queue_manual(ch, lead_id, step)
    logger.info(f"=== SEED TEST END lead_id={lead_id} ===")
    print(f"\nSeed test complete. lead_id={lead_id}")
    print(f"Outboxes: {OUTBOX_FILES['email'].parent}")
    print(f"Reply log: {REPLY_LOG}")


def run_log_reply(channel: str, lead_id: str, text: str):
    record = {
        "ts": _now_iso(),
        "channel": channel,
        "lead_id": lead_id,
        "reply_text": text,
        "classification": "interested" if any(
            w in text.lower() for w in ("yes", "interest", "demo", "call", "send")
        ) else "other",
    }
    with REPLY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"Reply logged: {channel}/{lead_id} -> {record['classification']}")
    print(f"Logged reply to {REPLY_LOG}")


def run_report():
    print("\n=== SEED TEST REPORT ===")
    for ch, path in OUTBOX_FILES.items():
        if path.exists():
            rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
            print(f"{ch:10s} | {len(rows)} messages queued/sent")
        else:
            print(f"{ch:10s} | (no outbox)")
    if REPLY_LOG.exists():
        replies = [json.loads(l) for l in REPLY_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
        by_ch = {}
        for r in replies:
            by_ch[r["channel"]] = by_ch.get(r["channel"], 0) + 1
        print(f"\nReplies logged: {len(replies)} {by_ch}")
    else:
        print("\nReplies logged: 0")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--send", action="store_true")
    p.add_argument("--channel", choices=["email", "linkedin", "instagram"], help="Single channel")
    p.add_argument("--all", action="store_true", help="All 3 channels")
    p.add_argument("--log-reply", action="store_true")
    p.add_argument("--lead-id", type=str)
    p.add_argument("--text", type=str)
    p.add_argument("--report", action="store_true")
    args = p.parse_args()

    if args.report:
        run_report()
    elif args.log_reply:
        if not (args.channel and args.lead_id and args.text):
            p.error("--log-reply needs --channel --lead-id --text")
        run_log_reply(args.channel, args.lead_id, args.text)
    elif args.send:
        channels = ["email", "linkedin", "instagram"] if args.all else (
            [args.channel] if args.channel else []
        )
        if not channels:
            p.error("--send needs --channel or --all")
        run_send(channels)
    else:
        p.print_help()


if __name__ == "__main__":
    main()