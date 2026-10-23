import re


def find_email_from_description(description_text):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, description_text or "")
    valid = [e for e in emails if not e.endswith(('.png', '.jpg', '.webp', '.gif'))]
    return valid[0] if valid else None


def extract_socials_from_text(description_text):
    text = description_text or ""
    linkedin = re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', text)
    instagram = re.search(r'instagram\.com/[a-zA-Z0-9_.]+', text)
    return {
        "linkedin": f"https://www.{linkedin.group(0)}" if linkedin else None,
        "instagram": f"https://www.{instagram.group(0)}" if instagram else None,
    }


MONEY_KEYWORDS = [
    "patreon", "sponsor", "sponsored", "course", "consulting", "consult",
    "merch", "shop", "masterclass", "teachable", "membership", "hire me",
    "coaching", "work with me", "book a call", "1:1", "one-on-one",
    "join my", "my program", "my course", "my mentorship",
]

# HIRING patterns — only signals they're LOOKING for help
HIRING_PATTERNS = [
    r"\bhiring (an? )?editor\b",
    r"\blooking for (an? )?editor\b",
    r"\bneed (an? )?editor\b",
    r"\bseeking (an? )?editor\b",
    r"\bwant (an? )?editor\b",
    r"\bstruggl\w* (to|with) edit",
    r"\bno time to edit\b",
    r"\bhelp (me )?(with )?edit(ing)?\b",
]

# HAS-EDITOR patterns — they already have one (weak anti-signal)
HAS_EDITOR_PATTERNS = [
    r"\bedited by\b",
    r"\bvideo editor[:\s]",
    r"\beditor[:\s]",
    r"\bediting by\b",
    r"\bcredit[s]?:.*editor\b",
    r"\bthanks? (to )?(my|our) editor\b",
]


def check_commercial_and_need(description_text, longform_count, short_count):
    text = (description_text or "").lower()

    found_money = [kw for kw in MONEY_KEYWORDS
                   if re.search(r"\b" + re.escape(kw) + r"\b", text)]

    has_editor = any(re.search(p, text) for p in HAS_EDITOR_PATTERNS)
    is_hiring_editor = any(re.search(p, text) for p in HIRING_PATTERNS)

    pain_signals = []
    # Only add "seeking editing help" if they're HIRING and don't already have one
    if is_hiring_editor and not has_editor:
        pain_signals.append("actively seeking editing help")

    # Structural pain: many long-form, no Shorts (real signal, from real durations)
    if longform_count >= 3 and short_count == 0:
        pain_signals.append("long-form only, zero Shorts")
    elif longform_count >= 2 and short_count < longform_count:
        pain_signals.append("heavy long-form, minimal clips")

    if re.search(r"\b(backlog|behind on|catch up on|weeks behind)\b", text):
        pain_signals.append("backlog mentioned")

    # Decide need
    if longform_count >= 3 and short_count == 0:
        need = "High: Long-form backlog, zero Shorts"
    elif pain_signals:
        need = "High: " + pain_signals[0]
    elif longform_count > 0 and short_count > 0 and short_count < longform_count:
        need = "Medium: Repurposing improving"
    else:
        need = "None"

    return {
        "has_money": len(found_money) > 0,
        "monetization_signal": found_money[0] if found_money else "None",
        "incubrix_need": need,
        "pain_signals": pain_signals,
        "has_real_need": need.startswith("High") or need.startswith("Medium"),
        "has_editor": has_editor,
    }