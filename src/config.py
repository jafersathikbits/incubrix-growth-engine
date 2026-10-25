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

# 180+ High-Intent Keywords Targeting Monetized Creators
SEARCH_QUERIES = [
    # Broad Business & Marketing
    "business", "startup", "entrepreneur", "marketing", "sales", "coaching", 
    "mindset", "finance", "investing", "crypto", "real estate", "ecommerce", 
    "SaaS", "tech", "AI", "leadership", "career", "health", "fitness", 
    "wealth", "money", "passive income", "consulting", "freelance", 
    "productivity", "networking", "management", "strategy", "business growth",
    
    # Expert-Led / Coaching / Consulting Niches
    "business coach", "life coach", "executive coach", "health coach", 
    "fitness coach", "career coach", "mindset coach", "leadership coach", 
    "sales coach", "marketing coach", "business mentor", "life coaching", 
    "executive coaching", "coaching business", "coaching tips", "consulting business",
    "consulting tips", "freelance business", "freelance tips", "solopreneur",
    
    # Monetization & High-Ticket Creators
    "course creator", "online course", "digital products", "membership site",
    "mastermind", "group coaching", "high ticket", "business strategy", 
    "personal branding", "thought leadership", "keynote speaker", 
    "author podcast", "book launch", "startup marketing", "founder stories",
    
    # B2B, SaaS & Tech Founders
    "SaaS founder", "tech startup", "b2b marketing", "b2b sales", 
    "b2b founder", "founder led sales", "startup founder", "startup stories", 
    "venture capital", "product marketing", "growth marketing", "demand generation",
    
    # Content Creation & Repurposing (The Exact Problem IncuBrix Solves)
    "content creation", "content marketing", "content strategy", "content repurposing",
    "video marketing", "video creator", "video podcast", "podcast marketing", 
    "podcast host", "podcast coaching", "youtube marketing", "youtube coach", 
    "youtube growth", "social media marketing", "social media growth",
    
    # Finance & Real Estate (Highly Monetized)
    "financial advisor", "wealth management", "financial coaching", "real estate agent",
    "real estate investing", "real estate coaching", "mortgage broker", 
    "insurance agent", "cpa marketing", "accounting firm", "bookkeeping",
    
    # E-commerce & Product Creators
    "ecommerce business", "shopify store", "amazon fba", "dropshipping", 
    "print on demand", "etsy seller", "digital marketing", "email marketing",
    "funnel building", "lead generation", "affiliate marketing",
    
    # Specific Audiences (High Engagement)
    "female entrepreneur", "mompreneur", "christian entrepreneur", 
    "veteran entrepreneur", "young entrepreneur", "introvert entrepreneur",
    "side hustle", "remote work", "digital nomad",
    
    # Misc High-Converting
    "agency owner", "creator economy", "business tips", "marketing tips",
    "sales training", "sales tips", "business podcast", "marketing podcast",
    "sales podcast", "entrepreneur podcast", "business tips podcast"
]

EXCLUDE_KEYWORDS = [
    "agency", "management", "fan", "clips", "compilation",
    "network", "media", "productions", "radio", "news",
    "hindi", "urdu", "arabic", "espanol", "spanish", "french", "german"
]

def _warn_if_empty(name, value):
    if not value:
        print(f"[config] WARNING: {name} is empty. Check your .env file.")

_warn_if_empty("YOUTUBE_API_KEYS", YOUTUBE_API_KEYS)
_warn_if_empty("GROQ_API_KEYS", GROQ_API_KEYS)