import time
import logging
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config import YOUTUBE_API_KEYS, LOGS_DIR, EXCLUDE_KEYWORDS

logging.basicConfig(filename=LOGS_DIR / 'engine.log', level=logging.INFO)

class YouTubeClient:
    def __init__(self):
        self.keys = YOUTUBE_API_KEYS
        self.current_key_idx = 0
        self.youtube = build('youtube', 'v3', developerKey=self.keys[self.current_key_idx])

    def _rotate_key(self):
        self.current_key_idx += 1
        if self.current_key_idx >= len(self.keys):
            logging.error("All API keys exhausted.")
            raise Exception("QUOTA_EXHAUSTED")
        logging.warning(f"Rotating to API Key Index: {self.current_key_idx}")
        self.youtube = build('youtube', 'v3', developerKey=self.keys[self.current_key_idx])

    def search_channels(self, query, region_code):
        try:
            request = self.youtube.search().list(
                q=query, type='channel', regionCode=region_code, 
                relevanceLanguage='en', maxResults=50, part='snippet' # UPGRADED TO 50
            )
            response = request.execute()
            
            channels = []
            for item in response.get('items', []):
                title = item['snippet']['title'].lower()
                if any(bad_word in title for bad_word in EXCLUDE_KEYWORDS):
                    continue
                channels.append({
                    'channel_id': item['snippet']['channelId'],
                    'title': item['snippet']['title'],
                    'country': region_code
                })
            return channels
        except HttpError as e:
            if e.resp.status in [403, 429]:
                self._rotate_key()
                return self.search_channels(query, region_code)
            return []

    def get_multiple_channel_stats(self, channel_ids):
        """Fetches stats for up to 50 channels in ONE API call."""
        if not channel_ids:
            return {}
            
        try:
            ids_str = ",".join(channel_ids)
            request = self.youtube.channels().list(part="statistics", id=ids_str)
            response = request.execute()
            
            stats = {}
            for item in response.get('items', []):
                stats[item['id']] = int(item['statistics'].get('subscriberCount', 0))
            return stats
        except HttpError as e:
            if e.resp.status in [403, 429]:
                self._rotate_key()
                return self.get_multiple_channel_stats(channel_ids)
            return {}

    def get_latest_videos_rss(self, channel_id):
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            response = requests.get(rss_url, timeout=10)
            if response.status_code != 200:
                return []
            
            root = ET.fromstring(response.content)
            videos = []
            now = datetime.now(timezone.utc)
            
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                video_id = entry.find('{http://www.youtube.com/xml/schemas/2015}videoId')
                title = entry.find('{http://www.w3.org/2005/Atom}title')
                published = entry.find('{http://www.w3.org/2005/Atom}published')
                
                description = ""
                media_group = entry.find('{http://search.yahoo.com/mrss/}group')
                if media_group is not None:
                    desc = media_group.find('{http://search.yahoo.com/mrss/}description')
                    if desc is not None and desc.text:
                        description = desc.text
                
                duration = 0
                if media_group is not None:
                    content = media_group.find('{http://search.yahoo.com/mrss/}content')
                    if content is not None and 'duration' in content.attrib:
                        duration = int(content.attrib['duration'])
                
                if video_id is not None and title is not None and published is not None:
                    pub_date = datetime.fromisoformat(published.text.replace('Z', '+00:00'))
                    days_old = (now - pub_date).days
                    
                    title_text = title.text.lower()
                    is_longform = (duration > 300)
                    longform_keywords = [
                        "podcast", "episode", "ep.", "ep ", "#", "interview", 
                        "tutorial", "guide", "course", "training", "masterclass", 
                        "webinar", "tips", "strategy", "review", "breakdown"
                    ]
                    
                    if not is_longform and any(kw in title_text for kw in longform_keywords):
                        is_longform = True
                        
                    videos.append({
                        'video_id': video_id.text,
                        'title': title.text,
                        'published_at': published.text,
                        'description': description,
                        'duration': duration if duration > 0 else (3600 if is_longform else 30), 
                        'days_old': days_old
                    })
            return videos
        except Exception as e:
            logging.error(f"RSS Error for {channel_id}: {e}")
            return []

    def check_channel_activity(self, channel_id, sub_count, min_subs=5000, max_subs=100000, min_vids_30d=8, min_vids_60d=2, english_only=True):
        # Sub_count is now passed in from the batched API call!
        if sub_count < min_subs:
            return {"status": "Rejected", "reason": f"Subscribers < {min_subs}"}
        if sub_count > max_subs:
            return {"status": "Rejected", "reason": f"Subscribers > {max_subs}"}

        videos = self.get_latest_videos_rss(channel_id)
        if not videos:
            return {"status": "Rejected", "reason": "No RSS videos found"}

        count_30d = sum(1 for v in videos if v['days_old'] <= 30)
        count_60d = sum(1 for v in videos if v['days_old'] <= 60)
        
        if not (count_30d >= min_vids_30d or count_60d >= min_vids_60d):
            return {"status": "Rejected", "reason": f"Not active enough ({count_30d} in 30d, {count_60d} in 60d)"}

        if english_only:
            recent_title = videos[0]['title']
            if not any(c.isalpha() and ord(c) < 128 for c in recent_title):
                return {"status": "Rejected", "reason": "Non-English content detected"}
            
        short_count = sum(1 for v in videos if 0 < v['duration'] <= 60)
        longform_count = sum(1 for v in videos if v['duration'] > 300)

        return {
            "status": "Active",
            "subscribers": sub_count,
            "videos": videos,
            "count_30d": count_30d,
            "count_60d": count_60d,
            "short_count": short_count,
            "longform_count": longform_count
        }