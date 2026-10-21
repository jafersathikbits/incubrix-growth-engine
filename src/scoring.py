def calculate_score(subscribers, has_email, has_social, video_count, has_money):
    score = 0
    
    # 1. Audience Size (Max 25) - Goldilocks Zone (10k-100k)
    if subscribers >= 10000 and subscribers <= 100000: 
        score += 25
    elif subscribers > 100000: 
        score += 10 
    else: 
        score += 15 # 5k-10k range

    # 2. Reachability (Max 30)
    if has_email: score += 25
    if has_social: score += 5
        
    # 3. Activity (Max 20)
    if video_count >= 8: score += 20
    elif video_count >= 4: score += 10
    
    # 4. Commercial Intent (Max 25)
    if has_money: score += 25
    
    return score

def determine_priority(score):
    if score >= 70: return "A"
    elif score >= 40: return "B"
    else: return "C"