import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="SITS Analytics Portal", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- LOGO PATH ---
LOGO_PATH = r"C:\Users\malki.p\Desktop\Power BI\assets\logo.png"

# --- INITIALIZE SESSION STATE ---
if "data" not in st.session_state: 
    st.session_state.data = pd.DataFrame()

# --- THEME ADAPTIVE STYLING ---
def apply_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        
        /* Define Dynamic Variables for Light/Dark Mode */
        :root {
            --bg-card: #ffffff;
            --text-main: #1F3B4D;
            --text-sub: #666666;
            --border-color: #f0f0f0;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-card: #1E1E1E;
                --text-main: #E0E0E0;
                --text-sub: #AAAAAA;
                --border-color: #333333;
            }
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem !important;
        }

        /* COMPACT LAYOUT WHILE PRESERVING TOP BAR */
        .block-container {
            padding-top: 3rem !important; /* Standard space to show the top bar */
            padding-bottom: 1rem !important;
            max-width: 98% !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #1F3B4D !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] h3 {
            color: white !important;
        }

        button {
            background-color: #FF6600 !important;
            color: white !important;
            border-radius: 6px !important;
            border: none !important;
        }

        .header-box {
            background: #FF6600;
            padding: 8px 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            color: white !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-box h2 { color: white !important; margin: 0; font-size: 1.1rem; font-weight: 700; }

        .kpi-wrapper {
            background-color: var(--bg-card);
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }
        .kpi-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; color: var(--text-sub); margin: 0; }
        .kpi-value { font-size: 1.2rem; font-weight: 800; margin: 0; }

        .section-header {
            color: var(--text-main) !important;
            font-weight: 800;
            font-size: 1.2rem;
            margin: 10px 0 5px 0;
            display: block;
            border-left: 3px solid #FF6600;
            padding-left: 10px;
        }

        footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

def kpi_card(label, value, color="#FF6600"):
    st.markdown(f'''
        <div class="kpi-wrapper" style="border-left: 5px solid {color};">
            <p class="kpi-label">{label}</p>
            <p class="kpi-value" style="color: {color};">{value}</p>
        </div>
    ''', unsafe_allow_html=True)

def process_data_safely(df):
    if df is None or df.empty: return pd.DataFrame()
    tto_col = next((c for c in ['SLA tto passed', 'TTO passed'] if c in df.columns), None)
    ttr_col = next((c for c in ['SLA ttr passed', 'TTR passed'] if c in df.columns), None)
    
    df['TTO_Done'] = df[tto_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if tto_col else 0
    df['TTR_Done'] = df[ttr_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if ttr_col else 0
    
    if 'Status' in df.columns:
        df['Is_Pending'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'pending' else 0)
        df['Is_Closed'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'closed' else 0)
    
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
    
    if 'Ref' not in df.columns: df['Ref'] = range(len(df))
    return df

apply_styles()

# --- LOGIN ---
if st.session_state.data.empty:
    st.markdown("<style>[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        st.markdown('<div style="text-align:center; margin-top:25vh; background:white; padding:30px; border-radius:15px; border-top:5px solid #FF6600; box-shadow: 0 10px 25px rgba(0,0,0,0.1);"><h2 style="color:#FF6600; margin:0;">SITS</h2><p style="font-size:0.7rem; color:#666;">ANALYTICS GATEWAY</p></div>', unsafe_allow_html=True)
        pwd = st.text_input("Access Key", type="password", placeholder="Key", label_visibility="collapsed")
        if pwd == "Admin@CXP":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("CONNECT", use_container_width=True):
                    url = "https://cxp.sits.lk/webservices/export-v2.php?format=spreadsheet&query=15"
                    res = requests.get(url, auth=("malki.p", "Abc@1234"))
                    st.session_state.data = process_data_safely(pd.read_excel(BytesIO(res.content)))
                    st.rerun()
            with c2:
                login_up = st.file_uploader("Upload", type=['xlsx', 'csv'], label_visibility="collapsed")
                if login_up:
                    df_up = pd.read_csv(login_up, encoding='latin1') if login_up.name.endswith('.csv') else pd.read_excel(login_up)
                    st.session_state.data = process_data_safely(df_up)
                    st.rerun()
    st.stop()

# --- DATA PREP ---
df_base = st.session_state.data.copy()
t_col = next((c for c in ['Team->Name', 'Team'] if c in df_base.columns), None)
a_col = next((c for c in ['Agent->Full name', 'Agent'] if c in df_base.columns), None)
c_col = next((c for c in ['Organization->Name', 'Organization'] if c in df_base.columns), None)
reason_col = next((c for c in ['Pending reason', 'Pending Reason'] if c in df_base.columns), None)

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=180)
    st.markdown("### DATA MANAGEMENT")
    new_data = st.file_uploader("Refresh Dataset", type=['xlsx', 'csv'])
    if new_data:
        df_new = pd.read_csv(new_data, encoding='latin1') if new_data.name.endswith('.csv') else pd.read_excel(new_data)
        st.session_state.data = process_data_safely(df_new)
        st.rerun()
    
    st.markdown("---")
    st.markdown("### DATE FILTER")
    if 'Start date' in df_base.columns:
        valid_dates = df_base['Start date'].dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
            selected_dates = st.date_input("Select Range", value=(min_date, max_date))
        else: selected_dates = None
    else: selected_dates = None

    units = ["All Departments"] + sorted(df_base[t_col].dropna().unique().tolist()) if t_col else ["All Departments"]
    selected_unit = st.selectbox("Operational Unit", units)
    
    # Customer Selection Filter (Changed from multiselect to selectbox)
    all_orgs_list = ["All Customers"] + sorted(df_base[c_col].dropna().unique().tolist()) if c_col else ["All Customers"]
    selected_org = st.selectbox("Select Customer", all_orgs_list)
    
    st.markdown("### EXCLUSIONS")
    # Exclusion list remains sorted without the "All" prefix as it is meant for specific exclusions
    orgs_for_exclusion = sorted(df_base[c_col].dropna().unique().tolist()) if c_col else []
    excluded_orgs = st.multiselect("Exclude Organizations", orgs_for_exclusion)
    
    all_agents = sorted(df_base[a_col].dropna().unique().tolist()) if a_col else []
    excluded_agents = st.multiselect("Exclude Agents", all_agents)
    
    if st.button("LOGOUT SESSION", use_container_width=True):
        st.session_state.data = pd.DataFrame()
        st.rerun()

# --- FILTERING ---
df = df_base.copy()

# Apply Customer Selection Filter (Updated logic for single selection)
if selected_org != "All Customers" and c_col:
    df = df[df[c_col] == selected_org]

if 'Status' in df.columns:
    # Calculate backlog based on current selection (including customer filter)
    backlog_val = len(df[df['Status'].astype(str).str.strip().str.lower() == 'pending'])
else:
    backlog_val = 0

one_month_ago = datetime.now() - timedelta(days=30)
if 'Status' in df.columns and 'Start date' in df.columns:
    aged_df = df[(df['Status'].astype(str).str.strip().str.lower() == 'pending') & (df['Start date'] < one_month_ago)]
    aged_count = len(aged_df)
else:
    aged_count, aged_df = 0, pd.DataFrame()

if selected_dates and len(selected_dates) == 2:
    df = df[(df['Start date'].dt.date >= selected_dates[0]) & (df['Start date'].dt.date <= selected_dates[1])]
if t_col and selected_unit != "All Departments": 
    df = df[df[t_col] == selected_unit]
if excluded_orgs and c_col:
    df = df[~df[c_col].isin(excluded_orgs)]
if excluded_agents and a_col:
    df = df[~df[a_col].isin(excluded_agents)]

# --- MAIN DASHBOARD ---
if aged_count > 0:
    st.warning(f"CRITICAL ALERT: There are {aged_count} Pending tickets that have been open for more than 30 days!")

st.markdown(f'<div class="header-box"><h2>CXP ANALYTICS: {selected_unit.upper()}</h2></div>', unsafe_allow_html=True)

# ROW 1
st.markdown('<span class="section-header">Performance Overview</span>', unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)
with k1: kpi_card("Selected Volume", len(df))
with k2: kpi_card("TTO Performance", f"{(df['TTO_Done'].sum()/max(1,len(df))*100):.1f}%")
with k3: kpi_card("TTR Performance", f"{(df['TTR_Done'].sum()/max(1,len(df))*100):.1f}%")
with k4: kpi_card("Live Total Backlog", backlog_val, color="#FF0000")
with k5: kpi_card("Aged (>30 Days)", aged_count, color="#7B1FA2")

# ROW 2
st.markdown('<span class="section-header">Total Tickets by Status</span>', unsafe_allow_html=True)
if 'Status' in df.columns:
    status_counts = df['Status'].value_counts()
    stat_cols = st.columns(len(status_counts) if len(status_counts) > 0 else 1)
    for i, (name, count) in enumerate(status_counts.items()):
        with stat_cols[i]:
            s_color = "#2E7D32" if name.lower() == 'closed' else "#1976D2" if name.lower() == 'assigned' else "#FBC02D" if name.lower() == 'resolved' else "#FF6600"
            kpi_card(name, count, color=s_color)

# --- MONTHLY ANALYSIS ---
if 'Start date' in df.columns:
    df['Month'] = df['Start date'].dt.to_period('M').astype(str)
    monthly = df.groupby('Month').agg({'Ref':'count','TTO_Done':'sum','TTR_Done':'sum','Is_Closed':'sum'}).reset_index()
    monthly['TTO %'] = (monthly['TTO_Done'] / monthly['Ref'] * 100).round(1)
    monthly['TTR %'] = (monthly['TTR_Done'] / monthly['Ref'] * 100).round(1)
else: monthly = pd.DataFrame()

st.markdown('<span class="section-header">Monthly SLA Analysis</span>', unsafe_allow_html=True)
cl, cr = st.columns([1.5, 1])
with cl:
    if not monthly.empty:
        fig = px.bar(monthly, x='Month', y=['TTO %', 'TTR %'], barmode='group', color_discrete_map={'TTO %': '#FF6600', 'TTR %': '#1F3B4D'})
        is_dark = st.get_option("theme.base") == "dark"
        f_color = "#E0E0E0" if is_dark else "#333333"
        g_color = "#333333" if is_dark else "#f0f0f0"
        fig.update_layout(
            height=280, margin=dict(l=0,r=0,t=10,b=0), 
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=f_color),
            legend=dict(orientation="h", y=1.1, x=1, font=dict(color=f_color)),
            xaxis=dict(tickfont=dict(color=f_color), showgrid=False),
            yaxis=dict(tickfont=dict(color=f_color), gridcolor=g_color)
        )
        st.plotly_chart(fig, use_container_width=True)
with cr:
    st.dataframe(monthly, use_container_width=True, hide_index=True, height=280)

# --- AGED TICKETS QUEUE ---
if aged_count > 0:
    st.markdown('<span class="section-header" style="color:#7B1FA2 !important;">Aged Pending Tickets Details</span>', unsafe_allow_html=True)
    aged_cols = ['Ref', 'Title', 'Start date', a_col]
    if reason_col: aged_cols.append(reason_col)
    st.dataframe(aged_df[aged_cols].sort_values('Start date'), use_container_width=True, hide_index=True)

# --- PENDING QUEUE WITH SEARCH ---
st.markdown('<span class="section-header">All Pending Tickets Queue</span>', unsafe_allow_html=True)
if 'Status' in df.columns:
    pending_display = df[df['Status'].astype(str).str.strip().str.lower() == 'pending'].copy()
    if not pending_display.empty:
        search_query = st.text_input("Search Pending Tickets", placeholder="Ref or Title...")
        if search_query:
            pending_display = pending_display[
                pending_display['Ref'].astype(str).str.contains(search_query, case=False, na=False) |
                pending_display['Title'].astype(str).str.contains(search_query, case=False, na=False)
            ]
        cols = ['Ref', 'Title', 'Status', a_col]
        if reason_col: cols.append(reason_col)
        st.dataframe(pending_display.sort_values('Ref'), use_container_width=True, hide_index=True)