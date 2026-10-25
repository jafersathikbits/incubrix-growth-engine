import time
import argparse
import json
import os
import re
import sqlite3
import requests
import hashlib
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.database import init_db, is_duplicate, insert_lead
from src.youtube_api import YouTubeClient
from src.enrichment import find_email_from_description, extract_socials_from_text, check_commercial_and_need
from src.ai_agent import generate_personalized_outreach
from src.outreach_gen import generate_priority_a_pack
from src.scoring import calculate_score, determine_priority
from src.config import SEARCH_QUERIES, TARGET_COUNTRIES, DATA_DIR, LOGS_DIR, EXCLUDE_KEYWORDS
from src.exporter import export_to_csv

APPROVED_COUNTRIES = {"US", "CA", "GB", "IE", "AU", "NZ", "SG"}
COUNTRY_CAP_RATIO = 0.55
NICHE_RE = re.compile(r"podcast|coach|mentor|course|consult|newsletter|creator|business|expert|tutorial", re.I)

NON_APPROVED_LANGUAGE_MARKERS = (
    "kannada", "hindi", "tamil", "telugu", "malayalam", "marathi", "gujarati",
    "punjabi", "bhojpuri", "odia", "assamese", "nepali", "urdu", "bangla",
    "bengali", "sinhala", "pashto", "mandarin", "cantonese", "tagalog",
    "bahasa", "swahili", "yoruba", "hausa", "amharic", "zulu",
    "español", "deutsch", "français", "italiano", "português", "nederlands", "polski",
)

PUBLICATION_NAMES = (
    "wall street journal", "wsj", "bloomberg", "reuters", "financial times", "the economist", 
    "forbes", "business insider", "cnbc", "cnn", "bbc news", "the new york times", 
    "new york times", "washington post", "the washington post", "the guardian", 
    "the telegraph", "financial review", "australian financial review", "afr", 
    "pushkin industries", "pushkin", "the times", "the sunday times", "anderson cooper", "stuff you missed"
)

PUBLICATION_EMAIL_DOMAINS = (
    "@wsj.com", "@bloomberg.net", "@reuters.com", "@ft.com", "@economist.com", "@forbes.com", 
    "@businessinsider.com", "@cnbc.com", "@cnn.com", "@nytimes.com", "@washingtonpost.com",
    "@theguardian.com", "@telegraph.co.uk", "@afr.com", "@smh.com.au", "@pushkin.fm", 
    "@npr.org", "@bbc.co.uk", "@howstuffworks.com"
)

STATE_FILE = DATA_DIR / "engine_state.json"
PODCAST_STATE_FILE = DATA_DIR / "podcast_state.json"

def _extract_email_from_xml(xml_text):
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.endswith('email') and elem.text:
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', elem.text)
                if emails: return emails[0]
    except Exception:
        pass
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', xml_text)
    valid = [e for e in emails if not e.endswith(('.png', '.jpg', '.webp', '.gif'))]
    return valid[0] if valid else None

def _classify_youtube_segment(title, desc):
    blob = (title + " " + desc).lower()
    if any(w in blob for w in ["coach", "consult", "expert", "course", "masterclass", "mentor", "training"]):
        return "Expert-led"
    if "podcast" in blob or "episode" in blob:
        return "Podcaster"
    return "YouTube-first"

def _get_rss_stats_and_segment(xml_text, name):
    count_30d = 0
    latest_date = "Unknown"
    text_lower = xml_text.lower()
    name_lower = name.lower()
    
    try:
        root = ET.fromstring(xml_text)
        now = datetime.now(timezone.utc)
        for item in root.findall('.//item'):
            pubDate = item.find('pubDate')
            if pubDate is not None and pubDate.text:
                try:
                    dt = datetime.strptime(pubDate.text[:25], "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
                    if latest_date == "Unknown": latest_date = dt.isoformat()
                    if (now - dt).days <= 30: count_30d += 1
                except: pass
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            pub = entry.find('{http://www.w3.org/2005/Atom}published')
            if pub is not None and pub.text:
                try:
                    dt = datetime.fromisoformat(pub.text.replace("Z", "+00:00"))
                    if latest_date == "Unknown": latest_date = dt.isoformat()
                    if (now - dt).days <= 30: count_30d += 1
                except: pass
    except Exception:
        pass
    
    if count_30d == 0: count_30d = 0 

    expert_words = ("coach", "consult", "expert", "mentor", "teacher", "academy", "course", "mastermind", "training")
    if any(w in name_lower for w in expert_words) or "course" in text_lower or "masterclass" in text_lower:
        segment = "Expert-led"
        monetization = "course"
    elif "podcast" in name_lower or "episode" in text_lower:
        segment = "Podcaster"
        monetization = "sponsor"
    else:
        segment = "YouTube-first"
        monetization = "sponsor"

    return count_30d, latest_date, segment, monetization

def run_podcast_scraper(db_path, queries, segment_filter, limit=5000, english_only=True, filter_commercial=True, min_podcast_episodes=0):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads WHERE primary_platform='Podcast'")
    existing_podcasts = cursor.fetchone()[0]
    
    if existing_podcasts >= limit:
        print(f"[SCRAPER] Already have {existing_podcasts} podcast leads. Skipping.")
        conn.close()
        return

    print(f"[SCRAPER] Starting iTunes scrape using your queries. Target: {limit} (Current: {existing_podcasts})")
    leads_found = existing_podcasts
    seen_emails = set()

    terms_to_search = queries if queries else SEARCH_QUERIES
    
    if segment_filter == "Expert-led" and not queries:
        terms_to_search = ["coaching", "consulting", "business coach", "masterclass", "mentor"]

    itunes_countries = ["us", "gb", "ca", "au", "ie", "nz", "sg"]
    
    state = _load_podcast_state()
    searched_combos = set(state.get("searched", []))

    for term in terms_to_search:
        if leads_found >= limit: break
        for itunes_cc in itunes_countries:
            if leads_found >= limit: break
            
            combo = f"{term}_{itunes_cc}"
            if combo in searched_combos:
                continue
                
            print(f"  -> Searching iTunes ({itunes_cc.upper()}) for: {term}")
            url = f"https://itunes.apple.com/search?term={term}&country={itunes_cc}&limit=200&entity=podcast"
            
            try:
                resp = requests.get(url, timeout=10).json()
                for result in resp.get("results", []):
                    if leads_found >= limit: break
                    
                    feed_url = result.get("feedUrl")
                    if not feed_url: continue
                    
                    try:
                        rss_resp = requests.get(feed_url, timeout=5)
                        xml_text = rss_resp.text
                        
                        email = _extract_email_from_xml(xml_text)
                        if email and email.lower() not in seen_emails:
                            name = result.get("collectionName", "Unknown Podcast")
                            
                            name_lower = name.lower()
                            if any(kw in name_lower for kw in EXCLUDE_KEYWORDS):
                                continue

                            if is_publication(name, email):
                                continue

                            count_30d, latest_date, segment, mon_signal = _get_rss_stats_and_segment(xml_text, name)
                            
                            # --- PODCAST FILTER ---
                            if count_30d < min_podcast_episodes:
                                continue
                            # ----------------------
                            
                            if segment_filter != "All" and segment != segment_filter:
                                continue
                                
                            if english_only:
                                text_lower = xml_text.lower()
                                if any(lang in text_lower for lang in NON_APPROVED_LANGUAGE_MARKERS):
                                    continue
                                
                            commercial = {"has_money": True, "monetization_signal": "sponsor", "pain_signals": []}
                            if filter_commercial:
                                commercial = check_commercial_and_need(xml_text, count_30d, 0)
                                if not commercial["has_money"]:
                                    continue
                                mon_signal = commercial["monetization_signal"]

                            seen_emails.add(email.lower())
                            stable_id = hashlib.sha256(feed_url.encode('utf-8')).hexdigest()
                            
                            score = calculate_score(
                                subscribers=0, has_email=True, has_social=False, video_count=count_30d, 
                                has_money=commercial["has_money"], 
                                pain_signals=commercial.get("pain_signals", []), 
                                longform_count=count_30d, short_count=0, days_since_post=7, has_editor=False
                            )
                            
                            priority = determine_priority(score)

                            if count_30d > 4:
                                need = f"High: {count_30d} recent episodes, needs repurposing."
                                first_msg = f"Hi {name}, noticed you have {count_30d} recent episodes. IncuBrix turns long audio into shorts and captions automatically. Reply STOP to opt out."
                            else:
                                need = "Medium: Long-form backlog, needs clips."
                                first_msg = f"Hi {name}, came across your podcast. IncuBrix turns long episodes into shorts and captions. Reply STOP to opt out."

                            lead_data = {
                                "lead_id": stable_id, "stable_creator_id": stable_id,
                                "creator_name": name, "country_iso2": itunes_cc.upper(), "primary_platform": "Podcast",
                                "profile_url": result.get("collectionViewUrl", ""),
                                "followers_or_subscribers": 0, "last_content_date": latest_date,
                                "recent_content_url": feed_url, "content_count_30d": count_30d, "longform_count_60d": count_30d * 2,
                                "monetization_signal": mon_signal, "monetization_evidence_url": feed_url,
                                "incubrix_need": need, "need_evidence_url": feed_url,
                                "best_channel": "Email", "channel_handle_or_url": email, "channel_evidence_url": feed_url,
                                "backup_channel": "", "personalization_hook": f"Your podcast {name} caught my attention.",
                                "first_message": first_msg,
                                "checked_date": time.strftime("%Y-%m-%d"), "priority": priority, "lead_score": score,
                                "candidate_status": "Qualified", "rejection_reason": "",
                                "duplicate_check": "UNIQUE", "completeness_check": "COMPLETE"
                            }
                            cols = ', '.join(lead_data.keys())
                            placeholders = ', '.join(['?'] * len(lead_data))
                            cursor.execute(f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({placeholders})", tuple(lead_data.values()))
                            leads_found += 1
                            
                            print(f"     -> SAVED: {name[:40]} ({leads_found}/{limit})")
                            
                    except Exception: pass
            except Exception as e: print(f"  Error on {term} ({itunes_cc}): {e}")
            time.sleep(0.2)
            
            searched_combos.add(combo)
            _save_podcast_state({"searched": list(searched_combos)})
            
        conn.commit()

    conn.close()
    print(f"[SCRAPER] Done. Total podcast leads in DB: {leads_found}")

def _country_distribution(db_path):
    if not os.path.exists(db_path): return {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT country_iso2, COUNT(*) FROM leads WHERE candidate_status='Qualified' GROUP BY country_iso2").fetchall()
        return {r[0]: r[1] for r in rows if r[0]}
    except: return {}
    finally: conn.close()

def _country_allowed(country, dist, total):
    if total < 30: return True
    current = dist.get(country, 0)
    return (current + 1) / (total + 1) <= COUNTRY_CAP_RATIO

def _load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except: return {}
    return {}

def _save_state(query_idx, country_idx, queue, leads_processed, a_count):
    try:
        STATE_FILE.write_text(json.dumps({
            "query_idx": query_idx, "country_idx": country_idx, 
            "queue": list(queue)[:5000],
            "leads_processed": leads_processed, "a_count": a_count,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8")
    except: pass

def _load_podcast_state():
    if PODCAST_STATE_FILE.exists():
        try: return json.loads(PODCAST_STATE_FILE.read_text(encoding="utf-8"))
        except: return {"searched": []}
    return {"searched": []}

def _save_podcast_state(state):
    try:
        PODCAST_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except: pass

def _contains_non_latin_script(text):
    if not text: return False
    for char in text:
        code = ord(char)
        if code < 0x0250 or (0x2000 <= code <= 0x206F) or (0x2190 <= code <= 0x27BF) or (0x1F000 <= code <= 0x1FAFF):
            continue
        return True
    return False

def _is_mostly_english(videos):
    if not videos: return False
    non_latin = sum(1 for v in videos[:5] if _contains_non_latin_script(v.get("title", "")))
    return non_latin < 2

def verify_language(creator_name, videos):
    blob = (creator_name or "").lower() + " " + " ".join(v.get("title", "").lower() for v in (videos or [])[:10])
    for lang in NON_APPROVED_LANGUAGE_MARKERS:
        if re.search(r"\b" + re.escape(lang) + r"\b", blob):
            return False, f"language:{lang}"
    return True, "ok"

def is_publication(creator_name, email):
    name_lower = f" {(creator_name or '').lower().strip()} "
    for pub in PUBLICATION_NAMES:
        if f" {pub} " in name_lower: return True
    if email:
        for dom in PUBLICATION_EMAIL_DOMAINS:
            if email.lower().endswith(dom): return True
    return False

def _find_evidence_video(videos, keyword):
    if not keyword or keyword == "None": return videos[0] if videos else None
    kw_lower = keyword.lower()
    for v in videos:
        if kw_lower in (v.get("description") or "").lower(): return v
    return videos[0] if videos else None

def _count_priority_a(db_path):
    if not os.path.exists(db_path): return 0
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM leads WHERE priority='A' AND candidate_status='Qualified'").fetchone()
        return row[0] if row else 0
    except: return 0
    finally: conn.close()

def _count_existing(db_path):
    if not os.path.exists(db_path): return 0
    conn = sqlite3.connect(db_path)
    try: return conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    except: return 0
    finally: conn.close()

def _count_by_platform(db_path, platform):
    if not os.path.exists(db_path): return 0
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM leads WHERE primary_platform = ?", (platform,)).fetchone()
        return row[0] if row else 0
    except: return 0
    finally: conn.close()

def _template_ai_data(recent_title, creator_name):
    return {
        "hook": f"Your recent video: {recent_title}.",
        "email": f"Hi {creator_name}, came across your recent video \"{recent_title}\". IncuBrix turns long-form content into shorts + captions + written posts in one pass. Worth a quick look? Reply STOP to opt out.",
        "linkedin": f"Hi {creator_name}, saw your video on \"{recent_title}\". IncuBrix helps creators repurpose long-form automatically. Open to a quick chat? Reply STOP to opt out.",
        "instagram": f"Hey {creator_name}, saw \"{recent_title}\". IncuBrix clips + repurposes long videos automatically. Want a look? Reply STOP to opt out."
    }

def rebalance_priorities(db_path):
    if not os.path.exists(db_path): return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE leads SET priority = 'B' WHERE priority = 'A'")
    platforms = cursor.execute("SELECT DISTINCT primary_platform FROM leads WHERE candidate_status='Qualified'").fetchall()
    
    total_a = 0
    for (plat,) in platforms:
        count = cursor.execute("SELECT COUNT(*) FROM leads WHERE primary_platform = ? AND candidate_status='Qualified'", (plat,)).fetchone()[0]
        # Cap at 25 as per assessment PDF requirement
        cap = max(5, min(25, round(count * 0.05)))
        
        query = """
            UPDATE leads
            SET priority = 'A'
            WHERE lead_id IN (
                SELECT lead_id FROM leads
                WHERE candidate_status = 'Qualified' AND primary_platform = ?
                ORDER BY lead_score DESC
                LIMIT ?
            )
        """
        cursor.execute(query, (plat, cap))
        print(f"[REBALANCE] Upgraded top {cap} {plat} leads to Priority A (out of {count} total).")
        total_a += cap
        
    conn.commit()
    conn.close()
    print(f"[REBALANCE] Total Priority A leads set to {total_a} (Max 25 per platform).")

def generate_all_priority_a_outreach(db_path):
    if not os.path.exists(db_path): return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        leads = conn.execute("SELECT * FROM leads WHERE candidate_status='Qualified' AND priority='A'").fetchall()
        if not leads:
            print("\n[OUTREACH] No Priority A leads found to generate outreach for.")
            return
        
        print(f"\n[OUTREACH] Generating multi-channel packs for {len(leads)} Priority A leads (this may take a few minutes)...")
        for lead in leads:
            lead_dict = dict(lead)
            try:
                time.sleep(2) 
                generate_priority_a_pack(lead_dict)
            except Exception as e:
                print(f"  [WARN] Pack failed for {lead_dict.get('creator_name')}: {e}")
        print("[OUTREACH] Done generating packs.")
    finally:
        conn.close()

def run_engine(db_path, limit=6000, custom_queries=None, filter_commercial=True,
               min_subs=5000, max_subs=100000, min_vids_30d=8, min_vids_60d=2,
               english_only=True, generate_outreach=True, sleep_between=0.2,
               resume_mode=False, source_filter="All", segment_filter="All", min_podcast_episodes=0,
               workspace=None):
    
    if workspace is not None:
        global STATE_FILE, PODCAST_STATE_FILE
        ws = Path(workspace)
        ws.mkdir(parents=True, exist_ok=True)
        STATE_FILE = ws / "engine_state.json"
        PODCAST_STATE_FILE = ws / "podcast_state.json"

    init_db(db_path)

    if source_filter == "All":
        yt_target = (limit + 1) // 2
        pod_target = limit - yt_target
    elif source_filter == "YouTube":
        yt_target, pod_target = limit, 0
    else:
        yt_target, pod_target = 0, limit

    yt_count = _count_by_platform(db_path, "YouTube")
    pod_count = _count_by_platform(db_path, "Podcast")
    total_existing = yt_count + pod_count

    print(f"[ENGINE] Targets -> YouTube: {yt_target}, Podcast: {pod_target} (limit={limit})")
    print(f"[ENGINE] Existing -> YouTube: {yt_count}, Podcast: {pod_count}")

    if total_existing >= limit:
        print(f"Already reached target of {limit} leads. Skipping scrape.")
        if generate_outreach:
            rebalance_priorities(db_path)
            generate_all_priority_a_outreach(db_path)
        return

    youtube_exhausted = False
    podcast_exhausted = False

    yt = None
    if source_filter in ["All", "YouTube"]:
        try:
            yt = YouTubeClient()
        except RuntimeError as e:
            if "NO_YOUTUBE_KEYS" in str(e):
                print("[ENGINE] No YouTube API keys found. Skipping YouTube crawl.")
                youtube_exhausted = True
            else:
                raise e

    base_queries = list(custom_queries) if custom_queries else list(SEARCH_QUERIES)
    countries = list(TARGET_COUNTRIES.keys())
    rejected_cids = set()
    
    if resume_mode:
        state = _load_state()
        query_idx = state.get("query_idx", 0)
        country_idx = state.get("country_idx", 0)
        frontier = deque(state.get("queue", []))
        print(f"[RESUME YOUTUBE] From query_idx={query_idx}, queue_size={len(frontier)}")
    else:
        query_idx = 0
        country_idx = 0
        frontier = deque()

    start_ts = time.time()

    while True:
        yt_count = _count_by_platform(db_path, "YouTube")
        pod_count = _count_by_platform(db_path, "Podcast")
        total = yt_count + pod_count

        if podcast_exhausted and not youtube_exhausted:
            new_yt = limit - pod_count
            if new_yt > yt_target:
                print(f"[ENGINE] Podcast exhausted -> YouTube target raised {yt_target} -> {new_yt}.")
                yt_target = new_yt
        if youtube_exhausted and not podcast_exhausted:
            new_pod = limit - yt_count
            if new_pod > pod_target:
                print(f"[ENGINE] YouTube exhausted -> Podcast target raised {pod_target} -> {new_pod}.")
                pod_target = new_pod

        if yt_count >= yt_target and pod_count >= pod_target:
            print(f"\n[ENGINE] All targets reached (YouTube: {yt_count}/{yt_target}, Podcast: {pod_count}/{pod_target}).")
            break
        if youtube_exhausted and podcast_exhausted:
            print("\n[ENGINE] Both YouTube and Podcast sources exhausted. Stopping early.")
            break
        if total >= limit:
            print(f"\n[ENGINE] Global limit of {limit} reached.")
            break

        made_progress = False

        if (not podcast_exhausted and source_filter in ["All", "Podcast"] and pod_count < pod_target):
            print(f"\n[ENGINE LOOP] Podcast scraper. Target: {pod_target} (current: {pod_count})")
            count_before = pod_count

            run_podcast_scraper(
                db_path, custom_queries, segment_filter, pod_target,
                english_only=english_only, filter_commercial=filter_commercial,
                min_podcast_episodes=min_podcast_episodes
            )

            count_after = _count_by_platform(db_path, "Podcast")
            if count_after > count_before:
                made_progress = True
            else:
                print("[ENGINE] Podcast scraper found no new leads. Marking Podcasts as exhausted.")
                podcast_exhausted = True
            pod_count = count_after

        if (not youtube_exhausted and source_filter in ["All", "YouTube"] and yt is not None and yt_count < yt_target):
            yt_count = _count_by_platform(db_path, "YouTube")
            pod_count = _count_by_platform(db_path, "Podcast")
            if podcast_exhausted:
                yt_target = max(yt_target, limit - pod_count)

            print(f"\n[ENGINE LOOP] YouTube scraper. Target: {yt_target} (current: {yt_count})")
            
            try:
                while yt_count < yt_target and not youtube_exhausted:
                    if _count_existing(db_path) >= limit:
                        break
                    if not frontier:
                        if query_idx >= len(base_queries) * len(countries):
                            print("\n[ENGINE] Exhausted all YouTube search combinations.")
                            youtube_exhausted = True
                            break
                        
                        query = base_queries[query_idx % len(base_queries)]
                        country_code = countries[country_idx % len(countries)]
                        print(f"\n[SEED] Searching YouTube '{query}' in {country_code}...")
                        
                        try:
                            seeds = yt.search_seeds(query, country_code)
                        except RuntimeError as e:
                            if "QUOTA_EXHAUSTED" in str(e):
                                print("\n[ENGINE] YOUTUBE API QUOTA EXHAUSTED during search. Stopping YouTube crawl.")
                                youtube_exhausted = True
                                break
                            raise e
                        
                        for s in seeds:
                            if not is_duplicate(db_path, s) and s not in rejected_cids:
                                frontier.append(s)
                        
                        query_idx += 1
                        if query_idx % len(base_queries) == 0:
                            country_idx += 1
                        _save_state(query_idx, country_idx, frontier, yt_count, 0)
                        continue

                    batch = []
                    while frontier and len(batch) < 50:
                        cid = frontier.popleft()
                        if not is_duplicate(db_path, cid) and cid not in rejected_cids:
                            batch.append(cid)

                    if not batch: continue

                    print(f"\n[BATCH] Checking {len(batch)} channels from queue...")
                    
                    try:
                        channels_data = yt.get_batch_channel_details(batch)
                    except RuntimeError as e:
                        if "QUOTA_EXHAUSTED" in str(e):
                            print("\n[ENGINE] YOUTUBE API QUOTA EXHAUSTED during batch details. Stopping YouTube crawl.")
                            youtube_exhausted = True
                            break
                        raise e

                    for c in channels_data:
                        if _count_existing(db_path) >= limit:
                            print(f"\n[ENGINE] Reached global limit of {limit}. Stopping.")
                            youtube_exhausted = True
                            break

                        cid = c["id"]
                        snippet = c.get("snippet", {})
                        stats = c.get("statistics", {})
                        branding = c.get("brandingSettings", {}).get("channel", {})
                        
                        title = snippet.get("title", "Unknown")
                        sub = int(stats.get("subscriberCount", 0))
                        rc = snippet.get("country")
                        desc = snippet.get("description", "")
                        
                        featured = branding.get("featuredChannelsUrls", [])
                        for f in featured:
                            if not is_duplicate(db_path, f) and f not in rejected_cids:
                                frontier.append(f)

                        title_lower = title.lower()
                        if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
                            rejected_cids.add(cid); continue

                        if not rc or rc not in APPROVED_COUNTRIES: 
                            rejected_cids.add(cid); continue
                        
                        dist = _country_distribution(db_path)
                        total_q = sum(dist.values())
                        if not _country_allowed(rc, dist, total_q): 
                            rejected_cids.add(cid); continue
                        if sub < min_subs or sub > max_subs: 
                            rejected_cids.add(cid); continue
                        if not NICHE_RE.search(desc + " " + title): 
                            rejected_cids.add(cid); continue
                        
                        if segment_filter != "All" and _classify_youtube_segment(title, desc) != segment_filter:
                            rejected_cids.add(cid); continue
                        
                        email = find_email_from_description(desc)
                        if is_publication(title, email): 
                            rejected_cids.add(cid); continue

                        print(f"  -> Extracting: {title} ({sub:,} subs)")
                        
                        videos = yt.get_latest_videos_rss(cid)
                        if not videos: 
                            rejected_cids.add(cid); continue
                        if english_only and not _is_mostly_english(videos): 
                            rejected_cids.add(cid); continue
                        
                        lang_ok, _ = verify_language(title, videos)
                        if not lang_ok: 
                            rejected_cids.add(cid); continue
                        
                        vids_to_check = [v["video_id"] for v in videos]
                        vid_stats = yt.get_video_stats_and_durations(vids_to_check)
                        
                        total_views = total_likes = total_comments = 0
                        for v in videos:
                            s = vid_stats.get(v["video_id"], {})
                            v["duration"] = s.get("duration", 0)
                            v["views"] = s.get("views", 0)
                            v["likes"] = s.get("likes", 0)
                            v["comments"] = s.get("comments", 0)
                            total_views += v["views"]
                            total_likes += v["likes"]
                            total_comments += v["comments"]

                        engagement_ratio = (total_likes + total_comments) / total_views if total_views > 0 else 0.0

                        activity = yt.check_channel_activity(sub, videos, min_subs, max_subs, min_vids_30d, min_vids_60d)
                        if activity.get("status") == "Rejected": 
                            rejected_cids.add(cid); continue

                        recent_video = videos[0]
                        all_desc = desc + " " + " ".join(v.get("description", "") for v in videos)
                        socials = extract_socials_from_text(all_desc)
                        if not email: email = find_email_from_description(all_desc)
                        
                        if email: best_channel, handle = "Email", email
                        elif socials["linkedin"]: best_channel, handle = "LinkedIn", socials["linkedin"]
                        elif socials["instagram"]: best_channel, handle = "Instagram", socials["instagram"]
                        else: 
                            rejected_cids.add(cid); continue
                        
                        commercial = check_commercial_and_need(all_desc, activity["longform_count"], activity["short_count"])
                        if filter_commercial and not commercial["has_money"]: 
                            rejected_cids.add(cid); continue
                        if not commercial["has_real_need"]: 
                            rejected_cids.add(cid); continue

                        days_since = 999
                        try:
                            pub = datetime.fromisoformat(recent_video["published_at"].replace("Z", "+00:00"))
                            days_since = (datetime.now(timezone.utc) - pub).days
                        except: pass

                        score = calculate_score(
                            subscribers=sub, has_email=bool(email), has_social=bool(socials["linkedin"] or socials["instagram"]),
                            video_count=activity["count_30d"], has_money=commercial["has_money"],
                            pain_signals=commercial.get("pain_signals", []),
                            longform_count=activity["longform_count"], short_count=activity["short_count"],
                            days_since_post=days_since, has_editor=commercial.get("has_editor", False),
                            engagement_ratio=engagement_ratio
                        )

                        priority = determine_priority(score)
                        backup = None
                        if best_channel != "Email" and email: backup = "Email"
                        elif best_channel != "LinkedIn" and socials["linkedin"]: backup = "LinkedIn"
                        elif best_channel != "Instagram" and socials["instagram"]: backup = "Instagram"

                        mon_vid = _find_evidence_video(videos, commercial["monetization_signal"])
                        mon_url = f"https://youtube.com/watch?v={mon_vid['video_id']}" if mon_vid else ""
                        need_url = f"https://youtube.com/watch?v={recent_video['video_id']}"

                        if priority == "A":
                            print(f"     -> AI outreach (score={score}, priority=A)...")
                            ai_data = generate_personalized_outreach(creator_name=title, recent_video_title=recent_video["title"], channel_name=title)
                        else:
                            ai_data = _template_ai_data(recent_video["title"], title)

                        def _clean(s): return (s or "").replace("[Name]", title).replace("[Creator]", title)

                        lead_data = {
                            "stable_creator_id": cid, "creator_name": title, "country_iso2": rc,
                            "primary_platform": "YouTube", "profile_url": f"https://youtube.com/channel/{cid}",
                            "followers_or_subscribers": sub, "last_content_date": recent_video["published_at"],
                            "recent_content_url": f"https://youtube.com/watch?v={recent_video['video_id']}",
                            "content_count_30d": activity["count_30d"], "longform_count_60d": activity["longform_count"],
                            "monetization_signal": commercial["monetization_signal"], "monetization_evidence_url": mon_url,
                            "incubrix_need": commercial["incubrix_need"], "need_evidence_url": need_url,
                            "best_channel": best_channel, "channel_handle_or_url": handle,
                            "channel_evidence_url": f"https://youtube.com/channel/{cid}/about", "backup_channel": backup,
                            "personalization_hook": _clean(ai_data.get("hook")),
                            "first_message": _clean(ai_data.get("email") if best_channel == "Email" else ai_data.get("linkedin") if best_channel == "LinkedIn" else ai_data.get("instagram")),
                            "checked_date": time.strftime("%Y-%m-%d"), "priority": priority,
                            "lead_score": score, "candidate_status": "Qualified",
                            "duplicate_check": "UNIQUE", "completeness_check": "COMPLETE",
                        }

                        insert_lead(db_path, lead_data)
                        yt_count += 1
                        print(f"     -> SAVED {title} ({yt_count}/{yt_target}) [{rc}] score={score} pri={priority} | engagement={engagement_ratio:.2%}")

                        lead_data["recent_video_title"] = recent_video["title"]
                        if generate_outreach and priority == "A":
                            try: generate_priority_a_pack(lead_data, ai_data=ai_data)
                            except Exception as e: print(f"     -> [WARN] Pack failed: {e}")

                        if sleep_between > 0: time.sleep(sleep_between)
                        _save_state(query_idx, country_idx, frontier, yt_count, 0)

            except RuntimeError as e:
                if "QUOTA_EXHAUSTED" in str(e):
                    print("\n[ENGINE] YOUTUBE API QUOTA EXHAUSTED. Stopping YouTube crawl to save partial data.")
                else:
                    print(f"[ENGINE] YouTube error: {e}")
                youtube_exhausted = True
            except Exception as e:
                print(f"[ENGINE] YouTube error: {e}")
                youtube_exhausted = True
            
            count_after = _count_by_platform(db_path, "YouTube")
            if count_after > yt_count:
                made_progress = True
            yt_count = count_after

        if not made_progress:
            print("\n[ENGINE] No progress made in the last loop iteration. Both sources may be exhausted. Stopping.")
            break

    yt_final  = _count_by_platform(db_path, "YouTube")
    pod_final = _count_by_platform(db_path, "Podcast")
    total     = yt_final + pod_final
    duration  = time.time() - start_ts
    print(f"\nRun complete. YouTube: {yt_final}/{yt_target}, Podcast: {pod_final}/{pod_target}, Total: {total}/{limit}. Duration: {duration/60:.1f} mins.")
    _save_state(query_idx, country_idx, frontier, yt_final, 0)

    if generate_outreach:
        rebalance_priorities(db_path)
        generate_all_priority_a_outreach(db_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true", help="Delete existing DB and start over")
    parser.add_argument("--limit", type=int, default=6000)
    parser.add_argument("--no-outreach", action="store_true")
    parser.add_argument("--source", choices=["All", "YouTube", "Podcast"], default="All")
    parser.add_argument("--segment", choices=["All", "Expert-led", "Podcaster", "YouTube-first"], default="All")
    args = parser.parse_args()

    db_path = str(DATA_DIR / "production.db")
    full_csv = str(DATA_DIR / "production_leads.csv")
    priority_csv = str(DATA_DIR / "production_priority_a.csv")

    if args.fresh and os.path.exists(db_path):
        print("Fresh start. Deleting DB...")
        os.remove(db_path)
        if STATE_FILE.exists(): STATE_FILE.unlink()
        if PODCAST_STATE_FILE.exists(): PODCAST_STATE_FILE.unlink()

    try:
        run_engine(db_path, limit=args.limit, generate_outreach=not args.no_outreach, 
                   resume_mode=not args.fresh, source_filter=args.source, segment_filter=args.segment)
    except KeyboardInterrupt:
        print("\n[STOPPED] Saving state...")
    except Exception as e:
        print(f"\n[NOTICE] Engine stopped: {e}")
    finally:
        print("\nExporting to CSV...")
        export_to_csv(db_path, full_csv, priority_csv)