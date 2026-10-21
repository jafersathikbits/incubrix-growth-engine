import time
from src.database import init_db, is_duplicate, insert_lead
from src.youtube_api import YouTubeClient
from src.enrichment import find_email_from_description, extract_socials_from_text, check_commercial_and_need
from src.ai_agent import generate_personalized_outreach
from src.scoring import calculate_score, determine_priority
from src.config import SEARCH_QUERIES, TARGET_COUNTRIES
from src.exporter import export_to_csv

def run_engine(limit=6000, custom_queries=None, filter_commercial=True, 
               min_subs=5000, max_subs=100000, min_vids_30d=8, min_vids_60d=2, english_only=True):
    print("Initializing Database...")
    init_db()
    
    print("Initializing YouTube Client...")
    yt = YouTubeClient()
    
    leads_processed = 0
    queries_to_run = custom_queries if custom_queries else SEARCH_QUERIES
    
    for country_code, _ in TARGET_COUNTRIES.items():
        for query in queries_to_run:
            if leads_processed >= limit:
                print(f"Reached limit of {limit} leads. Stopping engine run.")
                return

            print(f"Searching '{query}' in {country_code}...")
            channels = yt.search_channels(query, country_code)
            
            if not channels:
                continue
                
            # BATCH STATS: Get all subscriber counts in ONE API call to save quota
            channel_ids = [ch['channel_id'] for ch in channels]
            stats_batch = yt.get_multiple_channel_stats(channel_ids)
            
            for channel in channels:
                if leads_processed >= limit:
                    return

                channel_id = channel['channel_id']
                sub_count = stats_batch.get(channel_id, 0)
                
                if is_duplicate(channel_id):
                    continue
                
                print(f"  -> Checking activity for: {channel['title']}")
                
                activity_data = yt.check_channel_activity(
                    channel_id, 
                    sub_count, # Passed in from the batch API call
                    min_subs=min_subs, 
                    max_subs=max_subs, 
                    min_vids_30d=min_vids_30d, 
                    min_vids_60d=min_vids_60d, 
                    english_only=english_only
                )
                
                if not activity_data or activity_data.get('status') == 'Rejected':
                    print(f"     -> Rejected: {activity_data.get('reason', 'Unknown')}")
                    continue

                all_descriptions = " ".join([(v.get('description') or "") for v in activity_data['videos']])
                recent_video = activity_data['videos'][0]
                
                email = find_email_from_description(all_descriptions)
                socials = extract_socials_from_text(all_descriptions)
                
                commercial = check_commercial_and_need(
                    all_descriptions, 
                    activity_data['longform_count'], 
                    activity_data['short_count']
                )
                
                if filter_commercial and not commercial['has_money']:
                    print("     -> Rejected: No commercial/monetization signal found.")
                    continue
                
                if email:
                    best_channel, handle = "Email", email
                elif socials['linkedin']:
                    best_channel, handle = "LinkedIn", socials['linkedin']
                elif socials['instagram']:
                    best_channel, handle = "Instagram", socials['instagram']
                else:
                    print("     -> Rejected: No contact info found.")
                    continue
                
                score = calculate_score(
                    subscribers=activity_data['subscribers'],
                    has_email=bool(email),
                    has_social=bool(socials['linkedin'] or socials['instagram']),
                    video_count=activity_data['count_30d'],
                    has_money=commercial['has_money']
                )
                
                # Give bonus points for Shorts Deficit
                if "High Priority" in commercial['incubrix_need']:
                    score = min(100, score + 10)
                    
                priority = determine_priority(score)
                
                print(f"     -> Generating AI outreach (Score: {score}, Priority: {priority})...")
                ai_data = generate_personalized_outreach(
                    creator_name=channel['title'],
                    recent_video_title=recent_video['title'],
                    channel_name=channel['title']
                )
                
                # Failsafe: Replace hallucinated placeholders with the real channel name
                safe_name = channel['title']
                hook = ai_data.get('hook', '').replace("[Name]", safe_name).replace("[Creator]", safe_name)
                email_msg = ai_data.get('email', '').replace("[Name]", safe_name).replace("[Creator]", safe_name)
                linkedin_msg = ai_data.get('linkedin', '').replace("[Name]", safe_name).replace("[Creator]", safe_name)
                
                lead_data = {
                    'stable_creator_id': channel_id,
                    'creator_name': channel['title'],
                    'country_iso2': country_code,
                    'primary_platform': 'YouTube',
                    'profile_url': f"https://youtube.com/channel/{channel_id}",
                    'followers_or_subscribers': activity_data['subscribers'],
                    'last_content_date': recent_video['published_at'],
                    'recent_content_url': f"https://youtube.com/watch?v={recent_video['video_id']}",
                    'content_count_30d': activity_data['count_30d'], 
                    'longform_count_60d': activity_data['longform_count'], 
                    'monetization_signal': commercial['monetization_signal'],
                    'monetization_evidence_url': f"https://youtube.com/watch?v={recent_video['video_id']}",
                    'incubrix_need': commercial['incubrix_need'],
                    'need_evidence_url': f"https://youtube.com/watch?v={recent_video['video_id']}",
                    'best_channel': best_channel,
                    'channel_handle_or_url': handle,
                    'backup_channel': 'Instagram' if socials['instagram'] else 'LinkedIn',
                    'personalization_hook': hook,
                    'first_message': email_msg if best_channel == 'Email' else linkedin_msg,
                    'checked_date': time.strftime('%Y-%m-%d'),
                    'priority': priority,
                    'lead_score': score,
                    'candidate_status': 'Qualified',
                    'duplicate_check': 'UNIQUE',
                    'completeness_check': 'COMPLETE'
                }
                
                insert_lead(lead_data)
                leads_processed += 1
                print(f"     -> SUCCESS! Saved {channel['title']} (Need: {commercial['incubrix_need']}).")
                
                time.sleep(1)

if __name__ == "__main__":
    try:
        # Set to 6000 for a safe buffer above the 5000 Exceptional Tier
        run_engine(limit=6000) 
    except Exception as e:
        print(f"\n[NOTICE] Engine stopped early: {e}")
    finally:
        print("Exporting to CSV...")
        export_to_csv()