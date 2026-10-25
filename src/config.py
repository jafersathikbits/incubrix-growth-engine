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

# 180+ Original Keywords + 500 New High-Intent Keywords
SEARCH_QUERIES = [
    # --- YOUR ORIGINAL KEYWORDS ---
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
    "sales podcast", "entrepreneur podcast", "business tips podcast",

    # --- 500 NEW HIGH-INTENT KEYWORDS ---
    "podcast", "podcasting", "podcast guest", "podcast interview", 
    "podcast editing", "podcast growth", "podcast monetization", "podcast studio", 
    "audio podcast", "business podcast", "finance podcast", "health podcast", 
    "fitness podcast", "tech podcast", "news podcast", "sports podcast", 
    "comedy podcast", "true crime podcast", "history podcast", "science podcast", 
    "education podcast", "entrepreneur podcast", "startup podcast", "relationship coach", 
    "wellness coach", "nutrition coach", "financial coach", "spiritual coach", 
    "parenting coach", "ADHD coach", "sober coach", "dating coach", "sleep coach", 
    "holistic coach", "trauma coach", "abundance coach", "manifestation coach", 
    "productivity coach", "intimacy coach", "breathwork coach", "somatic coach", 
    "keto coach", "carnivore coach", "vegan coach", "strength coach", "running coach", 
    "triathlon coach", "golf coach", "tennis coach", "mental coach", 
    "career advice", "career development", "career transition", "job interview", 
    "resume tips", "linkedin tips", "networking tips", "salary negotiation", 
    "digital nomad", "online course creator", "course creation", "coaching program", 
    "high ticket coaching", "high ticket offer", "online business", "infopreneur", 
    "expert business", "consultant", "coach business", "coaching tools", 
    "coaching software", "coaching certification", "coaching skills", "founder", 
    "small business", "agency owner", "freelancer", "creator", "influencer", 
    "YouTuber", "video creator", "content creator", "digital marketer", 
    "SEO expert", "social media manager", "copywriter", "email marketer", 
    "sales funnel", "B2B marketing", "DTC brand", "Amazon FBA seller", 
    "dropshipper", "real estate investor", "stock trader", "crypto investor", 
    "financial advisor", "wealth manager", "personal finance educator", 
    "health professional", "nutritionist", "dietitian", "therapist", 
    "psychologist", "fitness trainer", "personal trainer", "yoga instructor", 
    "wellness expert", "doctor", "nurse", "dentist", "chiropractor", 
    "physical therapist", "occupational therapist", "speech therapist", 
    "mental health counselor", "life transition", "divorce coach", "grief coach", 
    "empty nest", "midlife women", "menopause", "perimenopause", "hormone health", 
    "gut health", "thyroid health", "autoimmune disease", "chronic illness", 
    "weight loss", "fat loss", "muscle gain", "bodybuilding", "powerlifting", 
    "crossfit", "calisthenics", "marathon training", "ultra running", 
    "cycling", "swimming", "triathlon training", "ironman", "yoga", 
    "pilates", "barre", "dance fitness", "zumba", "boxing", "martial arts", 
    "jiu jitsu", "mma", "self defense", "meditation", "mindfulness", 
    "sound healing", "reiki", "acupuncture", "naturopathy", "functional medicine", 
    "integrative medicine", "crypto trading", "day trading", "options trading", 
    "forex trading", "futures trading", "swing trading", "value investing", 
    "dividend investing", "index funds", "ETF investing", "real estate investing", 
    "rental properties", "house flipping", "wholesaling", "commercial real estate", 
    "REITs", "financial independence", "FIRE movement", "retire early", 
    "budgeting", "debt payoff", "credit repair", "wealth building", 
    "money mindset", "abundance mindset", "law of attraction", "personal development", 
    "self improvement", "self help", "habit building", "atomic habits", 
    "morning routine", "productivity hacks", "time management", "focus", 
    "discipline", "motivation", "goal setting", "vision board", "journaling", 
    "stoicism", "philosophy", "psychology", "neuroscience", "human behavior", 
    "behavioral economics", "inbound marketing", "outbound marketing", 
    "growth hacking", "performance marketing", "affiliate marketing", 
    "influencer marketing", "brand marketing", "digital PR", "public relations", 
    "SEO", "local SEO", "technical SEO", "keyword research", "link building", 
    "content strategy", "brand strategy", "marketing strategy", "business strategy", 
    "sales strategy", "pricing strategy", "product strategy", "UX design", 
    "UI design", "graphic design", "web design", "web development", "app development", 
    "software engineering", "coding", "python", "javascript", "react", 
    "nodejs", "data science", "machine learning", "artificial intelligence", 
    "AI tools", "ChatGPT", "Midjourney", "prompt engineering", "no code", 
    "low code", "automation", "Zapier", "Make", "Airtable", "Notion", 
    "productivity software", "project management", "agile", "scrum", 
    "lean startup", "design thinking", "innovation", "management", "team building", 
    "remote team", "company culture", "HR", "recruiting", "talent acquisition", 
    "employee retention", "performance management", "public speaking", 
    "storytelling", "communication skills", "negotiation", "conflict resolution", 
    "networking", "relationship building", "emotional intelligence", "empathy", 
    "vulnerability", "confidence", "self esteem", "anxiety", "depression", 
    "burnout", "stress management", "trauma healing", "inner child", "shadow work", 
    "somatic therapy", "CBT", "DBT", "psychotherapy", "counseling", "life purpose", 
    "finding purpose", "ikigai", "passion", "creativity", "art", "music", 
    "writing", "photography", "videography", "filmmaking", "acting", "dance", 
    "theater", "singing", "songwriting", "music production", "beatmaking", 
    "DJing", "audio engineering", "mixing", "mastering", "podcast production", 
    "video editing", "color grading", "motion graphics", "animation", "VFX", 
    "3D modeling", "game design", "game development", "Unity", "Unreal Engine", 
    "esports", "streaming", "Twitch", "YouTube growth", "YouTube algorithm", 
    "YouTube SEO", "YouTube monetization", "sponsorships", "brand deals", 
    "passion economy", "solopreneurship", "digital business", "location independence", 
    "travel hacking", "van life", "RV living", "minimalism", "simple living", 
    "sustainability", "zero waste", "eco friendly", "climate change", 
    "renewable energy", "solar power", "electric vehicles", "cryptocurrency", 
    "blockchain", "web3", "NFTs", "DeFi", "metaverse", "virtual reality", 
    "augmented reality", "podcast agency", "podcast network", "b2b podcast", 
    "saas podcast", "founder podcast", "creator podcast", "marketing expert", 
    "sales expert", "startup mentor", "coaching platform", 
    "online coaching", "virtual coaching", "executive presence", "public speaking coach", 
    "presentation skills", "pitch deck", "investor pitch", "angel investing", 
    "bootstrapping", "bootstrapped founder", "product market fit", 
    "go to market strategy", "customer acquisition", "customer retention", 
    "churn reduction", "lifetime value", "SaaS metrics", "ARR", "MRR", 
    "startup funding", "seed round", "series a", "startup growth", "growth loops", 
    "referral marketing", "viral marketing", "community building", "discord community", 
    "slack community", "facebook group", "mastermind group", "peer to peer learning", 
    "cohort based course", "evergreen course", "course launch", "webinar funnel", 
    "lead magnet", "email list", "newsletter growth", "substack", "ghost", 
    "convertkit", "email sequence", "cold email", "cold outreach", "linkedin outreach", 
    "instagram outreach", "twitter growth", "tiktok growth", "instagram reels", 
    "youtube shorts", "linkedin creator", "twitter creator", "threads creator", 
    "personal brand", "brand building", "digital reputation", "thought leader", 
    "keynote speaking", "tedx speaker", "motivational speaker", "workshop facilitator", 
    "corporate trainer", "leadership trainer", "sales trainer", "diversity and inclusion", 
    "dei consultant", "career coach for women", "career coach for moms", 
    "executive coach for women", "leadership coach for women", "minority founder", 
    "black founder", "latino founder", "asian founder", "women in tech", 
    "women in business", "mompreneur", "dadpreneur", 
    "immigrant founder", "first time founder", "serial entrepreneur", 
    "second time founder", "solo founder", "technical founder", "non technical founder", 
    "product manager", "product owner", "scrum master", "agile coach", "engineering manager", 
    "vp of engineering", "cto", "chief product officer", "chief marketing officer", 
    "cmo", "vp of sales", "head of growth", "growth team", "marketing team", 
    "sales team", "customer success", "customer support", "ux researcher", "ui developer", 
    "frontend developer", "backend developer", "full stack developer", "data analyst", 
    "data engineer", "machine learning engineer", "ai researcher", "prompt engineer"
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