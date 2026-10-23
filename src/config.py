import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


# ------------------------------------------------------------------
# YouTube API keys (multi-key rotation)
# Supported .env styles:
#   YT_KEY_1=xxx, YT_KEY_2=yyy, ...
#   YOUTUBE_API_KEYS=xxx,yyy,zzz
# ------------------------------------------------------------------
YOUTUBE_API_KEYS = []
for i in range(1, 21):
    key = os.getenv(f"YT_KEY_{i}")
    if key:
        YOUTUBE_API_KEYS.append(key.strip())

if not YOUTUBE_API_KEYS:
    yt_raw = os.getenv("YOUTUBE_API_KEYS", "")
    YOUTUBE_API_KEYS = [k.strip() for k in yt_raw.split(",") if k.strip()]


# ------------------------------------------------------------------
# Gemini
# ------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")


# ------------------------------------------------------------------
# Groq (multi-key rotation)
# Supported .env styles:
#   GROQ_KEY_1=xxx, GROQ_KEY_2=yyy, ...
#   GROQ_API_KEYS=xxx,yyy,zzz
#   GROQ_API_KEY=xxx            (single key, still works)
# ------------------------------------------------------------------
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

GROQ_API_KEYS = []
for i in range(1, 21):
    key = os.getenv(f"GROQ_KEY_{i}")
    if key:
        GROQ_API_KEYS.append(key.strip())

if not GROQ_API_KEYS:
    groq_raw = os.getenv("GROQ_API_KEYS", "") or os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEYS = [k.strip() for k in groq_raw.split(",") if k.strip()]

# Backwards-compatible single key alias (some modules may import this)
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None


# ------------------------------------------------------------------
# Targeting
# ------------------------------------------------------------------
TARGET_COUNTRIES = {
    "US": 0.40, "GB": 0.20, "CA": 0.15, "AU": 0.10,
    "IE": 0.05, "NZ": 0.05, "SG": 0.05,
}

SEARCH_QUERIES = [
    "business podcast", "startup podcast", "entrepreneur interview",
    "finance podcast", "investing podcast", "crypto podcast",
    "real estate investing", "financial advisor", "wealth building podcast",
    "stock market podcast", "passive income podcast",
    "life coach tips", "business coach", "mindset coach", "career coaching",
    "sales coaching", "fitness coach business", "health coach podcast",
    "marketing consultant", "executive coach", "leadership coaching",
    "relationship coach", "dating coach",
    "SaaS tutorial", "coding tutorial", "web development tutorial",
    "AI tools review",
]

EXCLUDE_KEYWORDS = [
    "agency", "management", "fan", "clips", "compilation",
    "network", "media", "productions", "radio",
    "hindi", "urdu", "arabic", "espanol",
]


# ------------------------------------------------------------------
# Small startup sanity check (prints warnings, does not crash)
# ------------------------------------------------------------------
def _warn_if_empty(name, value):
    if not value:
        print(f"[config] WARNING: {name} is empty. Check your .env file.")

_warn_if_empty("YOUTUBE_API_KEYS", YOUTUBE_API_KEYS)
_warn_if_empty("GROQ_API_KEYS", GROQ_API_KEYS)