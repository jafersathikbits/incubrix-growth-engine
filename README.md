# IncuBrix 2027 - Growth Engineer - Assessment

Finds -> verifies -> scores -> drafts multi-channel outreach for podcasters, YouTube-first creators, and expert-led creators in 7 approved English markets. Reruns weekly with 0% duplicates. Recovers from a single bad API key without stopping.

---

## Initial Setup

pip install -r requirements.txt

Create .env from .env.example and fill in:
YOUTUBE_API_KEYS, GROQ_API_KEYS, SMTP_*, SENDER_NAME, SENDER_TITLE.

---

## Run Command (one command)

python main.py

Runs the engine end-to-end. Outputs:

- data/production.db - SQLite source of truth
- data/production_leads.csv - full qualified list (UTF-8)
- data/production_priority_a.csv - Priority A only
- outreach/priority_a/<lead_id>.md - 3 channels x 3 messages per Priority A lead
- logs/engine.log - runtime log

### Optional UI

streamlit run app.py

Opens at http://localhost:8501 for visual browsing.

### Resume / Refresh

python -m src.resume_main

Appends new leads to the existing DB (no duplicates), regenerates Priority A packs, re-exports CSV.

### Tests

pytest -q

### Seed test (3-channel proof)

python -m src.seed_test --send --all
python -m src.seed_test --report

Uses test accounts from .env only. LinkedIn and Instagram messages are queued for manual send (platform rules forbid bulk automation).

---

## Runtime & cost (at 6,000 leads)

| Step | Time | Cost (Free Test) | Cost (Production) |
|---|---|---|---|
| YouTube search + channels.list | 30-45 min | INR 0 (free quota) | ~INR 0 (requires quota extension) |
| YouTube RSS fetches | 60-90 min | INR 0 | INR 0 |
| Groq LLM (Priority A approx. 250) | 3-5 min | ~$0.10 (~INR 8) | ~$2.00 (~INR 166) |
| **Total** | **~2-3 hrs** | **< $0.20 (< INR 16)** | **~$2.00 (~INR 166)** |

Note: The free API tiers are only suitable for local testing. Production requires a paid Groq tier to bypass rate limits, and a dedicated email sending tool (e.g., Instantly.ai) to prevent spam filtering.

---

## Failure recovery (demoable)

Every API call is wrapped. On a bad YouTube key (403/429), the engine rotates to the next key, logs the rotation, and retries. On a Groq failure, it marks the key exhausted for 60s, rotates, and falls back to a safe template if all keys fail - the pipeline never crashes.

To prove it: set YT_KEY_1=bad_key in .env, keep YT_KEY_2=real_key, run python main.py.

---

## Tools used (disclosure)

- YouTube Data API v3 - channel search, stats (multi-key rotation)
- YouTube public RSS feeds - recent videos per channel
- Groq API - Llama-3 for personalised outreach drafts
- Python: google-api-python-client, requests, pandas, openai, python-dotenv, streamlit
- SQLite - local dedupe + resume
- SMTP - test email send

AI usage: DeepSeek and GPT-based AI assisted code generation and message templates. Personalised message content is generated live by Groq from each lead's real recent video title. Every lead's evidence URL is stored in production.db and production_leads.csv.

---

## Compliance

- Public data only (channel title, description, subscriber count, public videos).
- Contact info comes only from the creator's own public channel description - never guessed.
- Every message includes sender identity + "Reply STOP to opt out."
- No automated messages sent on LinkedIn/Instagram. Human send only.
- India DPDP, GDPR, CAN-SPAM: legitimate-interest B2B outreach + opt-out + public-contact-only sourcing.

---

## Repository layout

.
|-- main.py                     # entry point
|-- app.py                      # optional Streamlit UI
|-- README.md
|-- PRODUCT_INSIGHTS.md
|-- requirements.txt
|-- .env.example
|-- outreach/                   # segment sequences + generated per-lead packs
|-- src/
|   |-- config.py
|   |-- youtube_api.py
|   |-- enrichment.py
|   |-- scoring.py
|   |-- ai_agent.py
|   |-- outreach_gen.py
|   |-- database.py
|   |-- exporter.py
|   |-- email_sender.py
|   |-- seed_test.py
|   |-- resume_main.py
|-- tests/
    |-- test_engine.py
