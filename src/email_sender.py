import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, formataddr
import os
from dotenv import load_dotenv

load_dotenv()

def get_smtp_connection():
    """Establishes and returns a logged-in SMTP connection."""
    smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    if not sender_email or not password:
        return None

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender_email, password)
        return server
    except Exception as e:
        print(f"Failed to connect to SMTP: {e}")
        return None

def send_test_email(to_email, subject, body, server=None):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_name = os.getenv("SENDER_NAME", "IncuBrix Growth Engine")
    sender_title = os.getenv("SENDER_TITLE", "")

    if not sender_email:
        return False, "SMTP_EMAIL missing in .env"

    msg = MIMEMultipart()
    
    # --- FIX: Safely format the Name and Title ---
    if sender_title:
        display_name = f"{sender_name} | {sender_title}"
    else:
        display_name = sender_name
        
    msg['From'] = formataddr((display_name, sender_email))
    # ---------------------------------------------
    
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=sender_email.split('@')[-1])
    msg.attach(MIMEText(body, 'plain'))

    # --- FAST PATH: Reuse the existing connection ---
    if server:
        try:
            server.send_message(msg)
            return True, "Test email sent successfully (fast)!"
        except Exception as e:
            return False, str(e)

    # --- SLOW PATH: Fallback if no connection passed ---
    try:
        server = smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587")))
        server.starttls()
        server.login(sender_email, os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)
        server.quit()
        return True, "Test email sent successfully!"
    except Exception as e:
        return False, str(e)