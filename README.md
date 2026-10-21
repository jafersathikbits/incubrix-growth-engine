# IncuBrix Growth Engine (Assessment Submission)
**Built for the IncuBrix 2027 Growth Engineer Assessment (Option 1).**

An automated, multi-channel lead generation and outreach engine designed to discover creators with a "Shorts Deficit", verify their commercial intent, and draft hyper-personalized outreach using AI.

## The Qualification Engine (How we filter for high-quality leads)
To ensure 0% waste and maximum ROI, the engine applies 5 strict filters before a lead is saved:
1. **The Goldilocks Zone:** Rejects anyone under 5k (no budget) or over 100k (has an agency/team) subscribers.
2. **Activity Check:** Requires 8+ uploads in the last 30 days or 2 long-form videos in 60 days (using zero-quota RSS feeds).
3. **Language Check:** Scans video titles for Latin characters to ensure English-speaking markets.
4. **Commercial Intent:** Scans descriptions for monetization signals (Patreon, courses, sponsors, shops).
5. **Shorts Deficit:** Detects if the creator posts long-form content but zero Shorts, highlighting a massive need for IncuBrix.

## Key Features
* **Intelligent Discovery:** Finds active creators using the YouTube Data API with batched subscriber checks to save quota.
* **Multi-LLM Fallback:** Uses Gemini primarily, with automatic failover to Groq (GPT-OSS 120B) to ensure the engine never stops.
* **0% Duplicates:** Uses SHA-256 hashing in an SQLite database, allowing the engine to resume from crashes without losing progress.
* **Enterprise UI:** A clean Streamlit dashboard for live execution, dynamic filtering, and a Seed Test (live email delivery).

## Prerequisites
* Python 3.10+
* YouTube Data API v3 Key(s)
* Gemini API Key
* Groq API Key
* Gmail App Password (for the Seed Test feature)

## Installation & Setup

1. **Clone the repository:**
```bash
git clone <your-repo-link>
cd incubrix-growth-engine
```

2. **Set up a virtual environment:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Environment Variables:**
Rename `.env.example` to `.env` and fill in your keys:
```env
YT_KEY_1=your_youtube_api_key
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-flash-latest
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## The "One Clear Run Command"

### Option A: Run the Enterprise UI (Recommended)
To run the full visual dashboard, live Seed Test, and generate leads:
```bash
streamlit run app.py
```

### Option B: Run the CLI (Headless)
To run the engine directly from the terminal and save to `data/leads.csv`:
```bash
python main.py
```

## Running Tests
To run the unit tests for the deduplication and enrichment logic:
```bash
pytest tests/
```

## Architecture
* `app.py`: Streamlit UI and Seed Test sender.
* `main.py`: Core orchestration loop.
* `src/youtube_api.py`: API batching, RSS parsing, key rotation.
* `src/enrichment.py`: Email/contact regex, Commercial intent NLP.
* `src/database.py`: SQLite deduplication and state management.
* `src/ai_agent.py`: Gemini/Groq prompt engineering.