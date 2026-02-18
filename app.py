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

        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 1rem !important;
            max-width: 98% !important;
        }

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
        .kpi-value { font-size: 1.1rem; font-weight: 800; margin: 0; }

        .section-header {
            color: var(--text-main) !important;
            font-weight: 800;
            font-size: 1.1rem;
            margin: 15px 0 10px 0;
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

# --- TECHNICIAN TEAM MAPPING ---
def get_team_from_technician(name):
    sits_support = [
        "L.V Sudesh Dilhan", "Nuwan Weerasekara", "Mahela Ekanayaka", "Anushka Nayanatharu",
        "Ruchira lakshitha bowandeniya", "Rusith Singhabahu", "Haritha Madhubhashana",
        "Nirantha Madhushanka", "Kavinda Nethmal", "Heshan Lakshitha", "Sanath Manjula",
        "Nadeesh Madhushan", "H.D.P Pradeep", "Dilan Madhawa", "SITS IT Support",
        "Sayanthan Rasalinkam", "Malmi Nandasiri", "Uthayananthan Thanushanth",
        "Ashan Aravinda", "Chameera Maduranga", "Praneeth Dilhan", "Lahiru Oshan",
        "Sajith Salinda", "Ramesh Neranjan", "Rasika Dulshan", "Romesh Seneviratne",
        "Sanjeewan Suthanthirabalan", "Supun Lakpriya", "Vishan Kenneth", "Kasun Karunasena",
        "Kanagesh Kugan", "Jineth Gayan", "Pramuditha Ranganath", "Kalpa Senarathna"
    ]
    gamma_it = [
        "Madhuka Gunaweera", "Vijay Philipkumar", "Chamal Dakshana", "Jeevan Indrajith",
        "Preshan Silva", "Kavindu Basilu", "Nimna Mendis", "Janindu Hewaalankarage",
        "Hasitha Munasinghe", "Gamma IT Group", "Maduka Pramoditha", "Sameera Rukshan",
        "Hashan Madushanka"
    ]
    service_desk = [
        "Mariyadas Melisha", "Apeksha Nilupuli", "Sahan Dananjaya", "Pathum Malshan",
        "Sasanka Madusith", "Ositha Buddika"
    ]
    
    if name in sits_support: return "SITS IT Support"
    if name in gamma_it: return "Gamma IT"
    if name in service_desk: return "Service Desk"
    return "Unassigned"

def process_data_safely(df):
    if df is None or df.empty: return pd.DataFrame()
    tto_col = next((c for c in ['SLA tto passed', 'TTO passed'] if c in df.columns), None)
    ttr_col = next((c for c in ['SLA ttr passed', 'TTR passed'] if c in df.columns), None)
    a_col = next((c for c in ['Agent->Full name', 'Agent'] if c in df.columns), None)
    
    # 1 if No (meaning NOT passed/failed), 0 if Yes (meaning SLA was breached)
    # We define 'Done' as meeting the SLA.
    df['TTO_Done'] = df[tto_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if tto_col else 0
    df['TTR_Done'] = df[ttr_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if ttr_col else 0
    
    if 'Status' in df.columns:
        df['Is_Pending'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'pending' else 0)
        df['Is_Closed'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'closed' else 0)
    
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
    
    if a_col:
        df['Mapped_Team'] = df[a_col].apply(get_team_from_technician)
    
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
t_col = 'Mapped_Team'
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

    units = ["All Departments", "SITS IT Support", "Gamma IT", "Service Desk"]
    selected_unit = st.selectbox("Operational Unit", units)
    
    all_orgs_list = ["All Customers"] + sorted(df_base[c_col].dropna().unique().tolist()) if c_col else ["All Customers"]
    selected_org = st.selectbox("Select Customer", all_orgs_list)
    
    st.markdown("### EXCLUSIONS")
    orgs_for_exclusion = sorted(df_base[c_col].dropna().unique().tolist()) if c_col else []
    excluded_orgs = st.multiselect("Exclude Organizations", orgs_for_exclusion)
    
    all_agents = sorted(df_base[a_col].dropna().unique().tolist()) if a_col else []
    excluded_agents = st.multiselect("Exclude Agents", all_agents)
    
    if st.button("LOGOUT SESSION", use_container_width=True):
        st.session_state.data = pd.DataFrame()
        st.rerun()

# --- FILTERING ---
df = df_base.copy()
if selected_org != "All Customers" and c_col:
    df = df[df[c_col] == selected_org]

if 'Status' in df.columns:
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
if selected_unit != "All Departments": 
    df = df[df[t_col] == selected_unit]
if excluded_orgs and c_col:
    df = df[~df[c_col].isin(excluded_orgs)]
if excluded_agents and a_col:
    df = df[~df[a_col].isin(excluded_agents)]

# --- BREACH CALCULATIONS ---
total_v = max(1, len(df))
tto_breach_count = len(df) - df['TTO_Done'].sum()
ttr_breach_count = len(df) - df['TTR_Done'].sum()
tto_breach_pct = (tto_breach_count / total_v) * 100
ttr_breach_pct = (ttr_breach_count / total_v) * 100

# --- MAIN INTERFACE ---
if aged_count > 0:
    st.error(f"⚠️ CRITICAL ALERT: {aged_count} Pending tickets have been open for more than 30 days!")

st.markdown(f'<div class="header-box"><h2>CXP ANALYTICS: {selected_unit.upper()}</h2></div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Main Dashboard", "Top Performers"])

with tab1:
    st.markdown('<span class="section-header">Performance & Breach Overview</span>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: kpi_card("Total Volume", len(df))
    with k2: kpi_card("TTO Breaches", f"{tto_breach_count} ({tto_breach_pct:.1f}%)", color="#D32F2F")
    with k3: kpi_card("TTR Breaches", f"{ttr_breach_count} ({ttr_breach_pct:.1f}%)", color="#D32F2F")
    with k4: kpi_card("Total Backlog", backlog_val, color="#1F3B4D")
    with k5: kpi_card("Aged (>30 Days)", aged_count, color="#7B1FA2")

    # Status Breakdown Row
    if 'Status' in df.columns:
        status_counts = df['Status'].value_counts()
        stat_cols = st.columns(len(status_counts) if len(status_counts) > 0 else 1)
        for i, (name, count) in enumerate(status_counts.items()):
            with stat_cols[i]:
                s_color = "#2E7D32" if name.lower() == 'closed' else "#1976D2" if name.lower() == 'assigned' else "#FBC02D" if name.lower() == 'resolved' else "#FF6600"
                kpi_card(name, count, color=s_color)

    # Top 10 Customers Row
    if c_col:
        st.markdown('<span class="section-header">Top 10 Customers by Ticket Volume</span>', unsafe_allow_html=True)
        top_cust = df.groupby(c_col)['Ref'].count().reset_index().sort_values('Ref', ascending=False).head(10)
        top_cust.columns = ['Customer Name', 'Ticket Count']
        
        c_chart, c_table = st.columns([1.5, 1])
        with c_chart:
            fig_cust = px.bar(top_cust, x='Ticket Count', y='Customer Name', orientation='h', color_discrete_sequence=['#FF6600'])
            fig_cust.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cust, use_container_width=True)
        with c_table:
            st.dataframe(top_cust, use_container_width=True, hide_index=True, height=300)

    # Monthly SLA Analysis
    if 'Start date' in df.columns:
        df['Month'] = df['Start date'].dt.to_period('M').astype(str)
        monthly = df.groupby('Month').agg({'Ref':'count','TTO_Done':'sum','TTR_Done':'sum'}).reset_index()
        monthly['TTO %'] = (monthly['TTO_Done'] / monthly['Ref'] * 100).round(1)
        monthly['TTR %'] = (monthly['TTR_Done'] / monthly['Ref'] * 100).round(1)
        
        st.markdown('<span class="section-header">Monthly SLA Analysis</span>', unsafe_allow_html=True)
        cl, cr = st.columns([1.5, 1])
        with cl:
            fig = px.bar(monthly, x='Month', y=['TTO %', 'TTR %'], barmode='group', color_discrete_map={'TTO %': '#FF6600', 'TTR %': '#1F3B4D'})
            fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1, x=1))
            st.plotly_chart(fig, use_container_width=True)
        with cr:
            st.dataframe(monthly, use_container_width=True, hide_index=True, height=280)

    # Aged Tickets Details
    if aged_count > 0:
        st.markdown('<span class="section-header" style="color:#7B1FA2 !important;">Aged Pending Tickets Details (>30 Days)</span>', unsafe_allow_html=True)
        aged_cols = ['Ref', 'Title', 'Start date', a_col]
        if reason_col: aged_cols.append(reason_col)
        st.dataframe(aged_df[aged_cols].sort_values('Start date'), use_container_width=True, hide_index=True)

    # Pending Queue
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

with tab2:
    if a_col:
        perf_data = df.groupby([a_col, t_col]).agg({
            'Ref': 'count',
            'TTO_Done': 'sum',
            'TTR_Done': 'sum'
        }).reset_index()
        perf_data.columns = ['Agent', 'Department', 'Tickets', 'TTO Met', 'TTR Met']
        
        # Calculate met percentages and breach counts
        perf_data['TTO %'] = (perf_data['TTO Met'] / perf_data['Tickets'] * 100).round(1)
        perf_data['TTR %'] = (perf_data['TTR Met'] / perf_data['Tickets'] * 100).round(1)
        perf_data['Total Breaches'] = (perf_data['Tickets'] * 2) - (perf_data['TTO Met'] + perf_data['TTR Met'])

        depts = ["SITS IT Support", "Gamma IT", "Service Desk"]
        for dept in depts:
            dept_df = perf_data[perf_data['Department'] == dept].sort_values('Tickets', ascending=False)
            if not dept_df.empty:
                st.markdown(f'<span class="section-header">{dept.upper()} PERSONNEL PERFORMANCE</span>', unsafe_allow_html=True)
                st.dataframe(dept_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"No active data for {dept} in current filter.")
