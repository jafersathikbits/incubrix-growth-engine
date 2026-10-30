# IncuBrix Growth Engine

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-f55036?style=for-the-badge&logo=groq&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

An enterprise-grade, multi-channel lead generation and outreach engine built for the IncuBrix 2027 Growth Engineer Assessment. 

This system automates the discovery, verification, scoring, and multi-channel outreach drafting for high-value creators across 7 English markets. It operates at scale while maintaining strict compliance and minimizing runtime costs.

---

## Core Capabilities

### Automated Lead Discovery & Enrichment
*   **Multi-Platform Crawling:** Utilizes the YouTube Data API v3 and podcast RSS feeds to discover creators across targeted niches.
*   **Automated Verification:** Validates channel data, checks recent activity, verifies language constraints, and extracts contact information.
*   **Priority Scoring:** Implements a deterministic scoring algorithm to rank leads into Priority A/B/C tiers based on commercial intent, audience size, and recent content output.

### AI-Powered Multi-Channel Outreach
*   **Dual-LLM Strategy:** Leverages the Groq API (Llama-3) to generate personalized, context-aware outreach messages based on each creator's recent video titles.
*   **Multi-Channel Sequences:** Automatically drafts customized messages for Email, LinkedIn, and Instagram (3 messages per channel for Priority A leads).
*   **Cost Optimization:** Processes thousands of leads in hours for a negligible runtime cost (under $0.20 for 5,000+ leads), leveraging free API quotas and highly efficient LLM routing.

### Enterprise-Grade Reliability
*   **API Failover Logic:** Implements a robust multi-key rotation mechanism. The pipeline automatically rotates to backup API keys if rate limits are hit or if a key is exhausted, ensuring the engine never crashes mid-run.
*   **Deduplication & State Management:** Utilizes a local SQLite database to track processed leads, ensuring a 0% duplicate rate on subsequent weekly runs and allowing resumable execution.
*   **Visual Management:** Includes a Streamlit-based user interface for visual inspection, filtering, and manual review of generated outreach drafts.

---

## Technical Architecture Highlights

*   **Sequential Pipeline:** The system executes a strict sequence: Discovery -> Verification -> Scoring -> AI Generation -> Export.
*   **Fault Tolerance:** The `src/ai_agent.py` module includes a custom timeout and rotation logic (`_EXHAUSTED_UNTIL`). If an API key fails, it marks the key as exhausted for 60 seconds, rotates to the next available key, and falls back to safe, pre-written templates if all keys fail simultaneously.
*   **Data Compliance:** Enforces strict data privacy by utilizing only publicly available data. Includes automated opt-out language ("Reply STOP to opt out") in all generated messages and strictly avoids unauthorized bulk automation on platforms that forbid it.
*   **Deterministic Scoring:** The `src/scoring.py` module evaluates leads based on weighted criteria: capacity gaps (subscriber count), monetization signals (presence of keywords like "sponsor" or "course"), and activity levels.

---

## Technology Stack

*   **Language:** Python 3.10+
*   **User Interface:** Streamlit
*   **AI/LLM Providers:** Groq (Llama-3)
*   **Data Sources:** YouTube Data API v3, public RSS feeds
*   **Database:** SQLite
*   **Communication:** SMTP (for email validation and dispatch)

---

## Local Setup & Installation

### 1. Prerequisites
*   Python 3.10+
*   API Keys for YouTube Data API v3 and Groq.

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/jafersathikbits/incubrix-growth-engine.git
cd incubrix-growth-engine

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory and add your API credentials:
```env
# YouTube Data API keys (comma separated for rotation)
YOUTUBE_API_KEYS=key1,key2

# Groq LLM API keys (comma separated for rotation)
GROQ_API_KEY=your_groq_key

# Sender identity
SENDER_NAME=Jafer Sathik B
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 4. Running the Application
To run the visual management interface:
```bash
streamlit run app.py
```
This will launch the Streamlit dashboard in your browser at `http://localhost:8501`.

To run the engine headless via the terminal:
```bash
python main.py
```

---

## Performance Metrics (Assessment Run)

| Metric | Result |
| :--- | :--- |
| **Total Leads Processed** | 5,028 |
| **Runtime Cost** | < $0.20 |
| **Execution Time** | ~ 2 to 3 hours |
| **Deduplication Rate** | 0% duplicates on weekly reruns |
| **System Uptime** | 100% (survived multiple API key failures via failover) |

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
**Author:** [Jafer Sathik B](https://github.com/jafersathikbits)
