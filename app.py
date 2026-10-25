import streamlit as st
import pandas as pd
import time
import os
import shutil   # <-- NEW: used to wipe the UI workspace on each run
import main # Import main to patch state files
from main import run_engine # Import run_engine directly
from src.exporter import export_to_csv
from src.config import DATA_DIR
from src.email_sender import send_test_email

# ------------------------------------------------------------------
# TRUE SANDBOX ISOLATION (Prevents interference with terminal run)
# ------------------------------------------------------------------
# Every file the UI run produces (DB, CSVs, state files, and anything
# else run_engine writes) lives inside this folder. The terminal run
# uses DATA_DIR defaults, so the two never collide.
UI_WORKSPACE = DATA_DIR / "ui_workspace"
UI_WORKSPACE.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="IncuBrix Growth Engine", layout="wide")

# ------------------------------------------------------------------
# A-Z HIGH-CONVERTING KEYWORDS FOR INCUBRIX
# ------------------------------------------------------------------
KEYWORD_DICT = {
    "A": ["AI", "Analytics", "App", "Agency", "Automation", "Affiliate", "Author", "Advertising", "Audio", "Accounting"],
    "B": ["Business", "B2B", "Branding", "Blogging", "Books", "Blockchain", "Bootstrapping", "Broadcast", "Budgeting", "Beauty", "Business Coach"],
    "C": ["Creator", "Coaching", "Consulting", "Crypto", "Content", "Course", "Career", "Copywriting", "Community", "Coding"],
    "D": ["Design", "Development", "Digital", "Data", "Dropshipping", "Dating", "DIY", "Domain", "Dance", "Drawing"],
    "E": ["Ecommerce", "Education", "Entrepreneurship", "Editing", "Email", "Engineering", "Entertainment", "Events", "Expert", "Ebooks", "Entrepreneur"],
    "F": ["Finance", "Fitness", "Freelance", "Fashion", "Food", "Film", "Founders", "Forex", "Funnels", "Furniture"],
    "G": ["Growth", "Gaming", "Graphic design", "Gardening", "Google Ads", "Gadgets", "Guitar", "Geometry"],
    "H": ["Health", "Hacking", "HR", "History", "Home", "Hardware", "Hustle", "Hair", "Healthcare", "Housing"],
    "I": ["Investing", "Instagram", "IT", "Insurance", "Interior design", "Internet", "Innovation", "Illustration"],
    "J": ["JavaScript", "Journalism", "Jobs", "Java", "Jewelry", "Judaism", "Jazz"],
    "K": ["Knowledge", "Kids", "Kitchen", "Kindle", "KDP", "Keto", "Kickstarter", "Knitting", "Kubernetes"],
    "L": ["Leadership", "Lifestyle", "Language", "Law", "LinkedIn", "Learning", "Logistics", "Luxury", "Life coaching", "Legal"],
    "M": ["Marketing", "Music", "Management", "Mobile", "Money", "Motivation", "Meditation", "Masterclass", "Motherhood", "Mechanics"],
    "N": ["Networking", "News", "Nutrition", "Node.js", "Nonprofit", "Nursing", "Nature", "Negotiation", "NFTs"],
    "O": ["Operations", "Outdoor", "Online", "Office", "Organization", "Organic", "Optimization", "Ocean"],
    "P": ["Podcast", "Product", "Python", "Photography", "Politics", "Psychology", "Programming", "Personal finance", "Productivity"],
    "Q": ["Quotes", "Quality", "Quantum", "Quizzes", "Questions", "Quantitative", "QuickBooks"],
    "R": ["Real estate", "React", "Relationships", "Running", "Retail", "Recruiting", "Robotics", "Recipes", "Reviews"],
    "S": ["SaaS", "Startup", "Sales", "Social media", "SEO", "Software", "Sports", "Science", "Security", "Selling"],
    "T": ["Tech", "Trading", "Travel", "Teaching", "TikTok", "Therapy", "Tools", "Testing", "Tax", "Team"],
    "U": ["UI/UX", "Universe", "University", "Urban", "UGC", "Underdog", "Unboxing", "Upwork"],
    "V": ["Video", "Vlog", "Virtual reality", "Venture capital", "Voice", "Vegan", "Vacation", "Visual"],
    "W": ["Web3", "Web development", "Workout", "Wellness", "Webinar", "Writing", "Weather", "Wedding", "Wealth"],
    "X": ["X (Twitter)", "Xero", "XML", "Xbox", "Xenial"],
    "Y": ["YouTube", "Yoga", "YCombinator", "Youth", "Yearly planning", "Yachting"],
    "Z": ["Zoom", "Zen", "Zcash", "Zoning", "Zumba", "Zoo"]
}

ALL_KEYWORDS = sorted(list(set([kw for sublist in KEYWORD_DICT.values() for kw in sublist])))

# ------------------------------------------------------------------
# SESSION STATE INIT
# ------------------------------------------------------------------
if "results_df" not in st.session_state:
    st.session_state.results_df = None
if "priority_a_df" not in st.session_state:
    st.session_state.priority_a_df = None
if "execution_time" not in st.session_state:
    st.session_state.execution_time = 0.0

# ------------------------------------------------------------------
# STATIC LIGHT THEME VARIABLES
# ------------------------------------------------------------------
bg = "#F8FAFC"
text = "#1E293B"
card_bg = "#FFFFFF"
card_border = "#E5E7EB"
input_bg = "#FFFFFF"
input_border = "#D1D5DB"
btn_bg = "#4F46E5" # Indigo brand color
btn_text = "#FFFFFF"
placeholder_color = "#9CA3AF"

# ------------------------------------------------------------------
# INJECT CSS (Enterprise Light Mode)
# ------------------------------------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global App Background */
    .stApp, body {{ background-color: {bg} !important; color: {text} !important; }}
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {{ color: {text} !important; font-family: 'Inter', sans-serif; }}
    #MainMenu, header, footer {{visibility: hidden;}}
    .block-container {{ padding-top: 2rem; max-width: 1400px; }}
    
    /* Force All Layouts to be Transparent */
    div[data-testid="stVerticalBlock"], 
    div[data-testid="stHorizontalBlock"], 
    div[data-testid="stMarkdownContainer"],
    div[data-testid="column"] {{ background-color: transparent !important; }}
    
    /* Divider Lines */
    hr {{ border-color: {card_border} !important; margin: 1.5rem 0 !important; }}
    
    /* Inputs & Placeholders */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="input"] {{
        border-radius: 6px !important;
        border: 1px solid {input_border} !important;
        background-color: {input_bg} !important;
        color: {text} !important;
    }}
    .stTextInput input::placeholder, 
    .stNumberInput input::placeholder, 
    .stTextArea textarea::placeholder {{
        color: {placeholder_color} !important;
        opacity: 1 !important; 
    }}
    
    /* Buttons */
    .stButton>button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        border: 1px solid {btn_bg} !important;
        width: 100%;
    }}
    
    .stDownloadButton>button {{
        background-color: {card_bg} !important;
        color: {text} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        border: 1px solid {card_border} !important;
    }}
    
    /* Main Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {card_bg} !important;
        border-radius: 8px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        border: 1px solid {card_border} !important;
        padding: 1.5rem;
    }}
    
    /* Dropdowns (Selectbox / Multiselect) */
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        color: {text} !important;
    }}
    div[data-baseweb="popover"], 
    div[data-baseweb="menu"], 
    div[data-baseweb="popover"] > div,
    ul[data-testid="stSelectboxVirtualDropdown"] {{
        background-color: {card_bg} !important;
        color: {text} !important;
    }}
    ul[role="listbox"] li {{ color: {text} !important; }}
    ul[role="listbox"] li:hover {{ background-color: {bg} !important; }}
    
    /* Multiselect Tags */
    span[data-baseweb="tag"] {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
    }}
    
    /* Info / Alert / Notification Boxes */
    div[data-testid="stNotification"], .stAlert {{
        background-color: {card_bg} !important;
        color: {text} !important;
        border: 1px solid {card_border} !important;
        border-radius: 6px;
    }}
    div[data-testid="stNotification"] p, .stAlert p, .stAlert span, .stAlert div {{
        color: {text} !important;
    }}
    .stAlert svg {{ fill: {text} !important; stroke: {text} !important; }}
    
    /* Expander Fix */
    div[data-testid="stExpander"] {{
        background-color: {card_bg} !important;
        border: 1px solid {card_border} !important;
        border-radius: 6px !important;
    }}
    div[data-testid="stExpander"] summary {{
        background-color: {card_bg} !important;
        color: {text} !important;
    }}
    div[data-testid="stExpander"] summary span,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary svg {{
        color: {text} !important;
        fill: {text} !important;
    }}
    div[data-testid="stExpander"] > div {{
        background-color: {card_bg} !important;
    }}
    
    /* Radio Button Labels */
    div[data-testid="stRadio"] label p {{
        color: {text} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.title("IncuBrix Growth Engine")
st.markdown("Automated creator discovery, qualification, and multi-channel outreach drafting.")

st.markdown("---")

# ------------------------------------------------------------------
# MAIN UI CONTAINER
# ------------------------------------------------------------------
with st.container(border=True):
    
    source_filter = st.radio(
        "Select Search Source", 
        ["All (YouTube + Podcasts)", "YouTube Only", "Podcasts Only"], 
        horizontal=True,
        help="Select where the engine should look for creators. Podcasts require parsing raw RSS feeds and take slightly longer."
    )

    st.markdown("---")
    
    st.markdown("### Search Parameters")
    
    search_queries = st.multiselect(
        "Search Keywords (Select from list OR type your own custom keyword and press Enter)",
        options=ALL_KEYWORDS, 
        default=[], 
        accept_new_options=True,
        help="Type any letter A-Z to see high-converting suggestions. You can also type your own custom keyword and press Enter."
    )

    limit = st.number_input(
        "Max Leads to Generate", 
        min_value=1, max_value=10000, value=None, step=1, placeholder="e.g. 10",
        help="The engine will stop once it reaches this total number of qualified leads."
    )

    st.markdown("---")

    with st.expander("Advanced Quality Filters (Optional)"):
        
        # --- YOUTUBE FILTERS ---
        st.markdown("**YouTube Specific Filters**")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            min_subs = st.number_input(
                "Min Subscribers", min_value=0, value=None, step=1000, placeholder="e.g. 5000",
                help="Sets the minimum audience size. Helps filter out micro-channels with low reach."
            )
        with f_col2:
            max_subs = st.number_input(
                "Max Subscribers", min_value=0, value=None, step=10000, placeholder="e.g. 100000",
                help="Sets the maximum audience size. Helps filter out mega-channels that already have editing teams."
            )
        with f_col3:
            min_vids_30d = st.number_input(
                "Min Videos (Last 30d)", min_value=0, value=None, step=1, placeholder="e.g. 8",
                help="Requires the channel to have uploaded at least this many videos recently."
            )
        
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            min_vids_60d = st.number_input(
                "Min Longform (Last 60d)", min_value=0, value=None, step=1, placeholder="e.g. 2",
                help="Requires the channel to have uploaded at least this many long-form videos recently."
            )
            
        st.markdown("---")
        
        # --- PODCAST FILTERS ---
        st.markdown("**Podcast Specific Filters**")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            min_podcast_episodes = st.number_input(
                "Min Podcast Episodes (Last 30d)", min_value=0, value=None, step=1, placeholder="e.g. 2", 
                help="Checks the RSS XML feed to ensure the podcast has published recently."
            )
            
        st.markdown("---")

        # --- GLOBAL FILTERS ---
        st.markdown("**Global Filters (Applies to both)**")
        gl_col1, gl_col2 = st.columns(2)
        with gl_col1:
            english_only = st.toggle(
                "English Content Only", value=True, 
                help="Rejects leads if non-English words are detected in their recent content."
            )
        with gl_col2:
            filter_commercial = st.toggle(
                "Require Commercial Intent", value=True, 
                help="Only keeps creators who mention sponsors, courses, or products in their bio."
            )

    st.markdown("---")
    
    run_button = st.button("Execute Engine", width='stretch', type="primary")

# ------------------------------------------------------------------
# EXECUTION LOGIC
# ------------------------------------------------------------------
if run_button:
    if not search_queries:
        st.warning("Please enter at least one search keyword.")
    elif limit is None:
        st.warning("Please enter a target number of leads.")
    else:
        # Full isolation: wipe the UI workspace so every UI run starts clean
        shutil.rmtree(UI_WORKSPACE, ignore_errors=True)
        UI_WORKSPACE.mkdir(parents=True, exist_ok=True)

        db_path = UI_WORKSPACE / "ui_sandbox.db"
        full_csv = UI_WORKSPACE / "ui_results.csv"
        priority_csv = UI_WORKSPACE / "ui_priority_a.csv"

        src_arg = "All" if "All" in source_filter else ("YouTube" if "YouTube" in source_filter else "Podcast")
        seg_arg = "All" 

        safe_min_subs = min_subs if min_subs is not None else 0
        safe_max_subs = max_subs if max_subs is not None else 999999999
        safe_min_vids_30d = min_vids_30d if min_vids_30d is not None else 0
        safe_min_vids_60d = min_vids_60d if min_vids_60d is not None else 0
        safe_min_podcast_eps = min_podcast_episodes if min_podcast_episodes is not None else 0

        start_time = time.time()
        
        with st.status("Executing pipeline...", expanded=True) as status:
            st.markdown(f"**Scanning targets:** {', '.join(search_queries)}")
            
            st.markdown("""
            *Engine is actively working in the background:*
            * **Crawling:** Fetching channel statistics and recent uploads.
            * **Parsing:** Reading raw RSS XML feeds (if Podcasts selected).
            * **Scoring:** Calculating Lead Scores based on commercial intent and activity.
            * **Drafting:** Generating personalized AI outreach for Priority A targets.
            """)
            
            try:
                run_engine(
                    db_path, limit=limit, custom_queries=search_queries, filter_commercial=filter_commercial,
                    min_subs=safe_min_subs, max_subs=safe_max_subs, min_vids_30d=safe_min_vids_30d,
                    min_vids_60d=safe_min_vids_60d, english_only=english_only,
                    source_filter=src_arg, segment_filter=seg_arg,
                    resume_mode=False,
                    min_podcast_episodes=safe_min_podcast_eps,
                    workspace=UI_WORKSPACE,   # <-- NEW: sandbox all state files
                )
                export_to_csv(str(db_path), str(full_csv), str(priority_csv))
                
                if os.path.exists(full_csv):
                    st.session_state.results_df = pd.read_csv(full_csv)
                    if os.path.exists(priority_csv):
                        st.session_state.priority_a_df = pd.read_csv(priority_csv)
                    else:
                        st.session_state.priority_a_df = pd.DataFrame()
                
                st.session_state.execution_time = round(time.time() - start_time, 2)
                status.update(label="Pipeline completed successfully.", state="complete", expanded=False)
            except Exception as e:
                status.update(label=f"Pipeline halted: {e}", state="error", expanded=False)

# ------------------------------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------------------------------
if st.session_state.results_df is not None and len(st.session_state.results_df) > 0:
    df = st.session_state.results_df
    priority_a_df = st.session_state.priority_a_df
    runtime = st.session_state.execution_time

    st.markdown("---")
    st.markdown("### Execution Summary")
    
    st.caption("Total Audience Reach calculates the combined subscriber/follower count across all scraped platforms.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads Extracted", len(df))
    m2.metric("Priority A Targets", len(df[df["priority"] == "A"]))
    m3.metric("Total Audience Reach", f"{df['followers_or_subscribers'].sum():,}")
    m4.metric("Execution Time", f"{runtime}s")

    st.markdown("### Qualified Leads Database")
    
    st.caption("**Priority A** leads are the top 5% highest-scoring creators. **Lead Score (0-100)** is calculated based on audience size, content frequency, commercial intent, and recent activity.")

    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        view_segment = st.radio("View Segment", ["All", "Expert-led", "Podcaster", "YouTube-first"], horizontal=True)
    with col_filter2:
        view_platform = st.radio("View Platform", ["All", "YouTube", "Podcast"], horizontal=True)
    with col_filter3:
        view_priority = st.radio("View Priority", ["All", "A", "B", "C"], horizontal=True)

    display_df = df.copy()
    
    if view_segment != "All":
        display_df = display_df[display_df["creator_segment"].str.lower() == view_segment.lower()]
    if view_platform != "All":
        display_df = display_df[display_df["primary_platform"].str.lower() == view_platform.lower()]
    if view_priority != "All":
        display_df = display_df[display_df["priority"] == view_priority]

    display_df = display_df.sort_values(by="lead_score", ascending=False)

    display_df = display_df[[
        "creator_name", "creator_segment", "primary_platform", "profile_url", 
        "followers_or_subscribers", "incubrix_need", "monetization_signal", 
        "best_channel", "channel_handle_or_url", "priority", "lead_score", "first_message",
    ]]

    def format_contact_link(val):
        if pd.isna(val) or not val:
            return val
        if "@" in val and not val.startswith("mailto:"):
            return f"mailto:{val}"
        return val

    display_df["channel_handle_or_url"] = display_df["channel_handle_or_url"].apply(format_contact_link)

    st.dataframe(
        display_df, width='stretch', hide_index=True,
        column_config={
            "creator_name": st.column_config.TextColumn("Creator Name", width="medium", help="Name of the creator or channel"),
            "creator_segment": st.column_config.TextColumn("Segment", width="small", help="Categorized as Expert-led, Podcaster, or YouTube-first"),
            "primary_platform": st.column_config.TextColumn("Platform", width="small"),
            "profile_url": st.column_config.LinkColumn("Profile Link", help="Direct link to their channel"),
            "followers_or_subscribers": st.column_config.NumberColumn("Subscribers", format="%d"),
            "incubrix_need": st.column_config.TextColumn("IncuBrix Need", width="medium", help="Specific reason why they need content repurposing"),
            "monetization_signal": st.column_config.TextColumn("Monetization", help="Evidence they sell a product, course, or have sponsors"),
            "best_channel": st.column_config.TextColumn("Best Channel", help="The optimal channel to reach them first"),
            "channel_handle_or_url": st.column_config.LinkColumn("Contact Link", display_text=r"mailto:(.*)|(.*)", help="Click to email or visit their social profile"),
            "priority": st.column_config.TextColumn("Priority", width="small", help="Top 5% (A), Top 20% (B), Rest (C)"),
            "lead_score": st.column_config.ProgressColumn("Lead Score", format="%d", min_value=0, max_value=100, help="Overall quality score out of 100"),
            "first_message": st.column_config.TextColumn("AI Outreach Draft", width="large", help="AI-generated personalized first message ready to copy/paste"),
        },
    )

    st.markdown("---")
    st.markdown("### Export Data")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(
            label="Download Full Results (ui_results.csv)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name="ui_results.csv",
            mime="text/csv",
            width='stretch',
            help="Download the entire database of leads"
        )
    with d_col2:
        if not priority_a_df.empty:
            st.download_button(
                label="Download Priority A Only (ui_priority_a.csv)",
                data=priority_a_df.to_csv(index=False).encode('utf-8'),
                file_name="ui_priority_a.csv",
                mime="text/csv",
                width='stretch',
                help="Download only the top 5% highest-scoring leads"
            )

    st.markdown("---")
    st.markdown("### Seed Test: Send Live Outreach")
    
    st.caption("Test the email sending functionality instantly using a lead you just scraped.")

    available_leads = display_df["creator_name"].tolist()
    if not available_leads:
        st.warning("No leads available for the selected filters.")
    else:
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            selected_lead = st.selectbox("Select Lead", available_leads, help="Select a lead from the filtered table to preview the AI message.")
        with t_col2:
            test_email = st.text_input("Send To (Test Email)", value="test@example.com", help="Enter a real email address to test the SMTP engine.")

        lead_row = df[df["creator_name"] == selected_lead].iloc[0]
        message_preview = lead_row["first_message"]
        st.code(message_preview, language="text")

        if st.button("Send Test Email", key="send_email_btn"):
            if test_email == "test@example.com" or "@" not in test_email:
                st.error("Please enter a valid test email address.")
            else:
                with st.spinner("Sending email..."):
                    success, msg = send_test_email(
                        to_email=test_email,
                        subject=f"IncuBrix Outreach Test: {selected_lead}",
                        body=message_preview,
                    )
                    if success:
                        st.success(f"{msg} Check your inbox.")
                    else:
                        st.error(f"Failed to send: {msg}")