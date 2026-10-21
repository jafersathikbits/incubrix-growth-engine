import re

def find_email_from_description(description_text):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, description_text)
    valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.webp'))]
    return valid_emails[0] if valid_emails else None

def extract_socials_from_text(description_text):
    linkedin = re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', description_text)
    instagram = re.search(r'instagram\.com/[a-zA-Z0-9_.]+', description_text)
    
    return {
        "linkedin": f"https://www.{linkedin.group(0)}" if linkedin else None,
        "instagram": f"https://www.{instagram.group(0)}" if instagram else None
    }

def check_commercial_and_need(description_text, longform_count, short_count):
    text = description_text.lower()
    
    money_keywords = ["patreon", "sponsor", "course", "consulting", "merch", "shop", "book", "masterclass", "teachable", "membership", "hire me"]
    found_money = [kw for kw in money_keywords if kw in text]
    
    monetization_signal = found_money[0] if found_money else "None"
    
    # Determine IncuBrix Need based on content strategy
    if longform_count >= 2 and short_count == 0:
        incubrix_need = "High Priority: Shorts Deficit (Long-form only)"
        need_evidence = True
    elif longform_count > 0 and short_count > 0:
        incubrix_need = "Medium Priority: Optimize Repurposing"
        need_evidence = True
    else:
        incubrix_need = "General Content"
        need_evidence = False
    
    return {
        "has_money": len(found_money) > 0,
        "monetization_signal": monetization_signal,
        "incubrix_need": incubrix_need,
        "has_need_evidence": need_evidence
    }