import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Load 6 YouTube Keys safely
YOUTUBE_API_KEYS = []
for i in range(1, 7):
    key = os.getenv(f"YT_KEY_{i}")
    if key:
        YOUTUBE_API_KEYS.append(key)

# API Keys & Models
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TARGET_COUNTRIES = {
    "US": 0.40, "GB": 0.20, "CA": 0.15, "AU": 0.10, "IE": 0.05, "NZ": 0.05, "SG": 0.05
}

SEARCH_QUERIES = [
    "business podcast", "tech coaching", "SaaS tutorial", "marketing consultant",
    "fitness coach business", "education creator", "startup podcast", "real estate coaching",
    "financial advisor podcast", "life coach tips", "mindset coach podcast", "coding tutorial",
    "AI tools review", "personal branding consultant", "copywriter tips", "web development tutorial",
    "product management podcast", "HR consultant podcast", "sales coaching tips", "ecommerce business podcast",
    "freelance designer tips", "video editing tutorial", "photography business podcast", "health coach podcast",
    "crypto investing podcast"
]

EXCLUDE_KEYWORDS = [
    "agency", "management", "fan", "clips", "compilation", 
    "network", "media", "productions", "radio", "hindi", "urdu", "arabic", "espanol"
]