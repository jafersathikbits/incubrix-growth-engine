import time
import logging
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

    def _rotate_key(self):
        prev = self.current_key_idx
        self.current_key_idx += 1
        if self.current_key_idx >= len(self.keys):
            raise RuntimeError("QUOTA_EXHAUSTED")
        logger.warning(f"Key rotation {prev} -> {self.current_key_idx}")
        self.youtube = self._build(self.current_key_idx)

    def _execute(self, request_fn, label, est_units=1):
        for attempt in range(len(self.keys)):
            t0 = time.time()
            try:
                result = request_fn()
                logger.info(f"{label}: OK in {time.time()-t0:.2f}s (key_idx={self.current_key_idx}, +{est_units}u)")
                return result
            except HttpError as e:
                status = getattr(e.resp, "status", None)
                if status in (403, 429):
                    logger.warning(f"{label}: quota/rate limit on key {self.current_key_idx} — rotating")
                    self._rotate_key()
                    continue
                logger.error(f"{label}: HttpError {status} - {e}")
                return None
            except Exception as e:
                logger.exception(f"{label}: unexpected {e}")
                return None
        raise RuntimeError("QUOTA_EXHAUSTED")

    def search_seeds(self, query, region_code):
        def _run():
            return self.youtube.search().list(
                q=query, type="channel", regionCode=region_code,
                relevanceLanguage="en", maxResults=50, part="snippet"
            ).execute()
        response = self._execute(_run, f"search_seed({query})", est_units=100)
        if not response:
            return []
        return [item["snippet"]["channelId"] for item in response.get("items", [])]

    def get_batch_channel_details(self, channel_ids):
        results = []
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i:i+50]
            def _run():
                return self.youtube.channels().list(
                    part="snippet,statistics,brandingSettings", 
                    id=",".join(chunk), maxResults=50
                ).execute()
            response = self._execute(_run, f"channels.list_batch({len(chunk)})", est_units=1)
            if response:
                results.extend(response.get("items", []))
        return results

    def get_video_stats_and_durations(self, video_ids):
        """1 quota unit per 50 videos. Fetches duration AND engagement stats."""
        out = {}
        if not video_ids:
            return out
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i+50]
            def _run():
                return self.youtube.videos().list(part="contentDetails,statistics", id=",".join(chunk)).execute()
            resp = self._execute(_run, f"videos.list({len(chunk)})", est_units=1)
            for it in (resp or {}).get("items", []):
                iso = it.get("contentDetails", {}).get("duration")
                stats = it.get("statistics", {})
                m = _ISO_DUR.fullmatch(iso or "")
                if m:
                    h, mi, s = (int(x or 0) for x in m.groups())
                    out[it["id"]] = {
                        "duration": h * 3600 + mi * 60 + s,
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0))
                    }
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
                desc = ""
                media_group = entry.find("{http://search.yahoo.com/mrss/}group")
                if media_group is not None:
                    d = media_group.find("{http://search.yahoo.com/mrss/}description")
                    if d is not None and d.text:
                        desc = d.text
                pub_date = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
                days_old = (now - pub_date).days
                videos.append({
                    "video_id": video_id.text,
                    "title": title.text,
                    "published_at": published.text,
                    "description": desc,
                    "duration": 0,
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "days_old": days_old,
                })
            return videos
        except Exception as e:
            logger.warning(f"RSS {channel_id}: {e}")
            return []

    def check_channel_activity(self, sub_count, videos, min_subs=5000, max_subs=100000, min_vids_30d=8, min_vids_60d=2):
        if sub_count < min_subs or sub_count > max_subs:
            return {"status": "Rejected", "reason": f"subs {sub_count} out of range"}
        if not videos:
            return {"status": "Rejected", "reason": "No RSS videos"}
        count_30d = sum(1 for v in videos if v["days_old"] <= 30)
        longform_60d = sum(1 for v in videos if v["days_old"] <= 60 and v["duration"] >= 300)
        if not (count_30d >= min_vids_30d or longform_60d >= min_vids_60d):
            return {"status": "Rejected", "reason": f"Not active ({count_30d} in 30d, {longform_60d} in 60d)"}
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