def calculate_score(subscribers, has_email, has_social, video_count, has_money,
                    pain_signals=None, longform_count=0, short_count=0,
                    days_since_post=999, has_editor=False):
    score = 0
    pain_signals = pain_signals or []

    # Pain (max 35)
    if longform_count >= 3 and short_count == 0:
        score += 35
    elif pain_signals:
        score += 25
    elif longform_count > 0 and short_count < longform_count:
        score += 10

    # Capacity gap (max 20)
    if 10_000 <= subscribers <= 100_000:
        score += 20
    elif 5_000 <= subscribers < 10_000:
        score += 12
    elif 100_000 < subscribers <= 200_000:
        score += 10
    elif subscribers > 200_000:
        score += 5

    if has_money:
        score += 25

    if has_email:
        score += 15
    elif has_social:
        score += 5

    if days_since_post <= 7:
        score += 5
    elif days_since_post <= 14:
        score += 3

    # Anti-signal: already has an editor (they don't need IncuBrix as much)
    if has_editor:
        score -= 15

    return max(0, min(100, score))


def determine_priority(score):
    # A threshold is a HINT; final A cap applied in main.py (250 max).
    if score >= 85:
        return "A"
    elif score >= 60:
        return "B"
    else:
        return "C"