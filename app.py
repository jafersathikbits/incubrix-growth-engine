import streamlit as st
import pandas as pd
import time
import os
from main import run_engine
from src.exporter import export_to_csv
from src.config import DATA_DIR
from src.email_sender import send_test_email

st.set_page_config(page_title="IncuBrix Growth Engine", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 2rem; max-width: 1400px; }
    h1 { font-weight: 600; color: #111827; letter-spacing: -0.5px; font-size: 1.8rem; margin-bottom: 0.5rem;}
    h3 { font-weight: 600; color: #374151; font-size: 1.1rem; margin-bottom: 1rem;}
    p { color: #6B7280; font-size: 0.95rem; }
    .stTextArea textarea, .stNumberInput input, .stTextInput input {
        border-radius: 6px !important;
        border: 1px solid #D1D5DB !important;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        box-shadow: none !important;
    }
    .stButton>button {
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        border: 1px solid #111827 !important;
        width: 100%;
    }
    .stButton>button:hover { background-color: #374151 !important; }
    .stDownloadButton>button {
        background-color: #FFFFFF !important;
        color: #374151 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        border: 1px solid #D1D5DB !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
        padding: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("IncuBrix Growth Engine")
st.markdown("Automated creator discovery, qualification, and multi-channel outreach drafting.")
st.markdown("<hr style='margin: 1rem 0; border-color: #E5E7EB;'>", unsafe_allow_html=True)

# Initialize Session State to hold data across button clicks
if 'df' not in st.session_state:
    st.session_state['df'] = None
if 'runtime' not in st.session_state:
    st.session_state['runtime'] = 0

with st.container(border=True):
    st.markdown("### Engine Configuration")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        custom_keywords = st.text_area(
            "Search Queries (comma separated)", 
            "business podcast, tech coaching, SaaS tutorial, real estate coaching",
            height=80
        )
    with col2:
        limit = st.number_input("Max Leads to Generate", min_value=1, max_value=10000, value=20, step=10)
        
    st.markdown("<hr style='margin: 1rem 0; border-color: #E5E7EB;'>", unsafe_allow_html=True)
    
    st.markdown("**Audience & Activity Rules**")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        min_subs = st.number_input("Min Subscribers", value=5000, step=1000)
    with f_col2:
        max_subs = st.number_input("Max Subscribers", value=100000, step=10000)
    with f_col3:
        english_only = st.toggle("English Content Only", value=True)

    st.markdown("**Content & Commercial Rules**")
    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        min_vids_30d = st.number_input("Min Videos (Last 30d)", value=8, step=1)
    with g_col2:
        min_vids_60d = st.number_input("Min Longform (Last 60d)", value=2, step=1)
    with g_col3:
        filter_commercial = st.toggle("Require Commercial Intent", value=True)

    st.markdown("<hr style='margin: 1rem 0; border-color: #E5E7EB;'>", unsafe_allow_html=True)
    run_button = st.button("Execute Engine", width="stretch")

if run_button:
    queries = [q.strip() for q in custom_keywords.split(",") if q.strip()]
    db_path = DATA_DIR / "leads.db"
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    start_time = time.time()
    
    with st.status("Executing pipeline...", expanded=True) as status:
        st.write(f"Initializing with limits: {min_subs}-{max_subs} subs...")
        try:
            run_engine(
                limit=limit, custom_queries=queries, filter_commercial=filter_commercial,
                min_subs=min_subs, max_subs=max_subs, min_vids_30d=min_vids_30d,
                min_vids_60d=min_vids_60d, english_only=english_only
            )
            export_to_csv()
            st.session_state['runtime'] = round(time.time() - start_time, 2)
            status.update(label="Pipeline completed successfully.", state="complete", expanded=False)
            
            # Load CSV into session state
            csv_path = DATA_DIR / "leads.csv"
            if os.path.exists(csv_path):
                st.session_state['df'] = pd.read_csv(csv_path)
                
        except Exception as e:
            st.session_state['runtime'] = round(time.time() - start_time, 2)
            status.update(label=f"Pipeline halted: {e}", state="error", expanded=False)

# Display Results from Session State (Persists across button clicks)
if st.session_state['df'] is not None and len(st.session_state['df']) > 0:
    df = st.session_state['df']
    
    st.markdown("<hr style='margin: 1.5rem 0; border-color: #E5E7EB;'>", unsafe_allow_html=True)
    st.markdown("### Execution Summary")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads Extracted", len(df))
    m2.metric("Priority A Targets", len(df[df['priority'] == 'A']))
    m3.metric("Total Audience Reach", f"{df['followers_or_subscribers'].sum():,}")
    m4.metric("Execution Time", f"{st.session_state['runtime']}s")
    
    st.markdown("### Qualified Leads Database")
    
    display_df = df[[
        'creator_name', 'profile_url', 'followers_or_subscribers', 'incubrix_need', 
        'monetization_signal', 'best_channel', 'channel_handle_or_url', 'priority', 'lead_score', 'first_message'
    ]].copy()
    
    def format_contact_link(val):
        if pd.isna(val) or not val: return val
        if "@" in val and not val.startswith("mailto:"):
            return f"mailto:{val}"
        return val
        
    display_df['channel_handle_or_url'] = display_df['channel_handle_or_url'].apply(format_contact_link)
    
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "creator_name": st.column_config.TextColumn("Creator Name", width="medium"),
            "profile_url": st.column_config.LinkColumn("YouTube Channel", display_text=r"https://youtube\.com/channel/(.*)"),
            "followers_or_subscribers": st.column_config.NumberColumn("Subscribers", format="%d"),
            "incubrix_need": st.column_config.TextColumn("IncuBrix Need", width="medium"),
            "monetization_signal": st.column_config.TextColumn("Monetization"),
            "best_channel": st.column_config.TextColumn("Best Channel"),
            "channel_handle_or_url": st.column_config.LinkColumn("Contact Link", display_text=r"mailto:(.*)|(.*)"),
            "priority": st.column_config.TextColumn("Priority", width="small"),
            "lead_score": st.column_config.ProgressColumn("Lead Score", format="%d", min_value=0, max_value=100),
            "first_message": st.column_config.TextColumn("AI Outreach Draft", width="large"),
        }
    )
    
    # --- SEED TEST SECTION ---
    st.markdown("<br><hr style='margin: 1rem 0; border-color: #E5E7EB;'>", unsafe_allow_html=True)
    st.markdown("### Seed Test: Send Live Outreach")
    st.markdown("Select a lead below to send their AI-drafted email to your own test account.")
    
    t_col1, t_col2 = st.columns([2, 1])
    with t_col1:
        selected_lead = st.selectbox(
            "Select Lead", 
            df['creator_name'].tolist(),
            help="Pick a creator to see their AI message."
        )
    with t_col2:
        test_email = st.text_input("Send To (Test Email)", value="test@example.com")
        
    lead_row = df[df['creator_name'] == selected_lead].iloc[0]
    message_preview = lead_row['first_message']
    
    st.code(message_preview, language="text")
    
    # Use a form or unique key to prevent instant rerun loop
    if st.button("Send Test Email", key="send_email_btn"):
        if test_email == "test@example.com" or "@" not in test_email:
            st.error("Please enter a valid test email address.")
        else:
            with st.spinner("Sending email..."):
                success, msg = send_test_email(
                    to_email=test_email, 
                    subject=f"IncuBrix Outreach Test: {selected_lead}", 
                    body=message_preview
                )
                if success:
                    st.success(f"✅ {msg} Check your inbox!")
                else:
                    st.error(f"❌ Failed to send: {msg}")

    st.markdown("<br>", unsafe_allow_html=True)
    csv_path = DATA_DIR / "leads.csv"
    if os.path.exists(csv_path):
        with open(csv_path, "rb") as file:
            st.download_button(
                label="Download leads.csv",
                data=file,
                file_name="incubrix_leads.csv",
                mime="text/csv",
            )