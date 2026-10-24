def calculate_score(subscribers, has_email, has_social, video_count, has_money,
                    pain_signals=None, longform_count=0, short_count=0,
                    days_since_post=999, has_editor=False, engagement_ratio=0.0):
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
    if subscribers == 0:
        score += 5
    elif 10_000 <= subscribers <= 100_000:
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

    if has_editor:
        score -= 15

    # Engagement Tie-breaker (max 5 points)
    if engagement_ratio > 0.05:
        score += 5
    elif engagement_ratio > 0.02:
        score += 3
    elif engagement_ratio > 0.01:
        score += 1

    return max(0, min(100, score))


def determine_priority(score):
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    else:
        return "C"