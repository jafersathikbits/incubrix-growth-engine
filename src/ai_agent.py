import json
import logging
import re
import time
from openai import OpenAI
from src.config import GROQ_API_KEYS, GROQ_MODEL, LOGS_DIR
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("incubrix.ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOGS_DIR / "engine.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(sh)

_EXHAUSTED_UNTIL = {}
_ROTATE_POINTER = 0

def _get_groq_client():
    global _ROTATE_POINTER
    if not GROQ_API_KEYS:
        return None, None
    now = time.time()
    n = len(GROQ_API_KEYS)
    for offset in range(n):
        idx = (_ROTATE_POINTER + offset) % n
        if _EXHAUSTED_UNTIL.get(idx, 0) > now:
            continue
        _ROTATE_POINTER = (idx + 1) % n
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEYS[idx],
            timeout=15.0,
            max_retries=0,
        )
        return client, idx
    
    # All keys are currently in timeout
    return None, None

def _parse_json_response(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Empty response from model")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())

def _fallback(recent_video_title, creator_name):
    logger.warning("Using fallback outreach template (all AI keys exhausted/rate limited)")
    return {
        "hook": f"Your recent video: {recent_video_title}.",
        "email": (
            f"Hi {creator_name},\n\n"
            f"Came across \"{recent_video_title}\". IncuBrix turns long-form content into "
            f"shorts, clips and blog drafts automatically, so one video becomes a week of posts.\n\n"
            f"Would a 15-min demo next week be worth it?\n\n"
            f"- Jafer Sathik B | IncuBrix Growth Engineer candidate\n"
            f"Reply STOP to opt out."
        ),
        "linkedin": (
            f"Hi {creator_name}, saw \"{recent_video_title}\". "
            f"IncuBrix helps creators repurpose long-form into shorts + written posts automatically. "
            f"Open to a quick chat? Reply STOP to opt out."
        ),
        "instagram": (
            f"Hey {creator_name}, came across \"{recent_video_title}\". "
            f"IncuBrix is built to help creators clip + repurpose long videos without editing pain. "
            f"Want a look? Reply STOP to opt out."
        ),
    }

def generate_personalized_outreach(creator_name, recent_video_title, channel_name):
    prompt = f"""
    You are an expert growth marketer for IncuBrix (an AI operating system for creators -
    turns long-form video into shorts, clips, blog drafts, captions, and cross-posting).

    Target creator: {creator_name} (channel: {channel_name})
    Recent video: "{recent_video_title}"

    Task:
    1. "hook": one sentence referencing the recent video specifically.
    2. "email": 60-80 word cold email. Reference the video, name the exact pain IncuBrix removes
       (editing / repurposing / consistency), one concrete CTA. End with:
       "Reply STOP to opt out."
    3. "linkedin": 30-40 word LinkedIn DM, professional tone, same hook. Include opt-out line.
    4. "instagram": 25-35 word Instagram DM, casual tone. Include opt-out line.

    Rules:
    - Address the creator by name ("{creator_name}"). No [Name] placeholders.
    - No made-up facts about them. Only use the video title.
    - No emojis in email. Emojis allowed in Instagram (max 1).
    - Return ONLY a valid JSON object with keys: hook, email, linkedin, instagram.

    CRITICAL: Output must be a single valid JSON object. No text before the opening brace. No text after the closing brace. No markdown fences. No explanations. Just the JSON object.
    """

    attempts = 0
    max_attempts = max(4, len(GROQ_API_KEYS) * 2)

    while attempts < max_attempts:
        client, key_idx = _get_groq_client()
        
        # If client is None, all keys are in a 60s timeout. Use fallback immediately.
        if client is None:
            return _fallback(recent_video_title, creator_name)

        attempts += 1
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            data = _parse_json_response(raw)
            required = {"hook", "email", "linkedin", "instagram"}
            if not required.issubset(data.keys()):
                raise ValueError(f"AI response missing keys: {required - set(data.keys())}")
            logger.info(
                f"AI OK: key_idx={key_idx} attempts={attempts} duration={time.time()-t0:.2f}s "
                f"creator='{creator_name}'"
            )
            return data

        except Exception as e:
            msg = str(e)
            dt = time.time() - t0

            if any(code in msg for code in ("429", "401", "403")) or "rate limit" in msg.lower():
                # 60-second timeout for this specific API key
                _EXHAUSTED_UNTIL[key_idx] = time.time() + 60
                logger.warning(
                    f"AI key_idx={key_idx} exhausted for 60s. Switching to fallback templates."
                )
                continue

            msg_lower = msg.lower()
            if any(kw in msg_lower for kw in ("expecting value", "json", "empty", "missing keys")):
                logger.warning(
                    f"AI JSON issue key_idx={key_idx} attempt {attempts} ({dt:.2f}s): {msg[:120]}. Retrying."
                )
                continue

            logger.error(f"AI unexpected error key_idx={key_idx} ({dt:.2f}s): {msg[:200]}")
            continue

    logger.warning(f"AI all attempts exhausted after {attempts} tries. Using fallback.")
    return _fallback(recent_video_title, creator_name)