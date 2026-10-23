import time
import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone

from src.database import init_db, is_duplicate, insert_lead
from src.youtube_api import YouTubeClient
from src.enrichment import (
    find_email_from_description,
    extract_socials_from_text,
    check_commercial_and_need,
)
from src.ai_agent import generate_personalized_outreach
from src.outreach_gen import generate_priority_a_pack
from src.scoring import calculate_score, determine_priority
from src.config import SEARCH_QUERIES, TARGET_COUNTRIES, DATA_DIR, LOGS_DIR
from src.exporter import export_to_csv


APPROVED_COUNTRIES = {"US", "CA", "GB", "IE", "AU", "NZ", "SG"}
PRIORITY_A_CAP = 250
COUNTRY_CAP_RATIO = 0.55
COUNTRY_MIN_BOOTSTRAP = 30
MIN_COUNTRIES = 3

NON_APPROVED_LANGUAGE_MARKERS = (
    "kannada", "hindi", "tamil", "telugu", "malayalam", "marathi", "gujarati",
    "punjabi", "bhojpuri", "odia", "assamese", "nepali", "urdu", "bangla",
    "bengali", "sinhala", "pashto", "mandarin", "cantonese", "tagalog",
    "bahasa", "swahili", "yoruba", "hausa", "amharic", "zulu",
    "español", "deutsch", "français", "italiano", "português", "nederlands",
    "polski",
)

PUBLICATION_NAMES = (
    "wall street journal", "wsj", "bloomberg", "reuters", "financial times",
    "the economist", "forbes", "business insider", "cnbc", "cnn",
    "bbc news", "the new york times", "new york times", "washington post",
    "the washington post", "the guardian", "the telegraph", "financial review",
    "australian financial review", "afr", "pushkin industries", "pushkin",
    "the times", "the sunday times",
)

PUBLICATION_EMAIL_DOMAINS = (
    "@wsj.com", "@bloomberg.net", "@reuters.com", "@ft.com",
    "@economist.com", "@forbes.com", "@businessinsider.com",
    "@cnbc.com", "@cnn.com", "@nytimes.com", "@washingtonpost.com",
    "@theguardian.com", "@telegraph.co.uk", "@afr.com",
    "@smh.com.au", "@pushkin.fm", "@npr.org", "@bbc.co.uk",
)

STATE_FILE = DATA_DIR / "engine_state.json"
RUNTIME_LOG = LOGS_DIR / "runtime.jsonl"


# ==================================================================
# Country balance
# ==================================================================
def _country_distribution(db_path):
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT country_iso2, COUNT(*) FROM leads "
            "WHERE candidate_status='Qualified' "
            "GROUP BY country_iso2"
        ).fetchall()
        return {r[0]: r[1] for r in rows if r[0]}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _country_allowed(country, dist, total):
    """Brief rule: ≤60% per country, ≥3 countries. Cap kicks in after 30-lead bootstrap."""
    if total < COUNTRY_MIN_BOOTSTRAP:
        return True
    new_total = total + 1
    current = dist.get(country, 0)
    return (current + 1) / new_total <= COUNTRY_CAP_RATIO


def _country_balance_report(db_path):
    dist = _country_distribution(db_path)
    total = sum(dist.values())
    if total == 0:
        return
    print("\n" + "=" * 60)
    print(f"  COUNTRY BALANCE ({total} leads)")
    print("=" * 60)
    for country, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = 100 * count / total
        flag = "  OVER 60% CAP" if pct > 60 else ""
        print(f"  {country}: {count:5d}  ({pct:5.1f}%){flag}")
    print("=" * 60)
    if len(dist) < MIN_COUNTRIES:
        print(f"  WARNING: Only {len(dist)} countries — brief requires ≥{MIN_COUNTRIES}")
    over = [c for c, n in dist.items() if 100 * n / total > 60]
    if over:
        print(f"  WARNING: Exceeds 60% cap: {over}")


# ==================================================================
# Runtime logging
# ==================================================================
def _log_runtime(limit, leads_processed, a_count, duration_sec, mode):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "limit": limit,
        "leads_processed": leads_processed,
        "priority_a": a_count,
        "duration_sec": round(duration_sec, 1),
        "duration_min": round(duration_sec / 60, 1),
        # Cost estimate (Groq free-tier pricing is ~$0.05-0.10 per 1k small calls)
        "approx_ai_calls": a_count,
        "approx_ai_cost_usd": round(a_count * 0.0004, 2),
        # YouTube quota used is tracked in logs/engine.log (count search() calls × 100)
    }
    try:
        with open(RUNTIME_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


# ==================================================================
# State save/restore
# ==================================================================
def _load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(query_idx, country_idx, page_token, leads_processed, a_count):
    try:
        STATE_FILE.write_text(json.dumps({
            "query_idx": query_idx,
            "country_idx": country_idx,
            "page_token": page_token,
            "leads_processed": leads_processed,
            "a_count": a_count,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8")
    except Exception:
        pass


# ==================================================================
# Qualification helpers
# ==================================================================
def _contains_non_latin_script(text):
    if not text:
        return False
    for char in text:
        code = ord(char)
        if code < 0x0250:
            continue
        if 0x2000 <= code <= 0x206F:
            continue
        if 0x2190 <= code <= 0x27BF:
            continue
        if 0x1F000 <= code <= 0x1FAFF:
            continue
        return True
    return False


def _is_mostly_english(videos):
    if not videos:
        return False
    non_latin = sum(1 for v in videos[:5]
                    if _contains_non_latin_script(v.get("title", "")))
    return non_latin < 2


def verify_language(creator_name, videos):
    parts = [creator_name or ""]
    for v in (videos or [])[:10]:
        parts.append(v.get("title", "") or "")
    blob = " ".join(parts).lower()
    for lang in NON_APPROVED_LANGUAGE_MARKERS:
        if re.search(r"\b" + re.escape(lang) + r"\b", blob):
            return False, f"language:{lang}"
    return True, "ok"


def is_publication(creator_name, email):
    name_lower = f" {(creator_name or '').lower().strip()} "
    for pub in PUBLICATION_NAMES:
        if f" {pub} " in name_lower:
            return True
    if email:
        email_lower = email.lower()
        for dom in PUBLICATION_EMAIL_DOMAINS:
            if email_lower.endswith(dom):
                return True
    return False


def _find_evidence_video(videos, keyword):
    if not keyword or keyword == "None":
        return videos[0] if videos else None
    kw_lower = keyword.lower()
    for v in videos:
        if kw_lower in (v.get("description") or "").lower():
            return v
    return videos[0] if videos else None


def _count_priority_a(db_path):
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE priority='A' AND candidate_status='Qualified'"
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()


def _count_existing(db_path):
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()


def _template_ai_data(recent_title, creator_name):
    return {
        "hook": f"Your recent video: {recent_title}.",
        "email": (
            f"Hi {creator_name}, came across your recent video \"{recent_title}\". "
            f"IncuBrix turns long-form content into shorts + captions + written posts in one pass. "
            f"Worth a quick look? Reply STOP to opt out."
        ),
        "linkedin": (
            f"Hi {creator_name}, saw your video on \"{recent_title}\". "
            f"IncuBrix helps creators repurpose long-form automatically. Open to a quick chat? "
            f"Reply STOP to opt out."
        ),
        "instagram": (
            f"Hey {creator_name}, saw \"{recent_title}\". "
            f"IncuBrix clips + repurposes long videos automatically. Want a look? "
            f"Reply STOP to opt out."
        ),
    }


# ==================================================================
# Engine
# ==================================================================
def run_engine(db_path, limit=6000, custom_queries=None, filter_commercial=True,
               min_subs=5000, max_subs=100000, min_vids_30d=8, min_vids_60d=2,
               english_only=True, generate_outreach=True, sleep_between=0.2,
               resume_mode=False):
    init_db(db_path)
    yt = YouTubeClient()

    leads_processed = _count_existing(db_path)
    a_count = _count_priority_a(db_path)
    base_queries = list(custom_queries) if custom_queries else list(SEARCH_QUERIES)
    countries = list(TARGET_COUNTRIES.keys())

    if resume_mode:
        state = _load_state()
        query_idx = state.get("query_idx", 0)
        country_idx = state.get("country_idx", 0)
        page_token_start = state.get("page_token")
        if query_idx or country_idx or page_token_start:
            print(f"[RESUME] From query_idx={query_idx}, country_idx={country_idx}, "
                  f"page_token={'set' if page_token_start else 'none'}")
        else:
            print("[RESUME] No saved state — starting from beginning")
    else:
        query_idx = 0
        country_idx = 0
        page_token_start = None

    print(f"Starting engine. Existing leads: {leads_processed} | "
          f"Priority A so far: {a_count}/{PRIORITY_A_CAP} | Target: {limit}")

    start_ts = time.time()
    first_iteration = True

    try:
        while leads_processed < limit:
            if query_idx >= len(base_queries):
                base_queries.append(f"{base_queries[query_idx % len(base_queries)]} tips")

            query = base_queries[query_idx]
            country_code = countries[country_idx % len(countries)]
            print(f"\n[SEARCH] '{query}' in {country_code}...")

            page_token = page_token_start if first_iteration else None
            first_iteration = False

            while True:
                if leads_processed >= limit:
                    print(f"Reached limit of {limit} leads.")
                    return

                _save_state(query_idx, country_idx, page_token, leads_processed, a_count)

                channels, next_page_token = yt.search_channels(query, country_code, page_token)
                if not channels:
                    break

                channel_ids = [ch["channel_id"] for ch in channels]
                stats_batch = yt.get_multiple_channel_stats(channel_ids)
                countries_batch = yt.get_channel_countries(channel_ids)

                candidates = []
                for channel in channels:
                    cid = channel["channel_id"]
                    sub = stats_batch.get(cid, 0)
                    rc = countries_batch.get(cid)
                    if is_duplicate(db_path, cid):
                        continue
                    if sub < min_subs or sub > max_subs:
                        continue
                    if not rc or rc not in APPROVED_COUNTRIES:
                        continue
                    candidates.append({**channel, "sub_count": sub, "country": rc})

                for c in candidates:
                    c["videos"] = yt.get_latest_videos_rss(c["channel_id"])
                candidates = [c for c in candidates if c["videos"]]

                all_vids = []
                for c in candidates:
                    all_vids.extend(v["video_id"] for v in c["videos"])
                durations = yt.get_video_durations(all_vids) if all_vids else {}
                for c in candidates:
                    for v in c["videos"]:
                        v["duration"] = durations.get(v["video_id"]) or 0

                for c in candidates:
                    if leads_processed >= limit:
                        return

                    cid = c["channel_id"]
                    title = c["title"]
                    videos = c["videos"]
                    print(f"  -> Checking: {title} ({c['sub_count']:,} subs)")

                    if english_only and not _is_mostly_english(videos):
                        print(f"     -> Rejected: non-English (script)")
                        continue

                    lang_ok, lang_reason = verify_language(title, videos)
                    if not lang_ok:
                        print(f"     -> Rejected: {lang_reason}")
                        continue

                    all_desc = " ".join((v.get("description") or "") for v in videos)
                    email = find_email_from_description(all_desc)
                    socials = extract_socials_from_text(all_desc)

                    if is_publication(title, email):
                        print(f"     -> Rejected: publication/brand")
                        continue

                    if email:
                        best_channel, handle = "Email", email
                    elif socials["linkedin"]:
                        best_channel, handle = "LinkedIn", socials["linkedin"]
                    elif socials["instagram"]:
                        best_channel, handle = "Instagram", socials["instagram"]
                    else:
                        print(f"     -> Rejected: no contact info")
                        continue

                    # ---- COUNTRY CAP (brief: ≤60% per country, ≥3 countries) ----
                    dist = _country_distribution(db_path)
                    total_q = sum(dist.values())
                    if not _country_allowed(c["country"], dist, total_q):
                        print(f"     -> Rejected: country cap ({c['country']} at "
                              f"{dist.get(c['country'], 0)}/{total_q})")
                        continue

                    activity = yt.check_channel_activity(
                        cid, c["sub_count"], videos,
                        min_subs=min_subs, max_subs=max_subs,
                        min_vids_30d=min_vids_30d, min_vids_60d=min_vids_60d,
                    )
                    if activity.get("status") == "Rejected":
                        print(f"     -> Rejected: {activity.get('reason')}")
                        continue

                    recent_video = videos[0]
                    commercial = check_commercial_and_need(
                        all_desc, activity["longform_count"], activity["short_count"],
                    )
                    if filter_commercial and not commercial["has_money"]:
                        print(f"     -> Rejected: no commercial signal")
                        continue
                    if not commercial["has_real_need"]:
                        print(f"     -> Rejected: no real need ({commercial['incubrix_need']})")
                        continue

                    days_since = 999
                    try:
                        pub = datetime.fromisoformat(recent_video["published_at"].replace("Z", "+00:00"))
                        days_since = (datetime.now(timezone.utc) - pub).days
                    except Exception:
                        pass

                    score = calculate_score(
                        subscribers=activity["subscribers"],
                        has_email=bool(email),
                        has_social=bool(socials["linkedin"] or socials["instagram"]),
                        video_count=activity["count_30d"],
                        has_money=commercial["has_money"],
                        pain_signals=commercial.get("pain_signals", []),
                        longform_count=activity["longform_count"],
                        short_count=activity["short_count"],
                        days_since_post=days_since,
                        has_editor=commercial.get("has_editor", False),
                    )

                    priority = determine_priority(score)
                    if priority == "A":
                        if a_count >= PRIORITY_A_CAP:
                            priority = "B"
                        else:
                            a_count += 1

                    backup = None
                    if best_channel != "Email" and email:
                        backup = "Email"
                    elif best_channel != "LinkedIn" and socials["linkedin"]:
                        backup = "LinkedIn"
                    elif best_channel != "Instagram" and socials["instagram"]:
                        backup = "Instagram"

                    mon_vid = _find_evidence_video(videos, commercial["monetization_signal"])
                    mon_url = f"https://youtube.com/watch?v={mon_vid['video_id']}" if mon_vid else ""
                    need_url = f"https://youtube.com/watch?v={recent_video['video_id']}"

                    if priority == "A":
                        print(f"     -> AI outreach (score={score}, priority=A)...")
                        ai_data = generate_personalized_outreach(
                            creator_name=title,
                            recent_video_title=recent_video["title"],
                            channel_name=title,
                        )
                    else:
                        ai_data = _template_ai_data(recent_video["title"], title)

                    def _clean(s):
                        return (s or "").replace("[Name]", title).replace("[Creator]", title)

                    lead_data = {
                        "stable_creator_id": cid,
                        "creator_name": title,
                        "country_iso2": c["country"],
                        "primary_platform": "YouTube",
                        "profile_url": f"https://youtube.com/channel/{cid}",
                        "followers_or_subscribers": activity["subscribers"],
                        "last_content_date": recent_video["published_at"],
                        "recent_content_url": f"https://youtube.com/watch?v={recent_video['video_id']}",
                        "content_count_30d": activity["count_30d"],
                        "longform_count_60d": activity["longform_count"],
                        "monetization_signal": commercial["monetization_signal"],
                        "monetization_evidence_url": mon_url,
                        "incubrix_need": commercial["incubrix_need"],
                        "need_evidence_url": need_url,
                        "best_channel": best_channel,
                        "channel_handle_or_url": handle,
                        "channel_evidence_url": f"https://youtube.com/channel/{cid}/about",
                        "backup_channel": backup,
                        "personalization_hook": _clean(ai_data.get("hook")),
                        "first_message": _clean(
                            ai_data.get("email") if best_channel == "Email"
                            else ai_data.get("linkedin") if best_channel == "LinkedIn"
                            else ai_data.get("instagram")
                        ),
                        "checked_date": time.strftime("%Y-%m-%d"),
                        "priority": priority,
                        "lead_score": score,
                        "candidate_status": "Qualified",
                        "duplicate_check": "UNIQUE",
                        "completeness_check": "COMPLETE",
                    }

                    insert_lead(db_path, lead_data)
                    leads_processed += 1
                    print(f"     -> SAVED {title} ({leads_processed}/{limit}) "
                          f"[{c['country']}] score={score} pri={priority}")

                    lead_data["recent_video_title"] = recent_video["title"]
                    if generate_outreach and priority == "A":
                        try:
                            generate_priority_a_pack(lead_data, ai_data=ai_data)
                        except Exception as e:
                            print(f"     -> [WARN] Pack failed: {e}")

                    if sleep_between > 0:
                        time.sleep(sleep_between)

                _save_state(query_idx, country_idx, next_page_token, leads_processed, a_count)

                if not next_page_token:
                    break
                page_token = next_page_token

            query_idx += 1
            if query_idx % len(base_queries) == 0:
                country_idx += 1
            _save_state(query_idx, country_idx, None, leads_processed, a_count)

    finally:
        duration = time.time() - start_ts
        _log_runtime(limit, leads_processed, a_count, duration,
                     mode="resume" if resume_mode else "fresh")
        _country_balance_report(db_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncuBrix Production Engine")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--no-outreach", action="store_true")
    args = parser.parse_args()

    db_path = str(DATA_DIR / "production.db")
    full_csv = str(DATA_DIR / "production_leads.csv")
    priority_csv = str(DATA_DIR / "production_priority_a.csv")

    if not args.resume:
        if os.path.exists(db_path):
            print("Fresh start. Deleting old production database...")
            os.remove(db_path)
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    try:
        run_engine(db_path, limit=args.limit,
                   generate_outreach=not args.no_outreach,
                   resume_mode=args.resume)
    except KeyboardInterrupt:
        print("\n[STOPPED] Ctrl+C. Saving progress...")
    except RuntimeError as e:
        if "QUOTA_EXHAUSTED" in str(e):
            print("\n" + "=" * 60)
            print("  ALL 12 API QUOTAS EXHAUSTED FOR TODAY")
            print("=" * 60)
            print("  This is normal — 10,000 units/day per project × 12 projects.")
            print("  Your progress is saved. Come back tomorrow and run:")
            print("      python main.py --resume")
            print("=" * 60)
        else:
            print(f"\n[NOTICE] Engine stopped early: {e}")
    except Exception as e:
        print(f"\n[NOTICE] Engine stopped early: {e}")
    finally:
        print("\nExporting to CSV...")
        export_to_csv(db_path, full_csv, priority_csv)
        print("Export complete. Resume with: python main.py --resume")