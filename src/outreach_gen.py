import argparse
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from src.config import BASE_DIR, DATA_DIR, LOGS_DIR
from src.ai_agent import generate_personalized_outreach

load_dotenv()

logger = logging.getLogger("incubrix.outreach")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOGS_DIR / "engine.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(sh)

OUT_DIR = BASE_DIR / "outreach" / "priority_a"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SENDER_NAME = os.getenv("SENDER_NAME", "Jafer Sathik B")
SENDER_TITLE = os.getenv("SENDER_TITLE", "Growth Engineer candidate, IncuBrix")
SENDER_EMAIL = os.getenv("SMTP_EMAIL", "Jafer@example.com")
BOOKING_LINK = os.getenv("BOOKING_LINK", "https://cal.com/Jafer/15min")
TRACKING_BASE = os.getenv("TRACKING_BASE_URL", "https://incubrix.example.com/r")
POSTAL_ADDRESS = os.getenv("CAN_SPAM_ADDRESS", "[POSTAL ADDRESS — set CAN_SPAM_ADDRESS in .env]")

EMAIL_SIGN_OFF = (
    f"\n\n— {SENDER_NAME} | {SENDER_TITLE}\n"
    f"{SENDER_EMAIL} | {BOOKING_LINK}\n"
    f"Reply STOP to opt out.\n"
    f"{POSTAL_ADDRESS}"
)
SHORT_SIGN_OFF = f"\n\n— {SENDER_NAME}, IncuBrix. Reply STOP to opt out."


_COMMON_FIRST_NAMES = {
    "aaron","adam","alex","alexander","ali","amanda","amy","andrew","andy","anna",
    "anthony","ashley","ben","benjamin","bob","brad","brandon","brian","bryan",
    "cameron","carl","carlos","carol","charles","chris","christian","christina",
    "christine","christopher","cindy","claire","colin","craig","dan","daniel",
    "danielle","dave","david","dean","debbie","dennis","derek","diana","donald",
    "doug","drew","ed","eddie","elizabeth","emily","emma","eric","erik","ethan",
    "evan","frank","fred","gabriel","gary","george","gerald","glenn","grace",
    "greg","gregory","hank","hannah","harry","heather","helen","henry","holly",
    "howard","ian","isaac","ivan","jack","jackie","jacob","james","jamie","jan",
    "jane","janet","janice","jason","jay","jeff","jeffrey","jennifer","jenny",
    "jeremy","jerry","jesse","jessica","jim","jimmy","joan","joe","joel","john",
    "johnny","jon","jonathan","jordan","jose","joseph","josh","joshua","juan",
    "judy","julia","julie","justin","karen","kate","katherine","kathy","keith",
    "kelly","ken","kenneth","kevin","kim","kimberly","kyle","larry","laura",
    "lauren","lee","leo","leonard","linda","lisa","logan","lori","louis","lucas",
    "lucy","luis","luke","lynn","mandy","manuel","marc","marcus","margaret",
    "maria","marie","marilyn","mario","mark","martha","martin","mary","mason",
    "matt","matthew","maureen","megan","melissa","micah","michael","michele",
    "michelle","mike","miles","mitch","monica","nancy","nathan","nick","nicole",
    "noah","norman","olivia","oscar","pam","patricia","patrick","paul","paula",
    "pedro","peggy","peter","phil","philip","phillip","rachel","ralph","randy",
    "raymond","rebecca","rich","richard","rick","rita","rob","robert","robin",
    "rod","roger","ron","ronald","rose","roy","russ","russell","ruth","ryan",
    "sam","samantha","samuel","sandra","sara","sarah","scott","sean","seth",
    "shane","shannon","sharon","shawn","sheila","sherry","shirley","simon",
    "sophia","stan","stephanie","stephen","steve","steven","stuart","sue",
    "susan","tammy","tanya","ted","teresa","terry","theresa","thomas","tim",
    "timothy","tina","todd","tom","tommy","tony","tracy","travis","trevor",
    "tyler","valerie","vanessa","veronica","victor","victoria","vince","vincent",
    "virginia","wade","walter","warren","wayne","wendy","wes","wesley","william",
    "willie","zach","zachary",
}
_TITLE_PREFIXES = {"mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", "prof", "prof."}


def _first_name(name):
    if not name:
        return "there"
    import re
    cleaned = re.sub(r"\s*[\|—–-]\s*.*$", "", name).strip()
    parts = [p.strip(".,'\"") for p in cleaned.split() if p.strip(".,'\"")]
    if not parts:
        return "there"
    if parts[0].lower() in _TITLE_PREFIXES and len(parts) > 1:
        parts = parts[1:]
    candidate = parts[0].lower()
    if candidate in _COMMON_FIRST_NAMES:
        return parts[0].capitalize()
    return "there"


def pick_segment(lead):
    need = (lead.get("incubrix_need") or "").lower()
    name = (lead.get("creator_name") or "").lower()
    title = (lead.get("recent_video_title") or "").lower()
    mon = (lead.get("monetization_signal") or "").lower()
    blob = " ".join([need, name, title, mon])

    expert_signals = ("coach", "consult", "expert", "educator", "course",
                      "mastermind", "mentor", "teacher", "training", "webinar")
    podcast_signals = ("podcast", "episode", "ep.", "interview")

    if any(w in blob for w in expert_signals):
        return "expert_led"
    if any(w in blob for w in podcast_signals):
        return "podcaster"
    return "youtube_first"


def _tracking_link(lead_id, channel, step):
    return f"{TRACKING_BASE.rstrip('/')}/{channel}/{lead_id}?step={step}"


def _safe_format(template, ctx):
    try:
        return template.format(**ctx)
    except KeyError as e:
        logger.warning(f"Template key missing: {e}")
        out = template
        for k, v in ctx.items():
            out = out.replace("{" + k + "}", str(v))
        return out


SEGMENT_TEMPLATES = {
    "podcaster": {
        "email_subject": "Your last episode deserves 12 more posts",
        "email_1": (
            'Hi {first_name},\n\n'
            'Came across "{recent_title}" in your recent uploads.\n\n'
            'A pattern with podcasters: a strong 45-60 min episode ships once, and the Shorts, '
            'LinkedIn post, and blog version never get made.\n\n'
            'IncuBrix takes one long episode and returns Shorts, captions, a blog draft, and '
            'cross-post copy — in one pass. Would a 2-min walkthrough be useful?'
        ),
        "email_fu1": (
            'Hi {first_name}, quick follow-up.\n\n'
            'When you finish an episode, who decides what gets clipped? If it\'s you at 11pm '
            'on Sunday, that\'s the bottleneck IncuBrix removes.\n\n'
            'Happy to show a 2-min before/after using one of your own episodes.'
        ),
        "email_fu2": (
            'Hi {first_name}, last note from me.\n\n'
            'If this isn\'t a fit right now, no problem. "{recent_title}" could become 8-12 '
            'Shorts + 1 LinkedIn post + 1 blog draft. If you ever want to see how, my inbox is open.'
        ),
        "linkedin_1": (
            'Hi {first_name}, came across "{recent_title}".\n\n'
            'A pattern with podcasters: one episode ships, 8-10 Shorts stay on the table. '
            'IncuBrix pulls them out and adds captions in one pass. Open to a 2-min walkthrough?'
        ),
        "linkedin_fu1": (
            'Hi {first_name}, following up. Curious — who handles the clipping today, you or '
            'nobody? Happy to show what one episode can become.'
        ),
        "linkedin_fu2": (
            'Hi {first_name}, last note. If repurposing is on the roadmap, I\'d love to show '
            'IncuBrix on your content. No worries if not.'
        ),
        "instagram_1": (
            'Hey {first_name}, saw "{recent_title}".\n\n'
            'Your episodes would make killer Shorts if someone clipped them. IncuBrix does '
            'exactly that. Want to see?'
        ),
        "instagram_fu1": (
            'Hey {first_name}, circling back. Curious if clipping is still manual on your side.'
        ),
        "instagram_fu2": (
            'Hey {first_name}, last ping! If repurposing ever becomes a headache, IncuBrix is here.'
        ),
    },
    "youtube_first": {
        "email_subject": 'Your "{recent_title}" has a second life on Shorts',
        "email_1": (
            'Hi {first_name},\n\n'
            'Saw "{recent_title}" in your recent uploads.\n\n'
            'The full video is strong, but the 2-3 moments that would work best as Shorts are '
            'buried in the middle. Most creators know this and still don\'t clip, because editing '
            '8 Shorts from one video takes a full weekend.\n\n'
            'IncuBrix pulls those moments out, adds captions, and gives you the Shorts + a written '
            'post draft in one pass. Worth a 2-min look?'
        ),
        "email_fu1": (
            'Hi {first_name}, quick nudge.\n\n'
            'How many Shorts did "{recent_title}" actually turn into? If the answer is 0 or 1, '
            'the ROI of repurposing is bigger than you think.'
        ),
        "email_fu2": (
            'Hi {first_name}, closing the loop.\n\n'
            'If repurposing is on your roadmap this quarter, IncuBrix turns one video into a '
            'Shorts pack + captions + a written post draft automatically.'
        ),
        "linkedin_1": (
            'Hi {first_name}, saw "{recent_title}".\n\n'
            'Most YouTube-first creators leave 6-10 Shorts on the table per video. IncuBrix '
            'extracts them + captions + a written post draft in one pass. 2-min look?'
        ),
        "linkedin_fu1": (
            'Hi {first_name}, circling back. If repurposing is still manual on your side, IncuBrix '
            'handles clip selection + captions + cross-post copy.'
        ),
        "linkedin_fu2": (
            'Hi {first_name}, closing the loop. If YouTube-to-Shorts is on your list, happy to '
            'show IncuBrix in 2 min.'
        ),
        "instagram_1": (
            'Hey {first_name}, saw "{recent_title}".\n\n'
            'There\'s easily 6-8 Shorts buried in it. IncuBrix pulls them out + captions them. '
            'Want a 2-min look?'
        ),
        "instagram_fu1": (
            'Hey {first_name}, following up — is clipping still a weekend project for you?'
        ),
        "instagram_fu2": (
            'Hey {first_name}, last note from me! If YouTube-to-Shorts is on your list, IncuBrix '
            'is worth 2 min.'
        ),
    },
    "expert_led": {
        "email_subject": 'Turning "{recent_title}" into pipeline',
        "email_1": (
            'Hi {first_name},\n\n'
            'Came across "{recent_title}" in your recent uploads.\n\n'
            'You already publish content that generates inbound leads. The problem most coaches '
            'and consultants hit is that one strong video stays one video — it never becomes the '
            '5 LinkedIn posts, the newsletter issue, or the clips that keep the funnel full '
            'between launches.\n\n'
            'IncuBrix solves that: one long-form video in, a week of cross-posted content out. '
            'Would a 2-min walkthrough be useful?'
        ),
        "email_fu1": (
            'Hi {first_name}, quick follow-up.\n\n'
            'For most coaches and consultants, the ROI of content isn\'t views — it\'s discovery '
            'calls. If "{recent_title}" only lived as one video, the second, third, and fourth '
            'pieces that would have driven those calls never happened.'
        ),
        "email_fu2": (
            'Hi {first_name}, last note from me.\n\n'
            'If repurposing is on your list, IncuBrix is built for exactly this. If it\'s not, '
            'totally fine — the content you\'re publishing is good and worth the listen.'
        ),
        "linkedin_1": (
            'Hi {first_name}, saw "{recent_title}".\n\n'
            'One pattern with coaches and consultants: content-to-leads is the goal — but one '
            'strong video usually stays one video. IncuBrix turns it into a week of cross-posted '
            'content. 2-min walkthrough?'
        ),
        "linkedin_fu1": (
            'Hi {first_name}, quick follow-up. If "{recent_title}" only lived as one video, the '
            'LinkedIn posts + newsletter blurb + clips that would have driven discovery calls '
            'never got made. IncuBrix fixes that in one pass.'
        ),
        "linkedin_fu2": (
            'Hi {first_name}, last note. If repurposing is on the roadmap this quarter, I\'d love '
            'to show what IncuBrix does on your content.'
        ),
        "instagram_1": (
            'Hey {first_name}, saw "{recent_title}".\n\n'
            'Coaches and consultants tend to run into this: content-to-leads is the goal, but one '
            'video usually stays one video. IncuBrix turns it into a week of posts. Open to a '
            '2-min look?'
        ),
        "instagram_fu1": (
            'Hey {first_name}, quick follow-up. If "{recent_title}" only lived as one video, '
            'there\'s a whole week of content that never got made.'
        ),
        "instagram_fu2": (
            'Hey {first_name}, last ping! If repurposing is on the roadmap, happy to show IncuBrix.'
        ),
    },
}


def _build_context(lead):
    recent_title = (
        lead.get("recent_video_title")
        or lead.get("personalization_hook", "").strip('"')
        or "your most recent video"
    )
    return {
        "first_name": _first_name(lead.get("creator_name", "")),
        "recent_title": recent_title,
    }


def generate_priority_a_pack(lead, ai_data=None):
    lead_id = lead.get("lead_id") or "UNKNOWN"
    name = lead.get("creator_name") or "there"
    platform = lead.get("primary_platform") or "YouTube"
    segment = pick_segment(lead)

    logger.info(f"Generating pack | lead={lead_id} | segment={segment} | name={name}")

    if ai_data is None:
        recent_title = lead.get("recent_video_title") or "recent content"
        try:
            ai_data = generate_personalized_outreach(
                creator_name=name, recent_video_title=recent_title, channel_name=platform)
        except Exception as e:
            logger.warning(f"AI call failed for {lead_id}: {e}")
            ai_data = {"hook": ""}

    ctx = _build_context(lead)
    tpl = SEGMENT_TEMPLATES[segment]

    email_subject = _safe_format(tpl["email_subject"], ctx)
    email_1 = _safe_format(tpl["email_1"], ctx) + EMAIL_SIGN_OFF
    email_fu1 = _safe_format(tpl["email_fu1"], ctx) + EMAIL_SIGN_OFF
    email_fu2 = _safe_format(tpl["email_fu2"], ctx) + EMAIL_SIGN_OFF
    li_1 = _safe_format(tpl["linkedin_1"], ctx) + SHORT_SIGN_OFF
    li_fu1 = _safe_format(tpl["linkedin_fu1"], ctx) + SHORT_SIGN_OFF
    li_fu2 = _safe_format(tpl["linkedin_fu2"], ctx) + SHORT_SIGN_OFF
    ig_1 = _safe_format(tpl["instagram_1"], ctx) + SHORT_SIGN_OFF
    ig_fu1 = _safe_format(tpl["instagram_fu1"], ctx) + SHORT_SIGN_OFF
    ig_fu2 = _safe_format(tpl["instagram_fu2"], ctx) + SHORT_SIGN_OFF

    lines = [
        f"# Outreach pack — {name}", "",
        f"- **lead_id:** `{lead_id}`",
        f"- **segment:** `{segment}`",
        f"- **platform:** {platform}",
        f"- **best channel:** {lead.get('best_channel', 'Email')}",
        f"- **backup channel:** {lead.get('backup_channel') or 'N/A'}",
        f"- **channel handle/URL:** {lead.get('channel_handle_or_url', 'N/A')}",
        f"- **country:** {lead.get('country_iso2', 'N/A')}",
        f"- **incubrix_need:** {lead.get('incubrix_need', 'N/A')}",
        f"- **monetization_signal:** {lead.get('monetization_signal', 'N/A')}",
        f"- **generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "> **Compliance:** LinkedIn and Instagram messages must be sent MANUALLY. "
        "Platform terms forbid automated bulk DMs. Human review before sending.",
        "", "---", "",
    ]

    for channel, subject, m1, m2, m3 in [
        ("EMAIL", email_subject, email_1, email_fu1, email_fu2),
        ("LINKEDIN (manual send only)", None, li_1, li_fu1, li_fu2),
        ("INSTAGRAM (manual send only)", None, ig_1, ig_fu1, ig_fu2),
    ]:
        ch_key = channel.split()[0].lower()
        if subject:
            lines += [f"## {channel}", "", f"**Subject:** {subject}", ""]
        else:
            lines += [f"## {channel}", ""]
        lines += [
            "### Message 1 — send now", "```", m1, "```",
            f"_Tracking:_ {_tracking_link(lead_id, ch_key, 1)}", "",
            "### Follow-up 1 — send +3 days", "```", m2, "```",
            f"_Tracking:_ {_tracking_link(lead_id, ch_key, 2)}", "",
            "### Follow-up 2 — send +7 days", "```", m3, "```",
            f"_Tracking:_ {_tracking_link(lead_id, ch_key, 3)}", "",
            "---", "",
        ]

    out_path = OUT_DIR / f"{lead_id}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote pack: {out_path} | segment={segment}")
    return out_path


def _load_priority_a(db_path, lead_id=None):
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if lead_id:
            rows = conn.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads WHERE candidate_status='Qualified' AND priority='A'"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from-db", type=Path, default=DATA_DIR / "production.db")
    p.add_argument("--lead-id", type=str)
    p.add_argument("--test-names", action="store_true",
                   help="Print _first_name() results for common cases")
    args = p.parse_args()

    if args.test_names:
        for n in ["Acquiring Minds", "Capital Allocators with Ted Seides",
                  "Andrew Giancola", "In the Money", "Beansprout",
                  "Ted Seides", "The Financial Freedom Podcast", "Sarah Johnson"]:
            print(f"{n!r:55} -> {_first_name(n)!r}")
        return

    leads = _load_priority_a(args.from_db, lead_id=args.lead_id)
    if not leads:
        print(f"No Priority A leads found in {args.from_db}")
        return

    print(f"Generating packs for {len(leads)} Priority A lead(s)...")
    ok, fail = 0, 0
    for lead in leads:
        try:
            path = generate_priority_a_pack(lead)
            print(f"  OK {lead.get('lead_id')} -> {path.name}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {lead.get('lead_id')}: {e}")
            fail += 1

    print(f"\nDone. Success: {ok} | Failed: {fail}")


if __name__ == "__main__":
    main()