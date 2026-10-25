# IncuBrix 2027 — Growth Engineer — Assessment

Finds → verifies → scores → drafts multi-channel outreach for podcasters, YouTube-first
creators, and expert-led creators in 7 approved English markets. Reruns weekly with
0% duplicates. Recovers from a single bad API key without stopping.

---

## Initial Setup

```bash
pip install -r requirements.txt
Create .env from .env.example and fill in:
YOUTUBE_API_KEYS, GROQ_API_KEY, SMTP_*, SENDER_NAME, SENDER_TITLE.

Run Command (one command)
bash
python main.py
Runs the engine end-to-end. Outputs:

data/production.db — SQLite source of truth

data/production_leads.csv — full qualified list (UTF-8)

data/production_priority_a.csv — Priority A only

outreach/priority_a/<lead_id>.md — 3 channels × 3 messages per Priority A lead

logs/engine.log — runtime log

Optional UI
bash
streamlit run app.py
Opens at http://localhost:8501 for visual browsing (used in the technical demo video).

Resume / Refresh
bash
python -m src.resume_main
Appends new leads to the existing DB (no duplicates), regenerates Priority A packs, re-exports CSV.

Tests
bash
pytest -q
Seed test (3-channel proof)
bash
python -m src.seed_test --send --all
python -m src.seed_test --report
text

**Block 2:**
```markdown
Uses test accounts from `.env` only. LinkedIn and Instagram messages are queued for manual send (platform rules forbid bulk automation).

---

## Runtime & cost (at 5,028 leads)

| Step | Time | Cost |
|---|---|---|
| YouTube search + channels.list | 30–45 min | ₹0 (free quota) |
| YouTube RSS fetches | 60–90 min | ₹0 |
| Groq LLM (Priority A ≈ 559) | 3–5 min | ~$0.10 |
| **Total** | **~2–3 hrs** | **< $0.20** |

---

## Failure recovery (demoable)

Every API call is wrapped. On a bad YouTube key (403/429), the engine rotates to the next key,
logs the rotation, and retries. On a Groq failure, it marks the key exhausted for 60s, rotates,
and falls back to a safe template if all keys fail — the pipeline never crashes.

**To prove it:** set `YT_KEY_1=bad_key` in `.env`, keep `YT_KEY_2=real_key`, run `python main.py`.

---

## Tools used (disclosure)

- **YouTube Data API v3** — channel search, stats (multi-key rotation)
- **YouTube public RSS feeds** — recent videos per channel
- **Groq API** — Llama-3.1-8b for personalised outreach drafts
- **Python:** `google-api-python-client`, `requests`, `pandas`, `openai`, `python-dotenv`, `streamlit`
- **SQLite** — local dedupe + resume
- **SMTP** — test email send

**AI usage:** GPT-based AI assisted code and message templates. Personalised message content is generated live by Groq from each lead's real recent video title. Every lead's evidence URL is stored in `production.db` and `production_leads.csv`.

---

## Compliance

- Public data only (channel title, description, subscriber count, public videos).
- Contact info comes only from the creator's own public channel description — never guessed.
- Every message includes sender identity + "Reply STOP to opt out."
- No automated messages sent on LinkedIn/Instagram. Human send only.
- India DPDP, GDPR, CAN-SPAM: legitimate-interest B2B outreach + opt-out + public-contact-only sourcing.

---

## Repository layout
.
├── main.py # entry point
├── app.py # optional Streamlit UI
├── README.md
├── PRODUCT_INSIGHTS.md
├── requirements.txt
├── .env.example
├── outreach/ # segment sequences + generated per-lead packs
├── src/
│ ├── config.py
│ ├── youtube_api.py
│ ├── enrichment.py
│ ├── scoring.py
│ ├── ai_agent.py
│ ├── outreach_gen.py
│ ├── database.py
│ ├── exporter.py
│ ├── email_sender.py
│ ├── seed_test.py
│ └── resume_main.py
└── tests/
└── test_engine.py
