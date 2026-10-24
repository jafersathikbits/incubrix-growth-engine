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

GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None

# ------------------------------------------------------------------
# Targeting
# ------------------------------------------------------------------
TARGET_COUNTRIES = {
    "US": 0.40, "GB": 0.20, "CA": 0.15, "AU": 0.10,
    "IE": 0.05, "NZ": 0.05, "SG": 0.05,
}

SEARCH_QUERIES = [
    # Base high-level
    "business", "startup", "entrepreneur", "marketing", "sales", "coaching", 
    "mindset", "finance", "investing", "crypto", "real estate", "ecommerce", 
    "SaaS", "tech", "AI", "leadership", "career", "life coach", "health", 
    "fitness", "wealth", "money", "passive income", "consulting", "agency", 
    "freelance", "productivity", "networking", "management", "strategy",
    
    # Expert-led & specific niches
    "business coach", "podcast", "creator", "consultant", "masterclass",
    "mentor", "digital marketing", "social media", "youtube", "content creation",
    "business tips", "marketing strategy", "sales training", 
    "coaching business", "life coaching", "executive coach", 
    "financial advisor", "wealth management", "real estate agent",
    "ecommerce business", "amazon fba", "dropshipping", 
    "saas founder", "tech startup", "ai tools", 
    "agency owner", "freelance business", "consulting business",
    "lead generation", "personal branding", "business growth", 
    "leadership podcast", "sales coaching", "agency growth", 
    "freelance tips", "consulting tips", "mastermind podcast", 
    "founder stories", "female entrepreneur", "b2b sales", 
    "marketing tips", "personal development", "wealth building", 
    "real estate investing", "course creator", "digital products", 
    "online business", "solopreneur", "startup stories", 
    "venture capital", "business strategy", "customer acquisition", 
    "email marketing", "social media marketing", "business podcast",
    
    # NEW: High-ticket, highly-monetized creators (Perfect for IncuBrix)
    "video podcast", "youtube marketing", "podcast marketing",
    "content strategy", "content repurposing", "video creator",
    "online coach", "business mentor", "course business",
    "membership podcast", "b2b marketing", "b2b founder",
    "founder led sales", "personal brand", "creator business",
    "podcast host", "youtube channel", "content marketing",
    "brand building", "thought leadership", "keynote speaker",
    "author podcast", "book launch", "startup marketing",
    "b2b podcast", "business podcast host", "online course creator",
    "youtube coach", "podcast coach", "video marketing"
]

EXCLUDE_KEYWORDS = [
    "agency", "management", "fan", "clips", "compilation",
    "network", "media", "productions", "radio",
    "hindi", "urdu", "arabic", "espanol",
]

def _warn_if_empty(name, value):
    if not value:
        print(f"[config] WARNING: {name} is empty. Check your .env file.")

_warn_if_empty("YOUTUBE_API_KEYS", YOUTUBE_API_KEYS)
_warn_if_empty("GROQ_API_KEYS", GROQ_API_KEYS)