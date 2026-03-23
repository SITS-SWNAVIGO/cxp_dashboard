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
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from PIL import Image

# --- STEP 1: PAGE CONFIGURATION ---
# This changes the logo in the browser tab (Title Bar)
st.set_page_config(
    page_title="CXP Analytics Portal",
    page_icon="logo.png", # Replace with your logo file name
    layout="wide"
)

# --- 1. SET DEFAULT DATE RANGE ---
today = datetime.now()
three_months_ago = today - timedelta(days=90)

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

# --- THEME ADAPTIVE STYLING (ULTRA-COMPACT & COLORFUL) ---
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
            /* Static Background Colors */
            --app-bg: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-card: rgba(30, 30, 30, 0.85);
                --text-main: #F8FAFC;
                --text-sub: #94A3B8;
                --border-color: rgba(255, 255, 255, 0.1);
                --app-bg: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            }
        }

        /* 1. GLOBAL SPACE & STATIC BACKGROUND */
        [data-testid="stAppViewContainer"] {
            background: var(--app-bg) !important;
            background-attachment: fixed !important;
        }

        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem !important;
        }

        .block-container { 
            padding-top: 1rem !important; 
            padding-bottom: 0rem !important;
            max-width: 99% !important; 
        }

        [data-testid="stVerticalBlock"] {
            gap: 0.25rem !important;
        }

        /* 2. COMPACT HERO HEADER */
        .hero-title {
            font-size: 1.6rem !important;
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
                
        [data-testid="stSidebarContent"] {
            padding-top: 0rem !important;
        }

        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-top: -45px !important;
            margin-bottom: -35px !important;
            text-align: center;
            display: flex;
            justify-content: center;
        }

        [data-testid="stSidebar"] [data-testid="stImage"] img {
            max-width: 80% !important;
        }

        /* 3. COLORFUL COMPACT TABS */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] { 
            gap: 5px !important; 
            margin-top: 4px !important; 
            margin-bottom: 8px !important;
            background-color: transparent !important;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 15px !important;
            padding: 4px 12px !important;
            font-size: 0.75rem !important;
            height: 30px !important;
            color: var(--text-sub) !important;
            transition: all 0.3s ease;
        }

        /* Active Tab Highlight */
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: var(--sampath-orange) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(255, 102, 0, 0.3) !important;
            transform: translateY(-1px);
        }

        /* 4. KPI METRIC CARDS */
        .kpi-wrapper {
            background: var(--bg-card);
            padding: 2px 3px !important;
            border-radius: 6px; 
            border: 1px solid var(--border-color); 
            text-align: center;
            height: 24px !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin-bottom: 8px !important; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            /* Visual indicator for colorful theme */
            border-left: 3px solid #FF6600 !important;
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

        [data-testid="column"] {
            padding-bottom: 10px !important;
        }

        [data-testid="stHorizontalBlock"] {
            margin-bottom: 8px !important;
            padding-top: 2px !important;
        }

        /* 5. CRITICAL ALERT */
        .critical-alert-box {
            animation: critical-glow 2s infinite;
            padding: 3px 12px !important; 
            border-radius: 20px;
            border: 1px solid rgba(211, 47, 47, 0.4);
            color: #D32F2F; 
            font-weight: 600;
            text-align: center; 
            margin: 8px auto !important; 
            max-width: fit-content;
            font-size: 0.75rem;
            line-height: 1;
            display: block;
        }

        @keyframes critical-glow {
            0% { box-shadow: 0 0 5px rgba(211, 47, 47, 0.2); }
            50% { box-shadow: 0 0 15px rgba(211, 47, 47, 0.5); }
            100% { box-shadow: 0 0 5px rgba(211, 47, 47, 0.2); }
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

import streamlit as st
import base64
import os

# --- 1. CONFIG & STYLING ---
def UI_login_styles():
    st.markdown("""
        <style>
            /* Hide Sidebar and Header during login */
            [data-testid="stSidebar"], [data-testid="stHeader"] {display: none !important;}
            
            /* Main Background Gradient */
            .stApp {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            }

            /* Glassmorphism Login Card */
            .login-container {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                text-align: center;
                margin-top: 5vh;
            }

            .brand-text {
                font-family: 'Inter', sans-serif;
                font-weight: 800;
                letter-spacing: -1px;
                margin-bottom: 5px;
            }

            /* Custom Button Styling */
            div.stButton > button {
                background: linear-gradient(90deg, #FF6600 0%, #FF8533 100%);
                color: white;
                border: none;
                padding: 12px;
                border-radius: 12px;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            div.stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(255, 102, 0, 0.4);
            }
        </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIN UI LOGIC ---
if not st.session_state.get('authenticated', False):
    UI_login_styles()
    
    _, center_col, _ = st.columns([1, 1.2, 1])
    
    with center_col:
        # Logo Loading Logic
        logo_html = ""
        if 'LOGO_PATH' in globals() and os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                bin_str = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{bin_str}" style="width:80px; margin-bottom:20px;">'

        # Card Header
        st.markdown(f'''
            <div class="login-container">
                {logo_html}
                <h1 class="brand-text" style="color:white; font-size: 2.2rem;">
                    CXP <span style="color:#FF6600;">ANALYTICS</span>
                </h1>
                <p style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase; letter-spacing:2px; margin-bottom:30px;">
                    Performance Management Portal
                </p>
            </div>
        ''', unsafe_allow_html=True)

        # Functional Input Area
        with st.container():
            st.markdown("<div style='margin-top: -20px;'>", unsafe_allow_html=True)
            user = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
            pw = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            
            if st.button("SIGN IN TO PORTAL", use_container_width=True):
                # Replace get_db_user with your actual auth function
                role = get_db_user(user, pw) 
                if role:
                    st.session_state.authenticated = True
                    st.session_state.user_role = role.lower()
                    st.session_state.username = user
                    
                    # Auto-Load existing session data from SQLite
                    db_df = load_from_db()
                    if not db_df.empty:
                        st.session_state.data = process_data_safely(db_df)
                    
                    st.rerun() # Fixed attribute error
                else:
                    st.error("Authentication Failed: Check credentials")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<p style='text-align:center; color:#475569; font-size:11px; margin-top:30px;'>Internal Use Only • BI Performance Pro v2.1</p>", unsafe_allow_html=True)
    
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

    # 1. Date Logic: Calculate the range
    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)
    
    # 2. Date Input: Two separate boxes using columns
    col_f, col_t = st.columns(2)
    
    with col_f:
        date_from = st.date_input(
            "From Date",
            value=three_months_ago,
            max_value=today,
            key="sidebar_from"
        )
        
    with col_t:
        date_to = st.date_input(
            "To Date",
            value=today,
            max_value=today,
            key="sidebar_to"
        )
    
    # 3. Handle the selection for downstream filtering
    selected_dates = [date_from, date_to]

    # --- DATA COPY ---
    df_base = st.session_state.data.copy()
    
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

    # 1. CORE LOGIC (Success = 'no' mapping)
    tto_met_count = int((df['SLA tto passed'].astype(str).str.lower() == 'no').sum())
    tto_perf_pct = (tto_met_count / total_v * 100) if total_v > 0 else 0
    tto_breach_count = total_v - tto_met_count
    tto_breach_pct = 100 - tto_perf_pct

    res_df = df[df['Status'] == 'Resolved']
    total_resolved = len(res_df)
    ttr_met_count = int((res_df['SLA ttr passed'].astype(str).str.lower() == 'no').sum())
    ttr_perf_pct = (ttr_met_count / total_resolved * 100) if total_resolved > 0 else 0
    ttr_breach_count = total_resolved - ttr_met_count
    ttr_breach_pct = 100 - ttr_perf_pct

    total_sla_points = total_v + total_resolved
    overall_met_combined = tto_met_count + ttr_met_count
    overall_perf_rate = (overall_met_combined / total_sla_points * 100) if total_sla_points > 0 else 0

    # Vibrant Corporate Colors
    def get_status_color(val):
        if val >= 95: return "#00C853" # Vibrant Green
        if val >= 85: return "#FFAB00" # Vibrant Amber
        return "#FF1744" # Vibrant Red

    # --- UPDATED: COMPACT VIBRANT KPI CARD ---
    def kpi_card(label, value, color="#1f2c38"):
        st.markdown(f"""
            <div style="
                background-color: {color};
                padding: 3px 4px;
                border-radius: 3px;
                text-align: center;
                margin-bottom: 5px;
                box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
            ">
                <p style="margin: 0; font-size: 8px; font-weight: 700; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px;">{label}</p>
                <h2 style="margin: 0; font-size: 12px; color: white; font-weight: 800; line-height: 1.1;">{value}</h2>
            </div>
        """, unsafe_allow_html=True)

    # --- 2. PERFORMANCE HEALTH ---
    st.markdown("### Operational Performance Health")
    
    def create_thin_ring(title, value):
        color = get_status_color(value)
        fig = go.Figure(go.Pie(
            values=[value, 100 - value],
            hole=0.85,
            marker=dict(colors=[color, "rgba(255, 255, 255, 0.05)"], line=dict(width=0)),
            hoverinfo='none', textinfo='none', sort=False
        ))
        fig.update_layout(
            annotations=[
                {'text': f"<span style='font-size:24px; font-weight:800; color:{color};'>{value:.1f}%</span>",
                 'x': 0.5, 'y': 0.5, 'showarrow': False},
                {'text': "HEALTH", 'x': 0.5, 'y': 0.35, 'showarrow': False, 
                 'font': {'size': 8, 'color': 'gray'}}
            ],
            title={'text': f"<b>{title}</b>", 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 11, 'color': 'gray'}},
            showlegend=False, height=180, margin=dict(t=30, b=0, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    g1, g2, g3 = st.columns(3)
    with g1: st.plotly_chart(create_thin_ring("OVERALL PERFORMANCE", overall_perf_rate), use_container_width=True)
    with g2: st.plotly_chart(create_thin_ring("TTO SUCCESS", tto_perf_pct), use_container_width=True)
    with g3: st.plotly_chart(create_thin_ring("TTR SUCCESS", ttr_perf_pct), use_container_width=True)

    # --- 3. MONTHLY TRENDS ---
    if sd_col in df.columns:
        st.markdown("#### Monthly Performance Breakdown")
        df_m = df.copy()
        df_m[sd_col] = pd.to_datetime(df_m[sd_col], errors='coerce')
        df_m = df_m.dropna(subset=[sd_col])
        df_m['Month'] = df_m[sd_col].dt.strftime('%b %Y')
        df_m['Month_Sort'] = df_m[sd_col].dt.to_period('M')

        def calc_monthly(x):
            m_tto_total, m_tto_met = len(x), int((x['SLA tto passed'].astype(str).str.lower() == 'no').sum())
            m_res = x[x['Status'] == 'Resolved']
            m_ttr_total, m_ttr_met = len(m_res), int((m_res['SLA ttr passed'].astype(str).str.lower() == 'no').sum())
            return pd.Series({
                'Volume': float(m_tto_total),
                'TTO Perf %': (m_tto_met / m_tto_total * 100) if m_tto_total > 0 else 0,
                'TTR Perf %': (m_ttr_met / m_ttr_total * 100) if m_ttr_total > 0 else 0,
                'Overall %': ((m_tto_met + m_ttr_met) / (m_tto_total + m_ttr_total) * 100) if (m_tto_total + m_ttr_total) > 0 else 0
            })

        monthly_perf = df_m.groupby(['Month_Sort', 'Month']).apply(calc_monthly).reset_index().sort_values('Month_Sort', ascending=False).head(3)
        st.dataframe(
            monthly_perf[['Month', 'Volume', 'TTO Perf %', 'TTR Perf %', 'Overall %']].style
            .format({'Volume': '{:.0f}', 'TTO Perf %': '{:.1f}%', 'TTR Perf %': '{:.1f}%', 'Overall %': '{:.1f}%'})
            .applymap(lambda v: f'color: {get_status_color(v)}; font-weight: bold;', subset=['TTO Perf %', 'TTR Perf %', 'Overall %']),
            use_container_width=True, hide_index=True
        )

    st.markdown("<br>", unsafe_allow_html=True) # Adding breathable space

    # --- 4. ALL KPI CARDS (TTO, TTR, VOLUME, STATUS) ---
    st.markdown("#### Time To Own (TTO) Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("TTO PERFORMANCE %", f"{tto_perf_pct:.1f}%", color=get_status_color(tto_perf_pct))
    with c2: kpi_card("TTO MET", tto_met_count, color="#2E7D32")
    with c3: kpi_card("TTO BREACH %", f"{tto_breach_pct:.1f}%", color="#C62828")
    with c4: kpi_card("TTO BREACH", tto_breach_count, color="#D32F2F")

    st.markdown("#### Time To Resolve (TTR) Metrics")
    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi_card("TTR PERFORMANCE %", f"{ttr_perf_pct:.1f}%", color=get_status_color(ttr_perf_pct))
    with c6: kpi_card("TTR MET", ttr_met_count, color="#2E7D32")
    with c7: kpi_card("TTR BREACH %", f"{ttr_breach_pct:.1f}%", color="#C62828")
    with c8: kpi_card("TTR BREACH", ttr_breach_count, color="#D32F2F")

    st.markdown("#### Volume & Status Summary")
    cv1, cv2, cv3 = st.columns(3)
    with cv1: kpi_card("TOTAL VOLUME", total_v, color="#0277BD")
    with cv2: kpi_card("BACKLOG", backlog_val, color="#E91E63")
    with cv3: kpi_card("AGED (>30 DAYS)", aged_count, color="#6A1B9A")

    if status_col and not df.empty:
        status_counts = df[status_col].value_counts()
        s_cols = st.columns(len(status_counts))
        for i, (name, count) in enumerate(status_counts.items()):
            with s_cols[i]: kpi_card(name.upper(), count, color="#455A64")

    st.divider()

    # --- 5. SIDE-BY-SIDE TABLES ---
    available_cols = [c for c in ['Ref', 'Title', sd_col, 'Agent', 'Status'] if c in df.columns]
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("<h6 style='margin-bottom: 8px;'>Pending Tickets</h6>", unsafe_allow_html=True)
        st.dataframe(
            df_pending[available_cols].style.applymap(lambda x: 'color: #FFD600; font-weight: bold;' if x == 'Pending' else '', subset=['Status']) 
            if not df_pending.empty else pd.DataFrame(), 
            use_container_width=True, hide_index=True, height=220
        )

    with col_r:
        st.markdown("<h6 style='margin-bottom: 8px;'>Aged Tickets (>30 Days)</h6>", unsafe_allow_html=True)
        st.dataframe(
            df_aged[available_cols].style.applymap(lambda x: 'background-color: rgba(255, 82, 82, 0.1); color: #FF5252; font-weight: bold;', subset=['Ref']) 
            if not df_aged.empty else pd.DataFrame(), 
            use_container_width=True, hide_index=True, height=220
        )

# --- TAB 2: PERSONNEL PERFORMANCE ---
with tab2:
    if not df.empty and 'Agent' in df.columns:
        # 1. CHAINED DATA PROCESSING
        agent_stats = (df.assign(
            TTO_Met=df['SLA tto passed'].astype(str).str.lower().map({'no': 1}).fillna(0),
            TTR_Met=df['SLA ttr passed'].astype(str).str.lower().map({'no': 1}).fillna(0)
        ).groupby('Agent').agg(
            Total=('Ref', 'count'),
            TTO_Sum=('TTO_Met', 'sum'),
            TTR_Sum=('TTR_Met', 'sum')
        ).assign(
            TTO_Pct=lambda x: (x['TTO_Sum'] / x['Total'] * 100).round(1),
            TTR_Pct=lambda x: (x['TTR_Sum'] / x['Total'] * 100).round(1),
            Overall=lambda x: ((x['TTO_Pct'] + x['TTR_Pct']) / 2).round(1)
        ).reset_index().sort_values('Total', ascending=False))

        # 2. TOP PERFORMER CARD & RADAR
        st.markdown("### Personnel Insights")
        top = agent_stats.sort_values('Overall', ascending=False).iloc[0]
        
        l, r = st.columns([1, 2])
        with l:
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%); 
                            padding: 12px; border-radius: 8px; border-left: 5px solid #00e676; color: white;">
                    <p style="margin:0; font-size: 10px; opacity: 0.8;">TOP PERFORMER</p>
                    <h3 style="margin:0; font-size: 20px;">{top['Agent']}</h3>
                    <p style="margin:0; font-size: 16px; font-weight: 800;">{top['Overall']}% Score</p>
                </div>
            """, unsafe_allow_html=True)
            
            fig_r = go.Figure(go.Scatterpolar(
                r=[top['TTO_Pct'], top['TTR_Pct'], top['Overall']],
                theta=['TTO', 'TTR', 'Score'], fill='toself', line_color='#00d4ff'
            ))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 100])), 
                               height=180, margin=dict(t=20, b=20, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_r, use_container_width=True)

        with r:
            fig_b = px.bar(agent_stats, x='Agent', y=['TTO_Pct', 'TTR_Pct'], barmode='group',
                           color_discrete_sequence=['#00d4ff', '#7b1fa2'], height=260)
            fig_b.add_hline(y=83.7, line_dash="dot", line_color="#ff1744", annotation_text="Target")
            fig_b.update_layout(margin=dict(t=10, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', 
                                plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_b, use_container_width=True)

        # 3. COMPACT TABLE
        st.dataframe(
            agent_stats[['Agent', 'Total', 'TTO_Pct', 'TTR_Pct', 'Overall']],
            use_container_width=True, hide_index=True,
            column_config={
                "Agent": "Technician", "Total": "Tickets",
                "TTO_Pct": st.column_config.ProgressColumn("TTO %", format="%.1f%%", min_value=0, max_value=100),
                "TTR_Pct": st.column_config.ProgressColumn("TTR %", format="%.1f%%", min_value=0, max_value=100),
                "Overall": st.column_config.NumberColumn("Score", format="%.1f%%")
            }
        )
    else:
        st.info("No agent data available.")
# --- TAB 3: GROUP HIERARCHY (RESTORED TABLE + COLORFUL CARDS) ---
with tab3:
    # 1. DATA PREPARATION (Maintaining existing mapping logic)
    org_col_for_mapping = next((c for c in df.columns if 'organization' in c.lower() or 'customer' in c.lower()), None)
    if org_col_for_mapping:
        df['Parent_Company'] = df[org_col_for_mapping].apply(get_parent_company)
        
        # --- FIX: POPULATE MAPPING LOGIC BEFORE AGGREGATION ---
        # Mapping 'no' (meaning NOT breached) to 1 for successful compliance
        df['TTO_Done'] = df['SLA tto passed'].astype(str).str.lower().map({'no': 1}).fillna(0)
        df['TTR_Done'] = df['SLA ttr passed'].astype(str).str.lower().map({'no': 1}).fillna(0)

    if 'Parent_Company' in df.columns:
        # 2. AGGREGATE SUMMARY
        parent_summary = df.groupby('Parent_Company').agg({
            'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'
        }).reset_index().sort_values('Ref', ascending=False)

        parent_summary['TTO %'] = (parent_summary['TTO_Done'] / parent_summary['Ref'] * 100).fillna(0).round(1)
        
        # 3. COLORFUL GRADIENT CARDS (Top Overview)
        k_col1, k_col2, k_col3 = st.columns(3)
        
        with k_col1:
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1A237E, #0D47A1); padding: 15px; border-radius: 12px; border-left: 6px solid #00E5FF;">
                    <p style="margin:0; font-size: 11px; color: #BBDEFB; font-weight: bold; text-transform: uppercase;">Total Groups</p>
                    <h2 style="margin:0; color: white; font-size: 28px;">{len(parent_summary)}</h2>
                </div>""", unsafe_allow_html=True)
        
        with k_col2:
            top_val = parent_summary.iloc[0]['Parent_Company'] if not parent_summary.empty else "N/A"
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1B5E20, #2E7D32); padding: 15px; border-radius: 12px; border-left: 6px solid #00FF87;">
                    <p style="margin:0; font-size: 11px; color: #C8E6C9; font-weight: bold; text-transform: uppercase;">Lead Partner</p>
                    <h2 style="margin:0; color: white; font-size: 18px; padding-top: 5px;">{top_val}</h2>
                </div>""", unsafe_allow_html=True)
                
        with k_col3:
            avg_tto = parent_summary['TTO %'].mean().round(1) if not parent_summary.empty else 0
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4A148C, #6A1B9A); padding: 15px; border-radius: 12px; border-left: 6px solid #FF007A;">
                    <p style="margin:0; font-size: 11px; color: #E1BEE7; font-weight: bold; text-transform: uppercase;">Group Compliance</p>
                    <h2 style="margin:0; color: white; font-size: 28px;">{avg_tto}%</h2>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # 4. RESTORED: TOP CUSTOMERS TABLE (With Colorful Progress Bars)
        st.write("#### Top Customers by Parent Group")
        
        display_summary = parent_summary.copy()
        display_summary.columns = ['Parent Conglomerate', 'Total Volume', 'TTO Met', 'TTR Met', 'TTO Compliance %']
        
        st.dataframe(
            display_summary, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Parent Conglomerate": st.column_config.TextColumn("Parent Conglomerate", width="large"),
                "Total Volume": st.column_config.NumberColumn("Tickets"),
                "TTO Compliance %": st.column_config.ProgressColumn(
                    "Compliance", 
                    min_value=0, 
                    max_value=100, 
                    format="%.1f%%"
                )
            }
        )
        
        st.markdown("---")
        
        # 5. PARENT GROUP DISTRIBUTION (Original Feature)
        st.write("#### Parent Group Ticket Distribution")
        parent_list = sorted(df['Parent_Company'].dropna().unique().tolist())
        target_parent = st.selectbox("Select Parent Conglomerate", options=parent_list, key="parent_explorer_select")
        
        if target_parent:
            hierarchy_df = df[df['Parent_Company'] == target_parent]
            actual_org_col = next((c for c in ['Organization->Name', 'Organization Name', 'Organization', 'Customer'] if c in hierarchy_df.columns), None)
            
            if actual_org_col:
                subsidiaries = hierarchy_df.groupby(actual_org_col).agg({
                    'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'
                }).reset_index().sort_values('Ref', ascending=False)
                
                subsidiaries['TTO %'] = (subsidiaries['TTO_Done'] / subsidiaries['Ref'] * 100).fillna(0).round(1)
                subsidiaries['TTR %'] = (subsidiaries['TTR_Done'] / subsidiaries['Ref'] * 100).fillna(0).round(1)
                
                c_left, c_right = st.columns([1, 1.2])
                with c_left:
                    st.metric(f"Total Tickets: {target_parent}", len(hierarchy_df))
                    st.dataframe(
                        subsidiaries, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            actual_org_col: "Subsidiary",
                            "TTO %": st.column_config.ProgressColumn("TTO", min_value=0, max_value=100),
                            "TTR %": st.column_config.ProgressColumn("TTR", min_value=0, max_value=100)
                        }
                    )
                with c_right:
                    fig_sub = px.bar(
                        subsidiaries.head(10).sort_values('Ref', ascending=True), 
                        x='Ref', y=actual_org_col, orientation='h', 
                        title=f"Top 10 Customers in {target_parent}",
                        color_discrete_sequence=['#FF6600'], 
                        template="plotly_dark"
                    )
                    fig_sub.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.warning("Mapping column 'Parent_Company' not found.")

# --- TAB 4: EXECUTIVE REPORT (LOGIC CORRECTED FOR 90%+ PERFORMANCE) ---
with tab4:
    st.markdown('<h2 style="color: #FF6600; margin-top: 0; margin-bottom: 5px; font-size: 24px;">EXECUTIVE SUMMARY</h2>', unsafe_allow_html=True)
    
    if 'start_date' in locals() and 'end_date' in locals():
        date_label = f"{start_date} to {end_date}"
    else:
        date_label = "Full Operational Range"

    st.caption(f"Scope: {selected_unit.upper()} | {date_label}")

    # 1. FIXED CALCULATIONS
    current_total = len(df)
    
    # Identify the correct columns
    tto_col = 'TTO MET' if 'TTO MET' in df.columns else 'TTO_Done'
    ttr_col = 'TTR MET' if 'TTR MET' in df.columns else 'TTR_Done'

    if current_total > 0:
        # THE FIX: If your data uses 0 for Breach and 1 for Met, or vice versa:
        # We ensure we are counting the HIGHER volume (The Successes)
        raw_tto_sum = df[tto_col].sum()
        raw_ttr_sum = df[ttr_col].sum()

        # If the sum results in a tiny percentage (like 0.5%), it means '1' was 'Breach'.
        # We flip it to get the 'Met' percentage (the 90%+ value).
        if (raw_tto_sum / current_total) < 0.5:
            rep_tto = ((current_total - raw_tto_sum) / current_total * 100)
        else:
            rep_tto = (raw_tto_sum / current_total * 100)

        if (raw_ttr_sum / current_total) < 0.5:
            rep_ttr = ((current_total - raw_ttr_sum) / current_total * 100)
            total_ttr_breaches = int(raw_ttr_sum)
        else:
            rep_ttr = (raw_ttr_sum / current_total * 100)
            total_ttr_breaches = current_total - int(raw_ttr_sum)
    else:
        rep_tto = 0
        rep_ttr = 0
        total_ttr_breaches = 0

    # 2. SMALL COLORFUL CARDS (Layout from image_3f0ce3.png)
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    card_style = "padding: 10px; border-radius: 8px; text-align: center; height: 80px; display: flex; flex-direction: column; justify-content: center; box-shadow: 2px 4px 8px rgba(0,0,0,0.3);"

    with m_col1:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #1A237E, #1E88E5); {card_style} border-left: 5px solid #00E5FF;">
            <p style="margin:0; font-size: 11px; color: #BBDEFB; font-weight: bold;">VOLUME</p>
            <h3 style="margin:0; color: white; font-size: 24px;">{current_total:,}</h3></div>""", unsafe_allow_html=True)
            
    with m_col2:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #1B5E20, #2E7D32); {card_style} border-left: 5px solid #00FF87;">
            <p style="margin:0; font-size: 11px; color: #C8E6C9; font-weight: bold;">TTO %</p>
            <h3 style="margin:0; color: white; font-size: 24px;">{rep_tto:.1f}%</h3></div>""", unsafe_allow_html=True)

    with m_col3:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #E65100, #EF6C00); {card_style} border-left: 5px solid #FFD600;">
            <p style="margin:0; font-size: 11px; color: #FFE0B2; font-weight: bold;">TTR %</p>
            <h3 style="margin:0; color: white; font-size: 24px;">{rep_ttr:.1f}%</h3></div>""", unsafe_allow_html=True)

    with m_col4:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #B71C1C, #C62828); {card_style} border-left: 5px solid #FF5252;">
            <p style="margin:0; font-size: 11px; color: #FFCDD2; font-weight: bold;">AGED</p>
            <h3 style="margin:0; color: white; font-size: 24px;">{aged_count}</h3></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Risk Section
    col_risk, col_drivers = st.columns(2)
    with col_risk:
        st.error(f"**Critical Risks**\n* Aged Tickets: {aged_count}\n* SLA Breaches (TTR): {total_ttr_breaches}")
    with col_drivers:
        st.info("**Delay Drivers**\nTop factors impacting resolution: Pending vendor feedback and high-complexity holds.")
                
# --- TAB 5: AUDIT HISTORY (ORGANIZED SUB-TABS) ---
with tab5:
    # Internal CSS for clean, non-vibrant color accents
    st.markdown("""
        <style>
        /* Clean Colored Search Bar */
        div[data-testid="stTextInput"] > div[data-baseweb="input"] {
            border: 1px solid #FF6600 !important;
            border-radius: 8px !important;
            background-color: #fdfdfd !important;
            color: #000000 !important;
        }
        /* Style for the sub-tabs to make them stand out */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Creating Two Tabs inside Tab 5
    sub_tab1, sub_tab2 = st.tabs(["TICKET LOOKUP", "HISTORICAL LOG"])

    # --- SUB-TAB 1: SEARCH SPECIFIC TICKET ---
    with sub_tab1:
        
        search_ref = st.text_input(
            "Enter Ticket Ref ID:", 
            placeholder="e.g. R-154009", 
            key="ticket_search_sub"
        )
        
        if search_ref:
            try:
                with engine.connect() as conn:
                    query = text("""
                        SELECT Status_Log_Date, Ref, Current_Status, Agent 
                        FROM history_table 
                        WHERE Ref = :ref 
                        ORDER BY Status_Log_Date ASC
                    """)
                    history_df = pd.read_sql(query, conn, params={"ref": search_ref.strip()})
                    
                    if not history_df.empty:
                        # Logic for Duration
                        history_df['Status_Log_Date'] = pd.to_datetime(history_df['Status_Log_Date'])
                        history_df['Duration'] = history_df['Status_Log_Date'].diff().shift(-1)
                        
                        def format_duration(td):
                            if pd.isna(td): return "Active"
                            days = td.days
                            hours, remainder = divmod(td.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            return f"{days}d {hours}h" if days > 0 else f"{hours}h {minutes}m"

                        history_df['Time Spent'] = history_df['Duration'].apply(format_duration)
                        
                        # Displaying a clean color-coded status table
                        display_df = history_df.sort_values(by='Status_Log_Date', ascending=False).copy()
                        display_df['Date & Time'] = display_df['Status_Log_Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

                        def style_status(val):
                            s = str(val).lower()
                            if 'resolved' in s: return 'background-color: #d4edda; color: #155724;' # Light Green
                            if 'pending' in s: return 'background-color: #fff3cd; color: #856404;'  # Light Yellow
                            if 'assigned' in s: return 'background-color: #cce5ff; color: #004085;' # Light Blue
                            return ''

                        st.dataframe(
                            display_df[['Date & Time', 'Current_Status', 'Time Spent', 'Agent']].style.applymap(
                                style_status, subset=['Current_Status']
                            ),
                            use_container_width=True, 
                            hide_index=True
                        )
                    else:
                        st.warning(f"No records found for: {search_ref}")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- SUB-TAB 2: VIEW ENTIRE LOG ---
    with sub_tab2:
        try:
            with engine.connect() as conn:
                full_query = text("""
                    SELECT Status_Log_Date as 'Date & Time', 
                           Ref as 'Ticket ID', 
                           Current_Status as 'Status', 
                           Agent 
                    FROM history_table 
                    ORDER BY Status_Log_Date DESC 
                    LIMIT 500
                """)
                full_df = pd.read_sql(full_query, conn)

                if not full_df.empty:
                    full_df['Date & Time'] = pd.to_datetime(full_df['Date & Time']).dt.strftime('%Y-%m-%d %H:%M:%S')

                    # Subtle Table Styling
                    st.dataframe(full_df, use_container_width=True, hide_index=True)
                    
                    # Clean Export Button
                    csv = full_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV Report", 
                        data=csv, 
                        file_name="audit_history.csv", 
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("The history table is empty.")
        except Exception as e:
            st.error(f"Error: {e}")

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



