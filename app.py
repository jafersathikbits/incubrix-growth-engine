import streamlit as st
import pandas as pd
import time
import os
from main import run_engine
from src.exporter import export_to_csv
from src.config import DATA_DIR
from src.email_sender import send_test_email

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
# SESSION STATE INIT (Prevents screen reset on download)
# ------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "results_df" not in st.session_state:
    st.session_state.results_df = None
if "priority_a_df" not in st.session_state:
    st.session_state.priority_a_df = None
if "execution_time" not in st.session_state:
    st.session_state.execution_time = 0.0

def toggle_dark_mode():
    st.session_state.dark_mode = not st.session_state.dark_mode

# ------------------------------------------------------------------
# DYNAMIC THEME VARIABLES
# ------------------------------------------------------------------
if st.session_state.dark_mode:
    bg = "#0F172A"
    text = "#F8FAFC"
    card_bg = "#1E293B"
    card_border = "#334155"
    input_bg = "#334155"
    input_border = "#475569"
    btn_bg = "#F8FAFC"
    btn_text = "#0F172A"
    popover_bg = "#1E293B"
else:
    bg = "#F8FAFC"
    text = "#1E293B"
    card_bg = "#FFFFFF"
    card_border = "#E5E7EB"
    input_bg = "#FFFFFF"
    input_border = "#D1D5DB"
    btn_bg = "#111827"
    btn_text = "#FFFFFF"
    popover_bg = "#FFFFFF"

# ------------------------------------------------------------------
# INJECT CSS
# ------------------------------------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {{ background-color: {bg} !important; }}
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {{ color: {text} !important; font-family: 'Inter', sans-serif; }}
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .block-container {{ padding-top: 2rem; max-width: 1400px; }}
    
    .stTextInput input, .stNumberInput input, .stTextArea textarea {{
        border-radius: 6px !important;
        border: 1px solid {input_border} !important;
        background-color: {input_bg} !important;
        color: {text} !important;
    }}
    
    .stButton>button {{
        background-color: {btn_bg} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        border: 1px solid {btn_bg} !important;
        width: 100%;
    }}
    .stButton>button * {{ color: {btn_text} !important; }}
    
    .stDownloadButton>button {{
        background-color: {card_bg} !important;
        color: {text} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        border: 1px solid {card_border} !important;
    }}
    
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {card_bg} !important;
        border-radius: 8px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        border: 1px solid {card_border} !important;
        padding: 1.5rem;
    }}
    
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border-color: {input_border} !important;
        color: {text} !important;
    }}
    
    div[data-baseweb="popover"] > div {{
        background-color: {popover_bg} !important;
        color: {text} !important;
        border: 1px solid {card_border} !important;
    }}
    ul[role="listbox"] li {{ color: {text} !important; }}
    ul[role="listbox"] li:hover {{ background-color: {input_border} !important; }}
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# HEADER & DARK MODE TOGGLE
# ------------------------------------------------------------------
col_title, col_toggle = st.columns([8, 2])
with col_title:
    st.title("IncuBrix Growth Engine")
    st.markdown("Automated creator discovery, qualification, and multi-channel outreach drafting.")
with col_toggle:
    st.write("") 
    st.write("") 
    st.toggle("Dark Mode", value=st.session_state.dark_mode, on_change=toggle_dark_mode)

st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# MAIN UI CONTAINER
# ------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### 1. Define Your Target Audience")
    
    col_src, col_seg = st.columns(2)
    with col_src:
        source_filter = st.radio("Data Sources to Search", ["All (YouTube + Podcasts)", "YouTube Only", "Podcasts Only"], horizontal=True)
    with col_seg:
        segment_filter = st.radio("Target Creator Segment", ["All", "Expert-led", "Podcaster", "YouTube-first"], horizontal=True)

    st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)
    
    st.markdown("### 2. Search Parameters")
    
    search_queries = st.multiselect(
        "Search Keywords (Type any letter A-Z to see suggestions, or add your own)",
        options=ALL_KEYWORDS, 
        default=[], 
        accept_new_options=True,
        help="Click and type any letter (A-Z) to see high-converting suggestions. You can also type your own custom keyword and press Enter."
    )

    limit = st.number_input("Max Leads to Generate (Total)", min_value=10, max_value=10000, value=20, step=10)

    st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)

    st.markdown("### 3. Quality Filters")
    
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        min_subs = st.number_input("Min Subscribers (YouTube only)", value=5000, step=1000)
    with f_col2:
        max_subs = st.number_input("Max Subscribers (YouTube only)", value=100000, step=10000)
    with f_col3:
        english_only = st.toggle("English Content Only", value=True)

    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        min_vids_30d = st.number_input("Min Videos (Last 30d)", value=8, step=1)
    with g_col2:
        min_vids_60d = st.number_input("Min Longform (Last 60d)", value=2, step=1)
    with g_col3:
        filter_commercial = st.toggle("Require Commercial Intent (Selling a course, sponsor, etc.)", value=True)

    st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)
    
    run_button = st.button("Execute Engine", width='stretch', type="primary")

# ------------------------------------------------------------------
# EXECUTION LOGIC (Stored in Session State)
# ------------------------------------------------------------------
if run_button:
    if not search_queries:
        st.warning("Please enter at least one search keyword.")
    else:
        db_path = DATA_DIR / "ui_sandbox.db"
        full_csv = DATA_DIR / "ui_results.csv"
        priority_csv = DATA_DIR / "ui_priority_a.csv"

        if os.path.exists(db_path):
            os.remove(db_path)

        src_arg = "All" if "All" in source_filter else ("YouTube" if "YouTube" in source_filter else "Podcast")
        seg_arg = segment_filter

        start_time = time.time()
        with st.status("Executing pipeline...", expanded=True) as status:
            st.write(f"Searching {source_filter} for {segment_filter} using keywords: {search_queries}...")
            try:
                run_engine(
                    db_path, limit=limit, custom_queries=search_queries, filter_commercial=filter_commercial,
                    min_subs=min_subs, max_subs=max_subs, min_vids_30d=min_vids_30d,
                    min_vids_60d=min_vids_60d, english_only=english_only,
                    source_filter=src_arg, segment_filter=seg_arg
                )
                export_to_csv(str(db_path), str(full_csv), str(priority_csv))
                
                # SAVE TO SESSION STATE
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
# DISPLAY RESULTS (Survives reruns if data exists in session state)
# ------------------------------------------------------------------
if st.session_state.results_df is not None and len(st.session_state.results_df) > 0:
    df = st.session_state.results_df
    priority_a_df = st.session_state.priority_a_df
    runtime = st.session_state.execution_time

    st.markdown(f"<hr style='margin: 1.5rem 0; border-color: {card_border};'>", unsafe_allow_html=True)
    st.markdown("### Execution Summary")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads Extracted", len(df))
    m2.metric("Priority A Targets", len(df[df["priority"] == "A"]))
    m3.metric("Total Audience Reach", f"{df['followers_or_subscribers'].sum():,}")
    m4.metric("Execution Time", f"{runtime}s")

    st.markdown("### Qualified Leads Database")
    
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
            "creator_name": st.column_config.TextColumn("Creator Name", width="medium"),
            "creator_segment": st.column_config.TextColumn("Segment", width="small"),
            "primary_platform": st.column_config.TextColumn("Platform", width="small"),
            "profile_url": st.column_config.LinkColumn("Profile Link"),
            "followers_or_subscribers": st.column_config.NumberColumn("Subscribers", format="%d"),
            "incubrix_need": st.column_config.TextColumn("IncuBrix Need", width="medium"),
            "monetization_signal": st.column_config.TextColumn("Monetization"),
            "best_channel": st.column_config.TextColumn("Best Channel"),
            "channel_handle_or_url": st.column_config.LinkColumn("Contact Link", display_text=r"mailto:(.*)|(.*)"),
            "priority": st.column_config.TextColumn("Priority", width="small"),
            "lead_score": st.column_config.ProgressColumn("Lead Score", format="%d", min_value=0, max_value=100),
            "first_message": st.column_config.TextColumn("AI Outreach Draft", width="large"),
        },
    )

    st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)
    st.markdown("### Export Data")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(
            label="Download Full Results (ui_results.csv)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name="ui_results.csv",
            mime="text/csv",
            width='stretch',
        )
    with d_col2:
        if not priority_a_df.empty:
            st.download_button(
                label="Download Priority A Only (ui_priority_a.csv)",
                data=priority_a_df.to_csv(index=False).encode('utf-8'),
                file_name="ui_priority_a.csv",
                mime="text/csv",
                width='stretch',
            )

    st.markdown(f"<hr style='margin: 1rem 0; border-color: {card_border};'>", unsafe_allow_html=True)
    st.markdown("### Seed Test: Send Live Outreach")
    
    available_leads = display_df["creator_name"].tolist()
    if not available_leads:
        st.warning("No leads available for the selected filters.")
    else:
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            selected_lead = st.selectbox("Select Lead", available_leads)
        with t_col2:
            test_email = st.text_input("Send To (Test Email)", value="test@example.com")

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
                        st.success(f"✅ {msg} Check your inbox!")
                    else:
                        st.error(f"❌ Failed to send: {msg}")