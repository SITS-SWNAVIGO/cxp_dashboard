import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import base64
from fpdf import FPDF
import master_data_sync
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import os
import base64
from io import BytesIO
import requests
from sqlalchemy import text

# --- 1. CONFIGURATION (MySQL Connection) ---
DB_HOST = "213.210.36.220"
DB_USER = "sits"
DB_PASS = "123456"
DB_NAME = "sits_analytics"
DB_PORT = "3309"

# Using PyMySQL driver (make sure it's installed)
CONNECTION_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="CXP Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. DATABASE ENGINE SETUP ---
# pool_pre_ping=True keeps connection alive
engine = create_engine(
    CONNECTION_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# --- 3. SYSTEM INITIALIZATION ---

# Initialize a global placeholder for the filtered dataframe
df = pd.DataFrame()
@st.cache_resource(show_spinner=False)
def initialize_system():
    """Ensures the users table exists and a super_admin is created."""
    try:
        with engine.connect() as conn:
            # Create User Table if missing
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(255) PRIMARY KEY,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL
                )
            """))
            
            # Check if Super User exists
            admin_check = conn.execute(
                text("SELECT 1 FROM users WHERE username = 'admin'")
            ).fetchone()
            
            if not admin_check:
                conn.execute(text("""
                    INSERT INTO users (username, password, role) 
                    VALUES ('admin', 'Admin@CXP', 'super_admin')
                """))
                
        return True
    except Exception as e:
        # Log the error but don't break sidebar
        print(f"Database Initialization Error: {e}")
        return False

# Run initialization
init_success = initialize_system()
if not init_success:
    st.warning("Database not fully initialized. Some functions may fail.")

# --- 4. DATA & AUTH FUNCTIONS ---

@st.cache_data(show_spinner=False)
def get_db_user(username, password):
    """Authenticates users against the live MySQL database."""
    try:
        with engine.connect() as conn:
            query = text("SELECT role FROM users WHERE username = :u AND password = :p")
            result = conn.execute(query, {"u": username, "p": password}).fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Authentication Error: {e}")  # Avoid blocking UI
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_from_db():
    """Retrieves live analytics data pushed by your local sync script."""
    try:
        with engine.connect() as conn:
            query = text("SELECT * FROM analytics_data")
            return pd.read_sql(query, conn)
    except Exception as e:
        print(f"No data found in database: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_db_last_updated():
    """Displays current status of the Easypanel database connection."""
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM analytics_data")).scalar()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return f"🟢 Live Connection | Records: {count:,} | Last Check: {now_str}"
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return "🔴 Database Connection Offline"

# --- LOGO PATH ---
BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame()

# --- THEME ADAPTIVE STYLING (ULTRA-COMPACT ONE-PAGE OPTIMIZED) ---
def apply_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        
        :root {
            --bg-card: #ffffff;
            --text-main: #1F3B4D;
            --text-sub: #64748B;
            --border-color: #E2E8F0;
            --sidebar-bg: linear-gradient(180deg, #102A43 0%, #061727 100%);
            --sampath-orange: linear-gradient(135deg, #FF6600 0%, #FF8533 100%);
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-card: rgba(30, 30, 30, 0.6);
                --text-main: #F8FAFC;
                --text-sub: #94A3B8;
                --border-color: rgba(255, 255, 255, 0.1);
            }
        }

        /* 1. GLOBAL SPACE ELIMINATION */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem !important;
        }

        .block-container { 
            padding-top: 1rem !important; /* Minimal top space */
            padding-bottom: 0rem !important;
            max-width: 99% !important; 
        }

        /* Tightens the gap between every Streamlit widget */
        [data-testid="stVerticalBlock"] {
            gap: 0.25rem !important;
        }

        /* 2. COMPACT HERO HEADER */
        .hero-title {
            font-size: 1.6rem !important; /* Smaller but bold */
            font-weight: 800 !important;
            background: var(--sampath-orange);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 !important;
            padding: 0 !important;
            text-align: center;
            text-transform: uppercase;
        }

        .hero-subtitle {
            color: var(--text-sub);
            font-size: 0.65rem;
            font-weight: 700;
            text-align: center;
            margin-top: -5px !important;
            margin-bottom: 10px !important;
            opacity: 0.8;
        }
                
        /* 1. TIGHTEN SIDEBAR TOP PADDING */
        [data-testid="stSidebarContent"] {
            padding-top: 0rem !important;
        }

        /* 2. REMOVE SPACING AROUND THE LOGO */
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-top: -45px !important;    /* Pulls the logo up to the very top */
            margin-bottom: -35px !important; /* Pulls the following content up toward the logo */
            text-align: center;
            display: flex;
            justify-content: center;
        }

        /* 3. OPTIONAL: SCALE LOGO FOR BETTER FIT */
        [data-testid="stSidebar"] [data-testid="stImage"] img {
            max-width: 80% !important; /* Slightly smaller logo fits better in compact view */
        }

        /* 1. REFINED CRITICAL ALERT WITH MICRO-MARGINS */
        .critical-alert-box {
            animation: critical-glow 2s infinite;
            padding: 3px 12px !important; 
            border-radius: 20px;
            border: 1px solid rgba(211, 47, 47, 0.4);
            color: #D32F2F; 
            font-weight: 600;
            text-align: center; 
            /* Added 8px top/bottom margin to separate from Sync text and Tabs */
            margin: 8px auto !important; 
            max-width: fit-content;
            font-size: 0.75rem;
            line-height: 1;
            display: block;
        }

        /* 2. DE-CLUTTERING THE TAB ROW */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 8px !important; 
            /* Ensures space between the Alert pill and the Buttons */
            margin-top: 4px !important; 
            margin-bottom: 8px !important;
        }

        /* 3. SUBTLE SYNC TEXT SPACING */
        /* Targets the 'Live Sync Active' text specifically */
        .stMarkdown div p {
            margin-bottom: 2px !important;
        }

        /* 4. BUTTON-SHAPED TABS (SHRUNK) */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 5px !important; }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 15px !important;
            padding: 4px 12px !important;
            font-size: 0.75rem !important;
            height: 30px !important;
        }

        /* 7. KPI METRIC CARDS (ROW SEPARATION FIX) */
        .kpi-wrapper {
            background: var(--bg-card);
            padding: 4px 3px !important;
            border-radius: 6px; 
            border: 1px solid var(--border-color); 
            text-align: center;
            height: 36px !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
            /* This forces space BELOW each card so the next row can't touch it */
            margin-bottom: 15px !important; 
        }

        /* Targets the Streamlit column gap specifically */
        [data-testid="column"] {
            padding-bottom: 10px !important;
        }

        /* Extra separation for the horizontal row containers */
        [data-testid="stHorizontalBlock"] {
            margin-bottom: 8px !important;
            padding-top: 2px !important;
        }

        .kpi-label { 
            font-size: 0.55rem !important; 
            font-weight: 700; 
            color: var(--text-sub); 
            text-transform: uppercase;
            margin-bottom: 1px !important;
        }

        .kpi-value { 
            font-size: 1rem !important; 
            font-weight: 800; 
            color: var(--text-main); 
            line-height: 0.5;
        }
    </style>
    """, unsafe_allow_html=True)

def kpi_card(label, value, color="#FF6600", flash=False):
    flash_class = "flashing-kpi" if flash else ""
    st.markdown(f'''
        <div class="kpi-wrapper {flash_class}" style="border-top: 3px solid {color};">
            <p class="kpi-label">{label}</p>
            <p class="kpi-value" style="color: {color};">{value}</p>
        </div>
    ''', unsafe_allow_html=True)

import pandas as pd

def get_parent_company(name):
    """
    Maps individual branches and subsidiaries into a single Parent Conglomerate.
    Uses 'Aggressive Keyword Detection' to catch typos and branches.
    """
    if pd.isna(name) or not str(name).strip():
        return "Unassigned"
    
    n = str(name).strip().upper()

    # Parent-to-keywords mapping
    mappings = {
        "Hela Clothing": ["HELA", "INDIGLOW", "CLOTHIG"],
        "Central Finance": ["CENTRAL FINANCE", "CF ", "CF-", "CF"],
        "Commercial Bank": ["COMMERCIAL BANK", "COMBANK", "CBC "],
        "Sampath Bank": ["SAMPATH"],
        "Hatton National Bank": ["HATTON NATIONAL", "HNB"],
        "Seylan Bank": ["SEYLAN"],
        "Nations Trust Bank": ["NATIONS TRUST", " NTB"],
        "Pan Asia Bank": ["PAN ASIA"],
        "DFCC Bank": ["DFCC"],
        "John Keells Group": ["JKH", "KELLS", "CINNAMON", "ELEPHANT HOUSE", "UNION ASSURANCE", "WALKERS TOURS"],
        "Hayleys Group": ["HAYLEYS", "ADVANTIS", "SINGER", "KINGSBURY", "DIPPED PRODUCTS", "ALUMEX", "FENTONS", "HAYCARB", "AMAYA"],
        "LOLC / Browns Group": ["LOLC", "BROWNS", "EDEN RESORT", "DICKWEYA", "AGSTAR", "MATURATA"],
        "Vallibel One": ["LB FINANCE", "ROYAL CERAMICS", "ROCELL", "LANKA TILES", "LANKA WALLTILES", "SWISSTEK", "DELMEGE"],
        "Cargills Group": ["CARGILLS", "FOOD CITY", "KFC", "K.F.C", "KIST", "KOTMALE"],
        "Gamma Pizzakraft": ["PIZZA HUT", "PIZZAHUT", "TACO BELL", "TACOBELL", "GAMMA PIZZA", "PIZZAKRAFT"],
        "Abans Group": ["ABANS", "COLOMBO CITY CENTRE", "CCC", "MINISO", "MCDONALDS"],
        "Softlogic": ["SOFTLOGIC", "ASIRI", "GLOMARK", "ODEL", "SKECHERS", "BURGER KING"],
        "Hemas Holdings": ["HEMAS", "ATLAS", "MORISON", "J.L. MORISON"],
        "MAS Holdings": ["MAS HOLDINGS", "MAS ACTIVE", "MAS FABRICS", "BODYLINE", "SLIMLINE"],
        "Brandix": ["BRANDIX", "FORTUDE"],
        "SITS Internal": ["SITS", "SYNERGY", "SMART INFRASTRUCTURE"],
        "IWS": ["SWEDISH CARS", "PURE CEYLON BEVARAGE", "IWS LOGISTICS", 
                "WINDCASTLE", "ART TV", "GERMANIA", "IWS HOLDINGS", 
                "IWS INVESTEMENTS", "IWS AUTOMOBILES", "DYNACOM ELECTRONICS", "EUROCARS"]
    }

    # Convert all keywords to uppercase once
    for parent, keywords in mappings.items():
        keywords_upper = [kw.upper() for kw in keywords]
        if any(kw in n for kw in keywords_upper):
            return parent

    return str(name).strip()

def get_team_from_technician(name):
    """
    Maps a technician's full name to their corresponding team.
    Returns 'Unassigned' if the technician is not in any predefined team.
    """
    if pd.isna(name) or not str(name).strip():
        return "Unassigned"

    name = str(name).strip()

    # Dictionary mapping team name -> list of technicians
    teams = {
        "SITS IT Support": [
            "L.V Sudesh Dilhan", "Nuwan Weerasekara", "Mahela Ekanayaka", "Anushka Nayanatharu",
            "Ruchira lakshitha bowandeniya", "Rusith Singhabahu", "Haritha Madhubhashana",
            "Nirantha Madhushanka", "Kavinda Nethmal", "Heshan Lakshitha", "Sanath Manjula",
            "Nadeesh Madhushan", "H.D.P Pradeep", "Dilan Madhawa", "SITS IT Support",
            "Sayanthan Rasalinkam", "Malmi Nandasiri", "Uthayananthan Thanushanth",
            "Ashan Aravinda", "Chameera Maduranga", "Praneeth Dilhan", "Lahiru Oshan",
            "Sajith Salinda", "Ramesh Neranjan", "Rasika Dulshan", "Romesh Seneviratne",
            "Sanjeewan Suthanthirabalan", "Supun Lakpriya", "Vishan Kenneth", "Kasun Karunasena",
            "Kanagesh Kugan", "Jineth Gayan", "Pramuditha Ranganath", "Kalpa Senarathna",
            "Rusith Tharanga Silva", "Duminda Dayasiri"
        ],
        "Gamma IT": [
            "Madhuka Gunaweera", "Vijay Philipkumar", "Chamal Dakshana", "Jeevan Indrajith",
            "Preshan Silva", "Kavindu Basilu", "Nimna Mendis", "Janindu Hewaalankarage",
            "Hasitha Munasinghe", "Gamma IT Group", "Maduka Pramoditha", "Sameera Rukshan",
            "Hashan Madushanka"
        ],
        "Service Desk": [
            "Mariyadas Melisha", "Apeksha Nilupuli", "Sahan Dananjaya", "Pathum Malshan",
            "Sasanka Madusith", "Ositha Buddika"
        ],
        "Software Dept": [
            "Software Support", "Dev Team", "Application Support"
            # Add more names if needed
        ],
        "Enterprise Team": [
            "Enterprise Support", "Field Engineering", "Project Team", "N.V.P. Rathnayake"
        ]
    }

    # Iterate over dictionary to find team
    for team_name, members in teams.items():
        if name in members:
            return team_name

    return "Unassigned"

# --- 5. DATA PROCESSING ---
def process_data_safely(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # --- UPDATED MAPPING TO MATCH SYNC SCRIPT ---
    col_map = {
        "tto": next((c for c in df.columns if 'TTO' in c.upper()), None),
        "ttr": next((c for c in df.columns if 'TTR' in c.upper()), None),
        "agent": 'Agent' if 'Agent' in df.columns else None,
        "company": 'Customer' if 'Customer' in df.columns else None,
        "start_date": 'Start Date' if 'Start Date' in df.columns else None,
    }

    # 3. SLA Standardization (Simple 1/0 check)
    def check_sla(val):
        return 1 if val == 1 else 0

    if col_map['tto']: df['TTO_Done'] = df[col_map['tto']].apply(check_sla)
    if col_map['ttr']: df['TTR_Done'] = df[col_map['ttr']].apply(check_sla)

    # 4. Date & Status Handling
    if col_map['start_date']:
        df['Start Date'] = pd.to_datetime(df[col_map['start_date']], errors='coerce')

    # 5. Mappings
    df['Mapped_Team'] = df['Agent'].apply(get_team_from_technician) if 'Agent' in df.columns else 'Unassigned'
    df['Parent_Company'] = df['Customer'].apply(get_parent_company) if 'Customer' in df.columns else 'Unassigned'

    return df

# --- 6. STREAMLIT SESSION INITIALIZATION ---
def initialize_session():
    """Ensures essential session state variables exist"""
    session_defaults = {
        "authenticated": False,
        "user_role": None,
        "username": None,
        "data": pd.DataFrame(),
        "last_updated": None
    }

    for key, default in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

initialize_session()

# Apply custom CSS/Styles
try:
    apply_styles()
except NameError:
    pass

# --- HELPER: LOGOUT FUNCTION ---
def logout():
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.data = pd.DataFrame()
    st.rerun()

# --- 2. LOGIN UI ---
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.5, 1])
    
    with center_col:
        logo_html = ""
        if 'LOGO_PATH' in globals() and os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                bin_str = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{bin_str}" style="width:120px; margin-bottom:20px;">'

        st.markdown(f'''
            <div style="text-align:center; margin-top:10vh; background:white; padding:30px; border-radius:15px; border-top:5px solid #FF6600; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                {logo_html}
                <h2 style="color:#FF6600; margin:0; font-family:sans-serif;">CXP ANALYTICS</h2>
                <p style="font-size:0.7rem; color:#666; font-weight:600; text-transform:uppercase; letter-spacing:1px;">Secure Access Portal</p>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        input_user = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        input_pass = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        
        if st.button("LOGIN", use_container_width=True):
            role = get_db_user(input_user, input_pass)
            if role:
                st.session_state.authenticated = True
                st.session_state.user_role = role.lower()
                st.session_state.username = input_user
                
                # Global Auto-Load: Load existing data if it exists in the database
                db_df = load_from_db()
                if not db_df.empty:
                    st.session_state.data = process_data_safely(db_df)
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

    # --- 3. SUPER ADMIN CONTROL PANEL ---
if st.session_state.user_role == "super_admin":
    with st.expander("👤 SUPER ADMIN: CONTROL PANEL", expanded=st.session_state.data.empty):
        t1, t2, t3 = st.tabs(["Register User", "Diagnostics", "User Directory"])
        
        with t1:
            st.subheader("Add New Account")
            nu, np = st.columns(2)
            new_u = nu.text_input("Username", key="reg_u")
            new_p = np.text_input("Password", type="password", key="reg_p")
            new_r = st.selectbox("Role", ["viewer", "manager", "admin", "super_admin"], key="reg_r")
            if st.button("Create User Account", use_container_width=True):
                if new_u and new_p:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"),
                                {"u": new_u, "p": new_p, "r": new_r}
                            )
                        st.success(f"User {new_u} created!")
                    except:
                        st.error("Username already exists.")

        with t2:
            st.subheader("System Health")
            if st.button("Test Connection", use_container_width=True):
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    st.success("✅ Database Connected")
                except Exception as e:
                    st.error(f"Error: {e}")

        with t3:
            st.subheader("User Directory")
            try:
                users_df = pd.read_sql(text("SELECT username, role FROM users"), engine)
                st.dataframe(users_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error: {e}")
        
        st.divider()
        if st.button("EXIT ADMIN SESSION", use_container_width=True, type="secondary"):
            logout()

# --- 4. DATA INITIALIZATION GATE ---
if st.session_state.data.empty:
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.info(f"System Storage: {get_db_last_updated()}")
        
        if st.session_state.user_role in ['super_admin', 'admin']:
            st.markdown("### Administrative Data Setup")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("RESTORE FROM DATABASE", use_container_width=True):
                    db_df = load_from_db()
                    if not db_df.empty:
                        st.session_state.data = process_data_safely(db_df)
                        st.rerun()
            with c2:
                login_up = st.file_uploader("Upload New Data", type=['xlsx', 'csv'], label_visibility="collapsed")
                if login_up:
                    df_up = pd.read_csv(login_up, encoding='latin1') if login_up.name.endswith('.csv') else pd.read_excel(login_up)
                    processed = process_data_safely(df_up)
                    save_to_db(processed)
                    st.session_state.data = processed
                    st.rerun()
            
            if st.button("CONNECT TO LIVE WEB SYNC", use_container_width=True, type="primary"):
                # ... API logic ...
                pass
        else:
            # Viewers see a simpler load button
            if st.button("LOAD ANALYTICS VIEW", use_container_width=True):
                db_df = load_from_db()
                if not db_df.empty:
                    st.session_state.data = process_data_safely(db_df)
                    st.rerun()

    # If script reaches here and data is empty, stop so dashboard doesn't crash
    st.stop()

# --- 5. DASHBOARD CODE STARTS BELOW ---

st.markdown(f"""
    <div style='padding: 10px; border-radius: 5px; background-color: #f0f2f6; margin-bottom: 20px;'>
        <p style='margin: 0; font-size: 0.9rem; color: #666; font-weight: bold;'>
            CXP DASHBOARD: <span style='color: #FF6600;'>{st.session_state.username}</span>
        </p>
    </div>
""", unsafe_allow_html=True)

# --- FIXED SIDEBAR ---
with st.sidebar:
    # Logo
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)
    
    st.markdown("---")
    st.markdown("### FILTERS")
    
    # --- DATA COPY ---
    df_base = st.session_state.data.copy()
    
    # --- DATE FILTER ---
    d_col = next((c for c in df_base.columns if 'start' in c.lower() or 'fixed' in c.lower()), None)
    if d_col and not df_base.empty:
        valid_dates = pd.to_datetime(df_base[d_col], errors='coerce').dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
            col_f, col_t = st.columns(2)
            with col_f:
                date_from = st.date_input("From Date", value=min_date, min_value=min_date, max_value=max_date, key="sidebar_from")
            with col_t:
                date_to = st.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date, key="sidebar_to")
            selected_dates = [date_from, date_to]
        else:
            selected_dates = []
    else:
        selected_dates = []
    
    # --- OPERATIONAL UNIT FILTER ---
    if 'Mapped_Team' in df_base.columns:
        raw_teams = df_base['Mapped_Team'].dropna().unique().tolist()
        available_teams = [t for t in raw_teams if str(t).strip().lower() not in ['unassigned', 'nan', 'none', '']]
        unit_options = ["All Departments"] + sorted(available_teams)
    else:
        unit_options = ["All Departments"]
    selected_unit = st.selectbox("Operational Unit", unit_options)
    
    # --- CUSTOMER FILTER ---
    if 'Parent_Company' in df_base.columns:
        all_parents_list = sorted(df_base['Parent_Company'].dropna().unique().tolist())
    else:
        all_parents_list = []
    all_parents_options = ["All Customers"] + all_parents_list
    selected_org = st.selectbox("Select Customer", all_parents_options)
    
    # --- EXCLUSIONS ---
    excluded_orgs = st.multiselect("Exclude Organizations", all_parents_list)
    
    # --- AGENT EXCLUSIONS ---
    agent_col = next((c for c in df_base.columns if 'agent' in c.lower() or 'full name' in c.lower()), None)
    all_agents = sorted(df_base[agent_col].dropna().unique().tolist()) if agent_col else []
    excluded_agents = st.multiselect("Exclude Agents", all_agents)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("LOGOUT SESSION", use_container_width=True):
        st.session_state.data = pd.DataFrame()
        st.experimental_rerun()

# --- 5. DASHBOARD FILTERING LOGIC ---
# --- 6. FINAL RENDER ---
# We check if the 'df' variable (the one we filtered in Section 5) has data
if not df.empty:
    # This is the "Bridge" - passing the FILTERED data to the UI function
    render_dashboard_content(df)
else:
    # If filters are too strict (e.g. no records for that date), show this:
    st.info("Below records are found to matching the current sidebar filters.")

df = st.session_state.data.copy() if not st.session_state.data.empty else pd.DataFrame()
df_pending = pd.DataFrame()
df_aged = pd.DataFrame()
backlog_val = 0
aged_count = 0

# Ensure selected_dates exists
selected_dates = selected_dates if 'selected_dates' in locals() else None

if not df.empty:
    # --- DATE FILTER ---
    date_col = next((c for c in df.columns if 'start' in c.lower() and 'date' in c.lower()), None)
    if date_col and selected_dates and len(selected_dates) == 2:
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            start_val, end_val = selected_dates
            mask = (df[date_col].dt.date >= start_val) & (df[date_col].dt.date <= end_val)
            df = df.loc[mask].copy()
        except Exception as e:
            st.error(f"Date Filter Error: {e}")

    # --- CUSTOMER FILTER ---
    if 'selected_org' in locals() and selected_org != "All Customers" and 'Parent_Company' in df.columns:
        df = df[df['Parent_Company'] == selected_org]

    # --- UNIT FILTER ---
    if 'selected_unit' in locals() and selected_unit != "All Departments" and 'Mapped_Team' in df.columns:
        df = df[df['Mapped_Team'] == selected_unit]

    # --- EXCLUSIONS ---
    if 'excluded_orgs' in locals() and excluded_orgs and 'Parent_Company' in df.columns:
        df = df[~df['Parent_Company'].isin(excluded_orgs)]

    if 'excluded_agents' in locals() and excluded_agents and a_col in df.columns:
        df = df[~df[a_col].isin(excluded_agents)]

    # --- STATUS & AGED LOGIC ---
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)

    if 'Status' in df.columns and date_col:
        df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
        df_pending = df[df['Status_Clean'] == 'pending'].copy()

        if not df_pending.empty:
            df_pending[date_col] = pd.to_datetime(df_pending[date_col], errors='coerce')
            
            # Handle timezone-naive conversion safely
            if df_pending[date_col].dt.tz is not None:
                temp_dates = df_pending[date_col].dt.tz_localize(None)
            else:
                temp_dates = df_pending[date_col]

            df_aged = df_pending[temp_dates < one_month_ago].copy()
        else:
            df_aged = pd.DataFrame()

        backlog_val = len(df_pending)
        aged_count = len(df_aged)
    else:
        backlog_val = 0
        aged_count = 0
        if not date_col:
            st.warning("Could not find a 'Start Date' column in the data.")

    # --- 2. CALCULATE METRICS (ALIGNED WITH SYNC SCRIPT) ---
    total_v = len(df)
    
    # Identify key columns safely
    sd_col = next((c for c in df.columns if 'start' in c.lower() and 'date' in c.lower()), 'Start Date')
    org_col_name = next((c for c in df.columns if 'customer' in c.lower() or 'organization' in c.lower()), 'Customer')
    
    # Filter for Backlog and Aged tickets
    status_col = 'Status' if 'Status' in df.columns else None
    completed_statuses = ['resolved', 'closed', 'completed', 'done']
    
    if status_col:
        df_pending = df[~df[status_col].astype(str).str.lower().isin(completed_statuses)].copy()
    else:
        df_pending = pd.DataFrame()

    backlog_val = len(df_pending)
    
    # Calculate Aged Tickets (>30 days)
    aged_count = 0
    if not df_pending.empty and sd_col in df_pending.columns:
        df_pending[sd_col] = pd.to_datetime(df_pending[sd_col], errors='coerce')
        now = pd.Timestamp.now()
        df_aged = df_pending[(now - df_pending[sd_col]).dt.days > 30]
        aged_count = len(df_aged)
    else:
        df_aged = pd.DataFrame()

    # SLA Calculations from sync script columns (1 = Met, 0 = Breach)
    tto_met_count = int(df['TTO MET'].sum()) if 'TTO MET' in df.columns else 0
    ttr_met_count = int(df['TTR MET'].sum()) if 'TTR MET' in df.columns else 0

    tto_breach_count = total_v - tto_met_count
    ttr_breach_count = total_v - ttr_met_count

    tto_perf_pct = (tto_met_count / total_v * 100) if total_v > 0 else 0
    ttr_perf_pct = (ttr_met_count / total_v * 100) if total_v > 0 else 0
    
    tto_breach_pct = 100 - tto_perf_pct
    ttr_breach_pct = 100 - ttr_perf_pct

    # --- 3. MAIN INTERFACE & TABS ---
    if aged_count > 0:
        st.markdown(f'<div class="critical-alert-box">⚠️ CRITICAL ALERT: {aged_count} Pending tickets have been open for more than 30 days!</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Main Dashboard", "Personnel Performance", "Group Hierarchy", "Executive Report", "Audit History"])

# --- TAB 1: MAIN DASHBOARD ---
    with tab1:
        import plotly.graph_objects as go
        import pandas as pd
        from datetime import datetime

        # --- 1. PERFORMANCE GAUGES SECTION ---
        st.markdown("### Operational Performance Health")
        
        # Calculate Overall Met/Breach
        overall_met = tto_met_count + ttr_met_count
        overall_breach = tto_breach_count + ttr_breach_count
        total_sla_points = overall_met + overall_breach
        overall_perf_rate = (overall_met / total_sla_points * 100) if total_sla_points > 0 else 0

        # Helper function for Gauge Charts
        def create_gauge(title, value, color):
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = value,
                number = {'suffix': "%", 'font': {'size': 26, 'color': '#1F3B4D'}},
                title = {'text': title, 'font': {'size': 18, 'color': '#1F3B4D'}},
                gauge = {
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#1F3B4D"},
                    'bar': {'color': color},
                    'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "#eeeeee",
                    'steps': [
                        {'range': [0, 75], 'color': '#fde8e8'},
                        {'range': [75, 90], 'color': '#fef9e7'},
                        {'range': [90, 100], 'color': '#e8f5e9'}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 3},
                        'thickness': 0.75,
                        'value': 95 
                    }
                }
            ))
            fig.update_layout(height=220, margin=dict(t=40, b=0, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)')
            return fig

        # Display 3 Gauges side-by-side
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_gauge("OVERALL PERFORMANCE", overall_perf_rate, "#1F3B4D"), use_container_width=True)
        with g2:
            st.plotly_chart(create_gauge("TTO PERFORMANCE", tto_perf_pct, "#2E7D32"), use_container_width=True)
        with g3:
            st.plotly_chart(create_gauge("TTR PERFORMANCE", ttr_perf_pct, "#FF6600"), use_container_width=True)

        # --- NEW: IMPROVED LAST 3 MONTHS PERFORMANCE TABLE (WITH TTO/TTR) ---
        st.markdown("#### Monthly Performance Breakdown")
        if sd_col in df.columns:
            df_m = df.copy()
            df_m[sd_col] = pd.to_datetime(df_m[sd_col], errors='coerce')
            df_m = df_m.dropna(subset=[sd_col])
            df_m['Month'] = df_m[sd_col].dt.strftime('%b %Y')
            df_m['Month_Sort'] = df_m[sd_col].dt.to_period('M')

            # Detailed Monthly Aggregation
            def calc_monthly(x):
                tto_m_total = len(x)
                tto_m_breach = x['TTO_Done'].sum() if 'TTO_Done' in x.columns else 0
                ttr_m_total = len(x[x['Status'] == 'Resolved']) # Only resolved tickets count for TTR
                ttr_m_breach = x['TTR_Done'].sum() if 'TTR_Done' in x.columns else 0
                
                return pd.Series({
                    'Volume': len(x),
                    'TTO Perf %': ((tto_m_total - tto_m_breach) / tto_m_total * 100) if tto_m_total > 0 else 0,
                    'TTR Perf %': ((ttr_m_total - ttr_m_breach) / ttr_m_total * 100) if ttr_m_total > 0 else 0,
                    'Overall %': (((tto_m_total + ttr_m_total) - (tto_m_breach + ttr_m_breach)) / (tto_m_total + ttr_m_total) * 100) if (tto_m_total + ttr_m_total) > 0 else 0
                })

            monthly_perf = df_m.groupby(['Month_Sort', 'Month']).apply(calc_monthly).reset_index()
            monthly_perf = monthly_perf.sort_values('Month_Sort', ascending=False).head(3)

            # Styling logic for text colors based on 95% Target
            def color_sla(val):
                color = '#2E7D32' if val >= 95 else '#FF6600' if val >= 85 else '#D32F2F'
                return f'color: {color}; font-weight: bold'

            # Display the enhanced table
            st.dataframe(
                monthly_perf[['Month', 'Volume', 'TTO Perf %', 'TTR Perf %', 'Overall %']].style
                .format({'TTO Perf %': '{:.1f}%', 'TTR Perf %': '{:.1f}%', 'Overall %': '{:.1f}%'})
                .applymap(color_sla, subset=['TTO Perf %', 'TTR Perf %', 'Overall %']),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Start Date column missing for trend analysis.")

        st.divider()

        # --- 2. DETAILED KPI CARDS (TTO & TTR) ---
        st.markdown("#### Time To Own (TTO) Metrics")
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("TTO PERFORMANCE %", f"{tto_perf_pct:.1f}%", color="#2E7D32" if tto_perf_pct >= 90 else "#FF6600")
        with c2: kpi_card("TTO MET", f"{tto_met_count}", color="#2E7D32")
        with c3: kpi_card("TTO BREACH %", f"{tto_breach_pct:.1f}%", color="#D32F2F")
        with c4: kpi_card("TTO BREACH", tto_breach_count, color="#D32F2F")

        st.markdown("#### Time To Resolve (TTR) Metrics")
        c5, c6, c7, c8 = st.columns(4)
        with c5: kpi_card("TTR PERFORMANCE %", f"{ttr_perf_pct:.1f}%", color="#2E7D32" if ttr_perf_pct >= 90 else "#FF6600")
        with c6: kpi_card("TTR MET", f"{ttr_met_count}", color="#2E7D32")
        with c7: kpi_card("TTR BREACH %", f"{ttr_breach_pct:.1f}%", color="#D32F2F")
        with c8: kpi_card("TTR BREACH", ttr_breach_count, color="#D32F2F")

        # --- 3. VOLUME & STATUS METRICS ---
        st.write("### Overall Volume & Status")
        c9, c10, c11 = st.columns(3)
        with c9: kpi_card("TOTAL VOLUME", total_v, color="#1F3B4D")
        with c10: kpi_card("TOTAL BACKLOG", backlog_val, color="#D32F2F" if backlog_val > 0 else "#1F3B4D", flash=(backlog_val > 0))
        with c11: kpi_card("AGED (>30 DAYS)", aged_count, color="#7B1FA2")

        # Status Cards Row
        if status_col and not df.empty:
            status_counts = df[status_col].value_counts()
            if not status_counts.empty:
                stat_cols = st.columns(len(status_counts))
                for i, (name, count) in enumerate(status_counts.items()):
                    with stat_cols[i]:
                        kpi_card(name.upper(), count, color="#FF6600")

        st.divider()

        # --- 4. ACTIONABLE DATA TABLES ---
        available_cols = [c for c in ['Ref', 'Title', sd_col, 'Agent', org_col_name, 'Status'] if c in df.columns]
        
        col_p, col_a = st.columns(2)
        with col_p:
            st.subheader("Pending Tickets")
            if not df_pending.empty:
                st.dataframe(df_pending[available_cols], use_container_width=True, hide_index=True)
            else:
                st.info("No pending tickets.")
                
        with col_a:
            st.subheader("Aged Tickets (>30 Days)")
            if not df_aged.empty:
                st.dataframe(df_aged[available_cols], use_container_width=True, hide_index=True)
            else:
                st.success("No aged tickets found.")

# --- TAB 2: PERSONNEL PERFORMANCE ---
    with tab2:
        if not df.empty and 'Agent' in df.columns:
            # Aggregate Data by Agent
            agent_stats = df.groupby('Agent').agg(
                Total_Tickets=('Ref', 'count'),
                TTO_Met_Sum=('TTO MET', 'sum'),
                TTR_Met_Sum=('TTR MET', 'sum')
            ).reset_index()

            # Calculate percentages based on the synced MET columns
            agent_stats['TTO %'] = (agent_stats['TTO_Met_Sum'] / agent_stats['Total_Tickets'] * 100).round(1)
            agent_stats['TTR %'] = (agent_stats['TTR_Met_Sum'] / agent_stats['Total_Tickets'] * 100).round(1)
            
            # Sort by volume to show most active agents first
            agent_stats = agent_stats.sort_values(by='Total_Tickets', ascending=False)

            # Chart visualization
            fig_agent = px.bar(
                agent_stats, 
                x='Agent', 
                y=['TTO %', 'TTR %'],
                barmode='group', 
                title="SLA Achievement by Technician",
                color_discrete_map={'TTO %': '#FF6600', 'TTR %': '#1F3B4D'},
                labels={'value': 'Percentage (%)', 'variable': 'Metric'}
            )
            
            # Add target line (83.7%)
            fig_agent.add_hline(y=83.7, line_dash="dot", line_color="red", annotation_text="Target 83.7%")
            fig_agent.update_layout(yaxis_range=[0, 105])
            
            st.plotly_chart(fig_agent, use_container_width=True)

            # Performance Table with Progress Bars
            st.markdown("#### Detailed Personnel Metrics")
            st.dataframe(
                agent_stats[['Agent', 'Total_Tickets', 'TTO %', 'TTR %']],
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Agent": st.column_config.TextColumn("Technician"),
                    "Total_Tickets": st.column_config.NumberColumn("Tickets Handled"),
                    "TTO %": st.column_config.ProgressColumn(
                        "TTO Performance", 
                        min_value=0, 
                        max_value=100, 
                        format="%.1f%%"
                    ),
                    "TTR %": st.column_config.ProgressColumn(
                        "TTR Performance", 
                        min_value=0, 
                        max_value=100, 
                        format="%.1f%%"
                    )
                }
            )
        else:
            st.info("Agent data is not available for the current selection.")

# --- TAB 3: GROUP HIERARCHY ---
    with tab3:
        
        # FORCE MAPPING: Ensure the function runs on the current dataframe
        org_col_for_mapping = next((c for c in df.columns if 'organization' in c.lower() or 'customer' in c.lower()), None)
        if org_col_for_mapping:
            df['Parent_Company'] = df[org_col_for_mapping].apply(get_parent_company)

        if 'Parent_Company' in df.columns:
            # 1. Top Customers Table (Using 'df' instead of 'df_base')
            parent_summary = df.groupby('Parent_Company').agg({
                'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'
            }).reset_index().sort_values('Ref', ascending=False)

            parent_summary['TTO %'] = (parent_summary['TTO_Done'] / parent_summary['Ref'] * 100).fillna(0).round(1)
            parent_summary.columns = ['Parent Conglomerate', 'Total Volume', 'TTO Met', 'TTR Met', 'TTO Compliance %']
            
            st.write("#### Top Customers by Parent Group")
            st.dataframe(parent_summary, use_container_width=True, hide_index=True)
            st.markdown("---")
        
            # 2. Parent Group Distribution
            st.write("#### Parent Group Ticket Distribution")
            parent_list = sorted(df['Parent_Company'].dropna().unique().tolist())
            target_parent = st.selectbox("Select Parent Conglomerate", options=parent_list, key="parent_explorer_select")
            
            if target_parent:
                hierarchy_df = df[df['Parent_Company'] == target_parent]
                
                expected_columns = ['Organization->Name', 'Organization Name', 'Organization', 'Customer', 'Subsidiary']
                actual_org_col = next((c for c in expected_columns if c in hierarchy_df.columns), None)
                
                if actual_org_col:
                    subsidiaries = hierarchy_df.groupby(actual_org_col).agg({
                        'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'
                    }).reset_index().sort_values('Ref', ascending=False)
                    
                    subsidiaries['TTO %'] = (subsidiaries['TTO_Done'] / subsidiaries['Ref'] * 100).fillna(0).round(1)
                    subsidiaries['TTR %'] = (subsidiaries['TTR_Done'] / subsidiaries['Ref'] * 100).fillna(0).round(1)
                    subsidiaries.columns = ['Subsidiary/Brand', 'Ticket Count', 'TTO Met', 'TTR Met', 'TTO Compliance %', 'TTR Compliance %']
                    
                    c_left, c_right = st.columns([1, 1.2])
                    with c_left:
                        st.metric(f"Total Tickets: {target_parent}", len(hierarchy_df))
                        st.dataframe(subsidiaries, use_container_width=True, hide_index=True)
                    with c_right:
                        fig_sub = px.bar(
                            subsidiaries.head(10).sort_values('Ticket Count', ascending=True), 
                            x='Ticket Count', y='Subsidiary/Brand', orientation='h', 
                            title=f"Top 10 Customers in {target_parent}",
                            color_discrete_sequence=['#FF6600'], template="plotly_dark"
                        )
                        fig_sub.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_sub, use_container_width=True)
        else:
            st.warning("Mapping column 'Parent_Company' not found.")

# --- TAB 4: EXECUTIVE REPORT ---
    with tab4:
        st.markdown('<h2 style="color: #FF6600; margin-bottom: 0;">EXECUTIVE SUMMARY</h2>', unsafe_allow_html=True)
        
        # 1. Date Label Logic
        # Checking against the sidebar date filter variables
        if 'start_date' in locals() and 'end_date' in locals():
            date_label = f"{start_date} to {end_date}"
        else:
            date_label = "Full Operational Range"

        st.caption(f"Operational Scope: {selected_unit.upper()} | Period: {date_label}")

        # 2. Performance Metrics Calculation
        # These variables are now derived directly from the 'df' passed into the function
        current_total = len(df)
        
        # Map to the columns established in the sync script
        tto_col = 'TTO MET' if 'TTO MET' in df.columns else 'TTO_Done'
        ttr_col = 'TTR MET' if 'TTR MET' in df.columns else 'TTR_Done'

        rep_tto = (df[tto_col].sum() / current_total * 100) if current_total > 0 and tto_col in df.columns else 0
        rep_ttr = (df[ttr_col].sum() / current_total * 100) if current_total > 0 and ttr_col in df.columns else 0
        
        # Calculate breach count for the risk section
        total_ttr_breaches = (current_total - int(df[ttr_col].sum())) if ttr_col in df.columns else 0

        # Display Top Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Selected Volume", f"{current_total:,}")
        m2.metric("TTO Compliance", f"{rep_tto:.1f}%")
        m3.metric("TTR Compliance", f"{rep_ttr:.1f}%")
        # aged_count is calculated at the top of the render function
        m4.metric("Aged Backlog", aged_count)

        st.divider()

        # 3. Risk Analysis Section
        col_risk, col_drivers = st.columns(2)
        
        with col_risk:
            st.error(f"### Critical Risks\n* **Aged Tickets (>30 Days):** {aged_count}\n* **SLA Breaches (TTR):** {total_ttr_breaches}")
        
        with col_drivers:
            st.info("### Delay Drivers\nTop factors currently impacting resolution times include pending vendor feedback and high-complexity service holds.")

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Board Assets (PDF Generation)
        st.subheader("Board Meeting Assets")
        if st.button("PREPARE PDF REPORT", use_container_width=True):
            try:
                # Passing calculated metrics to your PDF generator function
                pdf_bytes = generate_board_pdf(
                    current_total, 
                    0, # Placeholder for other count if needed
                    rep_tto, 
                    rep_ttr, 
                    aged_count, 
                    total_ttr_breaches, 
                    selected_unit, 
                    date_label, 
                    "General Analysis"
                )
                
                st.download_button(
                    label="DOWNLOAD BOARD-READY PDF BROCHURE",
                    data=pdf_bytes,
                    file_name=f"Executive_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generating report: {e}")
                
# --- TAB 5: AUDIT HISTORY ---
    with tab5:
        
        view_mode = st.radio(
            "Select View Mode:", 
            ["Search Specific Ticket", "View Entire Historical Log"], 
            horizontal=True, 
            key="audit_view_radio"
        )

        try:
            # Using the established SQLAlchemy engine
            with engine.connect() as conn:
                if view_mode == "Search Specific Ticket":
                    search_ref = st.text_input("Enter Ticket Ref ID:", placeholder="e.g. R-154009", key="ticket_search_input")
                    
                    if search_ref:
                        # Use text() for secure parameterized queries
                        query = text("""
                            SELECT Status_Log_Date, Ref, Current_Status, Agent 
                            FROM history_table 
                            WHERE Ref = :ref 
                            ORDER BY Status_Log_Date ASC
                        """)
                        history_df = pd.read_sql(query, conn, params={"ref": search_ref.strip()})
                        
                        if not history_df.empty:
                            # 1. Calculate Duration Logic
                            history_df['Status_Log_Date'] = pd.to_datetime(history_df['Status_Log_Date'])
                            
                            # Calculate time difference between status changes
                            history_df['Duration'] = history_df['Status_Log_Date'].diff().shift(-1)
                            
                            def format_duration(td):
                                if pd.isna(td): return "Active Now"
                                days = td.days
                                hours, remainder = divmod(td.seconds, 3600)
                                minutes, _ = divmod(remainder, 60)
                                if days > 0:
                                    return f"{days}d {hours}h {minutes}m"
                                return f"{hours}h {minutes}m"

                            history_df['Time Spent'] = history_df['Duration'].apply(format_duration)
                            
                            # Prepare for display (Latest status at top)
                            display_df = history_df.sort_values(by='Status_Log_Date', ascending=False).copy()
                            display_df.rename(columns={
                                'Status_Log_Date': 'Date & Time', 
                                'Current_Status': 'Status', 
                                'Ref': 'Ticket ID'
                            }, inplace=True)
                            
                            display_df['Date & Time'] = display_df['Date & Time'].dt.strftime('%Y-%m-%d %H:%M:%S')

                            # 2. Status Highlighting Logic
                            def apply_hc_style(val):
                                s = str(val).strip().lower()
                                if 'resolved' in s: return 'background-color: #28a745; color: white; font-weight: bold;'
                                if 'pending' in s: return 'background-color: #ffc107; color: black; font-weight: bold;'
                                if 'assigned' in s: return 'background-color: #007bff; color: white; font-weight: bold;'
                                if 'escalated' in s: return 'background-color: #dc3545; color: white; font-weight: bold;'
                                return ''

                            st.dataframe(
                                display_df[['Date & Time', 'Status', 'Time Spent', 'Agent']].style.applymap(
                                    apply_hc_style, subset=['Status']
                                ),
                                use_container_width=True, 
                                hide_index=True
                            )
                        else:
                            st.warning(f"No records found for Ticket ID: {search_ref}")

                else:
                    # Full Log View (Limited to 1000 for performance)
                    full_query = text("""
                        SELECT Status_Log_Date as 'Date & Time', 
                               Ref as 'Ticket ID', 
                               Current_Status as 'Status', 
                               Agent 
                        FROM history_table 
                        ORDER BY Status_Log_Date DESC 
                        LIMIT 1000
                    """)
                    full_df = pd.read_sql(full_query, conn)

                    if not full_df.empty:
                        full_df['Date & Time'] = pd.to_datetime(full_df['Date & Time']).dt.strftime('%Y-%m-%d %H:%M:%S')

                        def apply_full_hc_style(val):
                            s = str(val).strip().lower()
                            if 'resolved' in s: return 'background-color: #28a745; color: white; font-weight: bold;'
                            if 'pending' in s: return 'background-color: #ffc107; color: black; font-weight: bold;'
                            if 'assigned' in s: return 'background-color: #007bff; color: white; font-weight: bold;'
                            return 'background-color: #6c757d; color: white;'

                        st.dataframe(
                            full_df.style.applymap(apply_full_hc_style, subset=['Status']),
                            use_container_width=True, 
                            hide_index=True
                        )
                        
                        # Export functionality
                        csv = full_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Export Audit Trail (CSV)", 
                            data=csv, 
                            file_name="audit_trail_export.csv", 
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("The history table is currently empty.")

        except Exception as e:
            st.error(f"Audit Trail System Error: {str(e)}")

# --- 1. PDF CLASS DEFINITION ---
class SITS_Report(FPDF):
    def header(self):
        # Corporate Branding Header
        self.set_fill_color(255, 102, 0)  # SITS Orange
        self.rect(0, 0, 210, 45, 'F')
        
        self.set_y(10)
        self.set_font('Arial', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'EXECUTIVE PERFORMANCE REPORT', 0, 1, 'C')
        
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, f'SITS Operational Analytics - Generated {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Confidential Strategic Document - Page {self.page_no()}', 0, 0, 'C')

def generate_board_pdf(total_v, backlog, tto, ttr, aged, breaches, unit, dates, reasons):
    from fpdf import FPDF
    
    # Internal helper to prevent 'latin-1' encoding crashes
    def clean_text(s):
        if not s:
            return ""
        # Replace common Excel/Word special characters with standard versions
        replacements = {
            '\u2013': '-', # En-dash
            '\u2014': '-', # Em-dash
            '\u2018': "'", # Left single quote
            '\u2019': "'", # Right single quote
            '\u201c': '"', # Left double quote
            '\u201d': '"', # Right double quote
            '\u2022': '*', # Bullet point
        }
        for unicode_char, safe_char in replacements.items():
            s = str(s).replace(unicode_char, safe_char)
        # Final safety: encode to latin-1 and ignore anything else remaining
        return s.encode('latin-1', 'ignore').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    
    # Section I: Executive Overview
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(31, 59, 77)
    pdf.cell(0, 10, clean_text(f'Executive Summary: {unit}'), 0, 1, 'L')
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(50, 50, 50)
    intro_text = clean_text(
        f"This operational audit covers the period: {dates}. "
        f"Total processing volume: {total_v:,} tickets. "
        "Intended for board-level review of resource efficiency and SLA adherence."
    )
    pdf.multi_cell(0, 7, intro_text)
    pdf.ln(8)

    # Section II: Strategic KPI Grid
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(255, 102, 0)
    pdf.cell(0, 10, 'I. Key Performance Indicators', 0, 1, 'L')
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(47, 12, 'Metric Type', 1, 0, 'C', True)
    pdf.cell(47, 12, 'Actual Value', 1, 0, 'C', True)
    pdf.cell(47, 12, 'Benchmark', 1, 0, 'C', True)
    pdf.cell(47, 12, 'Status', 1, 1, 'C', True)

    pdf.set_font('Arial', '', 11)
    metrics = [
        ["Response (TTO)", f"{tto:.1f}%", "90.0%", "HEALTHY" if tto >= 90 else "ACTION REQ."],
        ["Resolution (TTR)", f"{ttr:.1f}%", "90.0%", "HEALTHY" if ttr >= 90 else "BELOW TARGET"],
        ["Pending Volume", str(backlog), "< 100", "STABLE" if backlog < 100 else "HIGH"],
    ]
    
    for row in metrics:
        pdf.cell(47, 10, clean_text(row[0]), 1)
        pdf.cell(47, 10, clean_text(row[1]), 1, 0, 'C')
        pdf.cell(47, 10, clean_text(row[2]), 1, 0, 'C')
        pdf.cell(47, 10, clean_text(row[3]), 1, 1, 'C')
    pdf.ln(10)

    # Section III: Risk Analysis
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(211, 47, 47)
    pdf.cell(0, 10, 'II. Critical Risk Assessment', 0, 1, 'L')
    
    pdf.set_fill_color(255, 245, 245)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    
    clean_reasons = clean_text(reasons).replace("'", "").replace("[", "").replace("]", "")
    risk_summary = clean_text(
        f"Analysis identifies {aged} aged tickets exceeding the 30-day threshold. "
        f"Total SLA breaches recorded: {breaches:,}. "
        f"Priority intervention required for: {clean_reasons}"
    )
    pdf.multi_cell(0, 7, risk_summary, 0, 'L', True)
    
    # Return as safe latin-1 bytes for Streamlit
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 1. THE HARD REFRESH FUNCTION ---
def refresh_data():
    """Wipes the existing DB, runs the sync script, and reloads state"""
    with st.spinner("Deleting old data and syncing fresh Excel..."):
        try:
            # 1. Manually clear Streamlit's cache to prevent seeing old data
            st.cache_data.clear()
            st.cache_resource.clear()
            
            # 2. Trigger the external sync script (This wipes the SQLite table)
            master_data_sync.process_data()
            
            # 3. Pull fresh data from the newly created database
            db_df = load_from_db() # Your function to read sqlite
            if not db_df.empty:
                # Update session state immediately
                st.session_state.data = process_data_safely(db_df)
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                st.toast(f"Success! {len(db_df)} records loaded.")
            else:
                st.error("The database is empty after sync. Check your Excel file.")
                
        except Exception as e:
            st.error(f"Sync failed: {e}")
    
    # Force the app to restart from the top with new data
    st.rerun()

# --- 2. SIDEBAR MANUAL TRIGGER ---
with st.sidebar:
    if st.button("REFRESH & WIPE DB", use_container_width=True, type="primary"):
        refresh_data()
    
    if 'last_update' in st.session_state:
        st.caption(f"Last Hard Sync: {st.session_state.last_update}")
    
    # Debugging count to show you the real-time record total
    if not st.session_state.data.empty:
        st.write(f"**Current Records:** {len(st.session_state.data)}")

# --- 3. AUTO-UPDATE FRAGMENT (30 SECONDS) ---
@st.fragment(run_every=30)
def sync_dashboard_ui():
    """Silently pulls from DB every 30s to update the dashboard charts"""
    # Force a fresh read from the database file on disk
    db_df = load_from_db()
    
    if not db_df.empty:
        # Update the session state silently
        st.session_state.data = process_data_safely(db_df)
        
        # Display the timestamp inside the fragment so you know it's live
        st.caption(f"Live Sync Active (30s) | Last Check: {datetime.now().strftime('%H:%M:%S')}")

# --- 5. MAIN APP EXECUTION ---
if not st.session_state.data.empty:
    # This calls the auto-sync loop
    sync_dashboard_ui()
else:
    st.info("No data available. Click 'REFRESH & WIPE DB' to import data from Excel.")

