import time
import logging
import json
import re
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config import YOUTUBE_API_KEYS, LOGS_DIR, EXCLUDE_KEYWORDS

logger = logging.getLogger("incubrix.youtube")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOGS_DIR / "engine.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(sh)

_ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

QUOTA_FILE = LOGS_DIR / "quota_usage.json"
DAILY_QUOTA = 10_000
PROACTIVE_ROTATE_AT = 9_500   # rotate when estimated usage hits 9,500/10,000


def _load_quota():
    """Returns {key_idx_str: estimated_units_used_today}. Resets if date changed."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if QUOTA_FILE.exists():
        try:
            data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            if data.get("date") == today:
                return data.get("usage", {})
        except Exception:
            pass
    return {}


def _save_quota(usage):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        QUOTA_FILE.write_text(
            json.dumps({"date": today, "usage": usage}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


class YouTubeClient:
    def __init__(self):
        self.keys = YOUTUBE_API_KEYS
        if not self.keys:
            raise RuntimeError("NO_YOUTUBE_KEYS")
        self.current_key_idx = 0
        self.youtube = self._build(self.current_key_idx)
        logger.info(f"YouTubeClient initialised with {len(self.keys)} key(s)")

    def _build(self, idx):
        return build("youtube", "v3", developerKey=self.keys[idx], cache_discovery=False)

    def _rotate_key(self, reason=""):
        prev = self.current_key_idx
        self.current_key_idx += 1
        if self.current_key_idx >= len(self.keys):
            raise RuntimeError("QUOTA_EXHAUSTED")
        logger.warning(f"Key rotation {prev} -> {self.current_key_idx} ({reason})")
        self.youtube = self._build(self.current_key_idx)

    def _proactive_rotate_if_needed(self):
        """Rotate BEFORE hitting quota wall."""
        usage = _load_quota()
        used = usage.get(str(self.current_key_idx), 0)
        if used >= PROACTIVE_ROTATE_AT:
            logger.warning(
                f"Key {self.current_key_idx} at ~{used}/{DAILY_QUOTA} units "
                f"(est.) — proactive rotate"
            )
            self._rotate_key(reason=f"proactive, ~{used} used")

    def _track_usage(self, units):
        usage = _load_quota()
        idx = str(self.current_key_idx)
        usage[idx] = usage.get(idx, 0) + units
        _save_quota(usage)

    def _execute(self, request_fn, label, est_units=1):
        """
        Runs a YouTube API call with:
          - Proactive rotation when key estimate > 9,500
          - Rate-limit handling: backoff 3x before rotating
          - Quota-exceeded (403 quotaExceeded): rotate immediately
        """
        for attempt in range(len(self.keys)):
            self._proactive_rotate_if_needed()

            t0 = time.time()
            try:
                result = request_fn()
                self._track_usage(est_units)
                dt = time.time() - t0
                logger.info(f"{label}: OK in {dt:.2f}s (key_idx={self.current_key_idx}, "
                            f"+{est_units}u)")
                return result

            except HttpError as e:
                status = getattr(e.resp, "status", None)
                dt = time.time() - t0
                reason = ""
                try:
                    body = json.loads(e.content.decode("utf-8"))
                    reason = body.get("error", {}).get("errors", [{}])[0].get("reason", "")
                except Exception:
                    pass

                # --- Daily quota exhausted → rotate immediately ---
                if status == 403 and reason == "quotaExceeded":
                    logger.warning(f"{label}: quotaExceeded on key {self.current_key_idx} — rotating")
                    self._track_usage(DAILY_QUOTA)  # mark as fully used
                    self._rotate_key(reason="quotaExceeded")
                    continue

                # --- Rate limit → backoff, then rotate if still failing ---
                if status == 429 or reason == "rateLimitExceeded":
                    logger.warning(f"{label}: rate-limited ({dt:.2f}s), backing off")
                    succeeded = False
                    for retry in range(3):
                        wait = 2 ** retry  # 1, 2, 4 sec
                        time.sleep(wait)
                        try:
                            result = request_fn()
                            self._track_usage(est_units)
                            logger.info(f"{label}: OK after {retry+1} retries "
                                        f"(key_idx={self.current_key_idx})")
                            succeeded = True
                            break
                        except HttpError as e2:
                            s2 = getattr(e2.resp, "status", None)
                            if s2 != 429:
                                break
                    if succeeded:
                        return result
                    logger.warning(f"{label}: persistent rate-limit on key "
                                   f"{self.current_key_idx} — rotating")
                    self._rotate_key(reason="persistent 429")
                    continue

                # --- Other 403 (bad key, restricted) → don't rotate, log and move on ---
                if status == 403:
                    logger.error(f"{label}: forbidden ({reason or 'unknown'}) — "
                                 f"key {self.current_key_idx} unusable")
                    return None

                # --- Unexpected error ---
                logger.exception(f"{label}: unexpected {status} ({dt:.2f}s)")
                return None

            except Exception as e:
                logger.exception(f"{label}: {e}")
                return None

        logger.error(f"{label}: exhausted all keys")
        raise RuntimeError("QUOTA_EXHAUSTED")

    def _parse_iso_duration(self, iso):
        m = _ISO_DUR.fullmatch(iso or "")
        if not m:
            return None
        h, mi, s = (int(x or 0) for x in m.groups())
        return h * 3600 + mi * 60 + s

    # ==============================================================
    # API wrappers — pass correct `est_units` for quota tracking
    # ==============================================================
    def search_channels(self, query, region_code, page_token=None):
        def _run():
            return self.youtube.search().list(
                q=query, type="channel", regionCode=region_code,
                relevanceLanguage="en", maxResults=50, part="snippet",
                pageToken=page_token,
            ).execute()

        response = self._execute(_run, f"search(q={query}, region={region_code})", est_units=100)
        if not response:
            return [], None

        channels = []
        for item in response.get("items", []):
            title = item["snippet"]["title"].lower()
            if any(bad in title for bad in EXCLUDE_KEYWORDS):
                continue
            channels.append({
                "channel_id": item["snippet"]["channelId"],
                "title": item["snippet"]["title"],
            })
        return channels, response.get("nextPageToken")

    def get_multiple_channel_stats(self, channel_ids):
        if not channel_ids:
            return {}
        def _run():
            return self.youtube.channels().list(
                part="statistics", id=",".join(channel_ids)).execute()
        response = self._execute(_run, f"channels.list stats({len(channel_ids)})", est_units=1)
        if not response:
            return {}
        return {it["id"]: int(it["statistics"].get("subscriberCount", 0))
                for it in response.get("items", [])}

    def get_channel_countries(self, channel_ids):
        if not channel_ids:
            return {}
        def _run():
            return self.youtube.channels().list(
                part="snippet", id=",".join(channel_ids)).execute()
        response = self._execute(_run, f"channels.list countries({len(channel_ids)})", est_units=1)
        if not response:
            return {}
        return {it["id"]: it.get("snippet", {}).get("country")
                for it in response.get("items", [])}

    def get_video_durations(self, video_ids):
        """1 quota unit per 50 videos."""
        out = {}
        if not video_ids:
            return out
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i+50]
            def _run():
                return self.youtube.videos().list(
                    part="contentDetails", id=",".join(chunk)).execute()
            resp = self._execute(_run, f"videos.list({len(chunk)})", est_units=1)
            for it in (resp or {}).get("items", []):
                out[it["id"]] = self._parse_iso_duration(
                    it.get("contentDetails", {}).get("duration"))
        return out

    def get_latest_videos_rss(self, channel_id):
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            response = requests.get(rss_url, timeout=10)
            if response.status_code != 200:
                return []
            root = ET.fromstring(response.content)
            videos = []
            now = datetime.now(timezone.utc)
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
                title = entry.find("{http://www.w3.org/2005/Atom}title")
                published = entry.find("{http://www.w3.org/2005/Atom}published")
                if not (video_id is not None and title is not None and published is not None):
                    continue
                description = ""
                media_group = entry.find("{http://search.yahoo.com/mrss/}group")
                if media_group is not None:
                    desc = media_group.find("{http://search.yahoo.com/mrss/}description")
                    if desc is not None and desc.text:
                        description = desc.text
                pub_date = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
                days_old = (now - pub_date).days
                videos.append({
                    "video_id": video_id.text,
                    "title": title.text,
                    "published_at": published.text,
                    "description": description,
                    "duration": 0,
                    "days_old": days_old,
                })
            return videos
        except Exception as e:
            logger.warning(f"RSS {channel_id}: {e}")
            return []

    def check_channel_activity(self, channel_id, sub_count, videos,
                               min_subs=5000, max_subs=100000,
                               min_vids_30d=8, min_vids_60d=2):
        if sub_count < min_subs or sub_count > max_subs:
            return {"status": "Rejected", "reason": f"subs {sub_count} out of range"}
        if not videos:
            return {"status": "Rejected", "reason": "No RSS videos"}

        count_30d = sum(1 for v in videos if v["days_old"] <= 30)
        longform_60d = sum(1 for v in videos
                           if v["days_old"] <= 60 and v["duration"] >= 300)

        if not (count_30d >= min_vids_30d or longform_60d >= min_vids_60d):
            return {"status": "Rejected",
                    "reason": f"Not active ({count_30d} in 30d, {longform_60d} long-form/60d)"}

        short_count = sum(1 for v in videos if 0 < v["duration"] <= 60)
        longform_count = sum(1 for v in videos if v["duration"] >= 300)

        return {
            "status": "Active",
            "subscribers": sub_count,
            "videos": videos,
            "count_30d": count_30d,
            "longform_60d": longform_60d,
            "short_count": short_count,
            "longform_count": longform_count,
        }