import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import base64
from sqlalchemy import text
from fpdf import FPDF
import streamlit as st
import master_data_sync  
from datetime import datetime
import pandas as pd
import time
import os
import master_data_sync 
import sqlite3
from streamlit_autorefresh import st_autorefresh

# interval is in milliseconds (300,000 ms = 5 minutes)
count = st_autorefresh(interval=300000, key="fivedatarefresh")

# --- 1. CONFIGURATION (Direct MySQL Connection) ---
# We use the same credentials as your master_data_sync.py
DB_HOST = "staging_sits_analytics"
DB_USER = "sits"
DB_PASS = "123456"
DB_NAME = "sits_analytics"
DB_PORT = "3306"

# The connection string for MySQL
# Use "mysql+mysqlconnector" to ensure compatibility
CONNECTION_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="CXP Analytics", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 3. DATABASE ENGINE SETUP ---
# pool_pre_ping=True helps keep the connection alive on the Easypanel server
engine = create_engine(
    CONNECTION_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# --- 3. SYSTEM INITIALIZATION ---
def initialize_system():
    """Ensures the users table exists in the MySQL database."""
    try:
        with engine.begin() as conn:
            # Create User Table if missing (MySQL uses VARCHAR for lengths)
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
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")

# Run initialization immediately when app starts
initialize_system()

# --- 4. DATA & AUTH FUNCTIONS ---

def get_db_user(username, password):
    """Authenticates users against the live MySQL database."""
    try:
        with engine.connect() as conn:
            query = text("SELECT role FROM users WHERE username = :u AND password = :p")
            result = conn.execute(query, {"u": username, "p": password}).fetchone()
            return result[0] if result else None
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

def load_from_db():
    """Retrieves the live analytics data pushed by your local sync script."""
    try:
        with engine.connect() as conn:
            query = text("SELECT * FROM analytics_data")
            return pd.read_sql(query, conn)
    except Exception as e:
        st.warning("No data found in database. Please run the local sync script.")
        return pd.DataFrame()

def get_db_last_updated():
    """Displays the current status of the Easypanel database connection."""
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM analytics_data")).scalar()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return f"🟢 Live Connection | Records: {count:,} | Last Check: {now_str}"
    except Exception:
        return "🔴 Database Connection Offline"

# --- LOGO PATH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame()

# --- THEME ADAPTIVE STYLING ---
def apply_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        
        /* 1. ROOT VARIABLES: Theme switching logic */
        :root {
            --bg-card: #ffffff;
            --text-main: #1F3B4D;
            --text-sub: #666666;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-card: #1E1E1E;
                --text-main: #E0E0E0;
                --text-sub: #AAAAAA;
                --border-color: #333333;
            }
        }

        /* 2. MAIN LAYOUT: Adaptive background & core typography */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--background-color) !important;
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem !important;
        }

        .block-container { 
            padding-top: 3rem !important; 
            padding-bottom: 1rem !important; 
            max-width: 98% !important; 
        }

      /* ULTRA-COMPACT SIDEBAR WITH VISIBILITY FIX */
        [data-testid="stSidebar"] {
            background-image: linear-gradient(180deg, #102A43 0%, #061727 100%) !important;
        }

        /* Remove vertical bloat */
        [data-testid="stSidebar"] .stVerticalBlock { gap: 0rem !important; }
        [data-testid="stSidebar"] .block-container { padding: 0.5rem 0.8rem !important; }

        /* Shrink Logo and Pull Content Up */
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-bottom: -35px !important;
            transform: scale(0.8);
        }

        /* LABELS: Clear Visibility & No Overlap */
        [data-testid="stSidebar"] label {
            color: #F0F4F8 !important;
            margin-bottom: 2px !important; 
            margin-top: 8px !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            display: block !important;
            text-transform: uppercase;
        }

        /* INPUTS: Force Visible Dark Text on White Background */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="base-input"] > input,
        [data-testid="stSidebar"] div[data-baseweb="input"] > input {
            min-height: 30px !important;
            height: 30px !important;
            background-color: #FFFFFF !important;
            border-radius: 4px !important;
            padding-left: 10px !important;
            /* Force text color for visibility */
            color: #102A43 !important; 
            -webkit-text-fill-color: #102A43 !important;
        }

        /* Fix for visibility of selected options in dropdowns */
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            color: #102A43 !important;
        }

        /* FILE UPLOADER: Minimalist */
        [data-testid="stFileUploadDropzone"] { padding: 5px !important; }
        [data-testid="stFileUploadDropzone"] div div { display: none !important; }

        /* BUTTONS: Bold & Gradient */
        [data-testid="stSidebar"] div.stButton > button {
            min-height: 35px !important;
            margin-top: 10px !important;
            background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%) !important;
            font-weight: 700 !important;
            color: white !important;
            text-transform: uppercase;
        }

        /* 5. TABS & BUTTONS */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            color: var(--text-main) !important;
            font-weight: 600 !important;
            padding: 10px 20px !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #FF6600 !important;
            border-bottom: 3px solid #FF6600 !important;
        }

        div.stButton > button:not([data-baseweb="tab"]) {
            background-color: #FF6600 !important;
            color: white !important;
            border-radius: 6px !important;
            border: none !important;
            transition: 0.3s;
            width: 100%;
        }
        
        div.stButton > button:not([data-baseweb="tab"]):hover {
            background-color: #e65c00 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        /* 6. UI COMPONENTS: KPI Cards & Headers */
        .header-box {
            background: #FF6600; padding: 8px 16px; border-radius: 8px;
            margin-bottom: 12px; color: white !important;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header-box h2 { color: white !important; margin: 0; font-size: 1.1rem; font-weight: 700; }

        .kpi-wrapper {
            background-color: var(--bg-card); 
            padding: 10px 12px;
            border-radius: 8px; 
            margin-bottom: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid var(--border-color); 
            text-align: center;
        }
        .kpi-label { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; color: var(--text-sub); margin: 0; }
        .kpi-value { font-size: 1rem; font-weight: 800; margin: 0; }

        /* 7. ALERT BOX & ANIMATIONS */
        @keyframes critical-glow {
            0% { background-color: rgba(211, 47, 47, 0.15); border-color: rgba(211, 47, 47, 0.5); }
            50% { background-color: rgba(211, 47, 47, 0.35); border-color: rgba(211, 47, 47, 1); }
            100% { background-color: rgba(211, 47, 47, 0.15); border-color: rgba(211, 47, 47, 0.5); }
        }

        .critical-alert-box {
            animation: critical-glow 1.5s infinite;
            padding: 15px; 
            border-radius: 8px; 
            border: 2px solid #D32F2F;
            color: #D32F2F; 
            font-weight: 800; 
            text-align: center; 
            margin-bottom: 20px; 
            font-size: 1.1rem;
        }

        @keyframes pulse-red-border {
            0% { box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(211, 47, 47, 0); }
            100% { box-shadow: 0 0 0 0 rgba(211, 47, 47, 0); }
        }

        .flashing-kpi {
            animation: pulse-red-border 2s infinite;
            border: 2px solid #D32F2F !important;
        }

        footer { visibility: hidden; }
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

# --- CORPORATE MAPPING ---
def get_parent_company(name):
    """
    Collapses individual branches and subsidiaries into a single Parent Conglomerate.
    Uses 'Aggressive Keyword Detection' to catch typos and branches.
    """
    if pd.isna(name): 
        return "Unassigned"
    
    # Standardize to uppercase and strip whitespace for matching
    n = str(name).strip().upper()
    
    # Mapping Dictionary: Key is the Parent Company, Value is a list of keywords
    mappings = [
        ("Hela Clothing", ["HELA", "INDIGLOW", "CLOTHIG"]),
        ("Central Finance", ["CENTRAL FINANCE", "CF ", "CF-", "CF"]),
        ("Commercial Bank", ["COMMERCIAL BANK", "COMBANK", "CBC "]),
        ("Sampath Bank", ["SAMPATH"]),
        ("Hatton National Bank", ["HATTON NATIONAL", "HNB"]),
        ("Seylan Bank", ["SEYLAN"]),
        ("Nations Trust Bank", ["NATIONS TRUST", " NTB"]),
        ("Pan Asia Bank", ["PAN ASIA"]),
        ("DFCC Bank", ["DFCC"]),
        ("John Keells Group", ["JKH", "KELLS", "CINNAMON", "ELEPHANT HOUSE", "UNION ASSURANCE", "WALKERS TOURS"]),
        ("Hayleys Group", ["HAYLEYS", "ADVANTIS", "SINGER", "KINGSBURY", "DIPPED PRODUCTS", "ALUMEX", "FENTONS", "HAYCARB", "AMAYA"]),
        ("LOLC / Browns Group", ["LOLC", "BROWNS", "EDEN RESORT", "DICKWEYA", "AGSTAR", "MATURATA"]),
        ("Vallibel One", ["LB FINANCE", "ROYAL CERAMICS", "ROCELL", "LANKA TILES", "LANKA WALLTILES", "SWISSTEK", "DELMEGE"]),
        ("Cargills Group", ["CARGILLS", "FOOD CITY", "KFC", "K.F.C", "KIST", "KOTMALE"]),
        ("Gamma Pizzakraft", ["PIZZA HUT", "PIZZAHUT", "TACO BELL", "TACOBELL", "GAMMA PIZZA", "PIZZAKRAFT"]),
        ("Abans Group", ["ABANS", "COLOMBO CITY CENTRE", "CCC", "MINISO", "MCDONALDS"]),
        ("Softlogic", ["SOFTLOGIC", "ASIRI", "GLOMARK", "ODEL", "SKECHERS", "BURGER KING"]),
        ("Hemas Holdings", ["HEMAS", "ATLAS", "MORISON", "J.L. MORISON"]),
        ("MAS Holdings", ["MAS HOLDINGS", "MAS ACTIVE", "MAS FABRICS", "BODYLINE", "SLIMLINE"]),
        ("Brandix", ["BRANDIX", "FORTUDE"]),
        ("SITS Internal", ["SITS", "SYNERGY", "SMART INFRASTRUCTURE"]),
        ("IWS", [
            "SWEDISH CARS", "PURE CEYLON BEVARAGE", "IWS LOGISTICS", 
            "WINDCASTLE", "ART TV", "GERMANIA", "IWS HOLDINGS", 
            "IWS INVESTEMENTS", "IWS AUTOMOBILES", "DYNACOM ELECTRONICS", "EUROCARS"
        ])
    ]

    # Iterative keyword matching
    for parent, keywords in mappings:
        if any(kw in n for kw in keywords):
            return parent
            
    # Return original name if no keyword matches
    return str(name).strip()

# --- TECHNICIAN TEAM MAPPING ---
def get_team_from_technician(name):
    # Standardize input for better matching
    name = str(name).strip()
    
    sits_support = [
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
    
    # ADDED: Software Dept Members
    software_dept = [
        "Software Support", "Dev Team", "Application Support" 
        # Add specific software personnel names here
    ]
    
# ADDED: Enterprise Team Members
    enterprise_team = [
        "Enterprise Support", "Field Engineering", "Project Team", "N.V.P. Rathnayake"
    ]

    # Mapping Logic: Matches names to specific Operational Units
    if name in sits_support: return "SITS IT Support"
    if name in gamma_it: return "Gamma IT"
    if name in service_desk: return "Service Desk"
    if name in software_dept: return "Software Dept"
    if name in enterprise_team: return "Enterprise Team"
    
    # Returning Unassigned allows you to see names that aren't mapped yet
    return "Unassigned"

def process_data_safely(df):
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    
    # 1. Clean column headers
    df.columns = [str(c).strip() for c in df.columns]
    
    # 2. Dynamic Column Identification
    tto_col = next((c for c in ['SLA tto passed', 'TTO passed', 'SLA tto p'] if c in df.columns), None)
    ttr_col = next((c for c in ['SLA ttr passed', 'TTR passed', 'SLA ttr p'] if c in df.columns), None)
    a_col = next((c for c in ['Agent->Full name', 'Agent', 'Agent Name'] if c in df.columns), None)
    c_col = next((c for c in ['Organization->Name', 'Organization', 'Organization Name'] if c in df.columns), None)
    
    # 3. SLA Standardization (Checks for 'no', 'met', or 'within sla')
    def check_sla(val):
        v = str(val).strip().lower()
        return 1 if v in ['no', 'met', 'within sla', 'achieved', 'yes'] else 0

    df['TTO_Done'] = df[tto_col].apply(check_sla) if tto_col else 0
    df['TTR_Done'] = df[ttr_col].apply(check_sla) if ttr_col else 0
    
    # 4. Date & Status Handling
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
        
    if 'Status' in df.columns:
        df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
        df['Is_Pending'] = (df['Status_Clean'] == 'pending').astype(int)
        df['Is_Closed'] = (df['Status_Clean'] == 'closed').astype(int)
    
    # 5. Mapped Team Logic (The Fix for Operational Units)
    if a_col:
        # Assign the team based on the technician name
        df['Mapped_Team'] = df[a_col].apply(get_team_from_technician)
    else:
        df['Mapped_Team'] = "Unassigned"
        
    # 6. Company Mapping
    if c_col:
        df['Parent_Company'] = df[c_col].apply(get_parent_company)
    else:
        df['Parent_Company'] = "Internal"
    
    # 7. Final Cleanup: Ensure no NaN values in filtering columns
    df['Mapped_Team'] = df['Mapped_Team'].fillna('Unassigned')
    df['Parent_Company'] = df['Parent_Company'].fillna('Internal')
    
    if 'Ref' not in df.columns: 
        df['Ref'] = range(len(df))
        
    return df

# --- 1. INITIALIZATION ---
def initialize_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "data" not in st.session_state:
        st.session_state.data = pd.DataFrame()

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
import pandas as pd
import os
import base64
from io import BytesIO
import requests
from sqlalchemy import text

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

# Using a small, styled header instead of st.title
st.markdown(f"""
    <div style='padding: 10px; border-radius: 5px; background-color: #f0f2f6; margin-bottom: 20px;'>
        <p style='margin: 0; font-size: 0.9rem; color: #666; font-weight: bold;'>
            CXP DASHBOARD: <span style='color: #FF6600;'>{st.session_state.username}</span>
        </p>
    </div>
""", unsafe_allow_html=True)

# Your analytics charts and tables go here...

# --- DATA PREP ---
df_base = st.session_state.data.copy()
org_col = next((c for c in ['Organization->Name', 'Organization'] if c in df_base.columns), "Organization")
a_col = next((c for c in ['Agent->Full name', 'Agent'] if c in df_base.columns), "Agent")
pr_col = next((c for c in ['Pending reason', 'Reason', 'Pending Reason'] if c in df_base.columns), None)
t_col = 'Mapped_Team'

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_PATH): 
        st.image(LOGO_PATH, width=180)
        
    st.markdown("### DATA MANAGEMENT")
    new_data = st.file_uploader("Update SQL Database", type=['xlsx', 'csv'])
    if new_data:
        df_new = pd.read_csv(new_data, encoding='latin1') if new_data.name.endswith('.csv') else pd.read_excel(new_data)
        processed_new = process_data_safely(df_new) 
        save_to_db(processed_new)
        st.session_state.data = processed_new
        st.rerun()
    
    st.markdown("---")
    st.markdown("### FILTERS")

    # 1. Date Filter Logic - Restoring the From/To Selectors
    # Dynamically find date column to prevent KeyErrors
    d_col = next((c for c in df_base.columns if 'start' in c.lower() or 'fixed' in c.lower()), None)
    selected_dates = []

    if d_col:
        valid_dates = pd.to_datetime(df_base[d_col], errors='coerce').dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
            
            # SIDE-BY-SIDE DATE PICKERS
            col_f, col_t = st.columns(2)
            with col_f:
                date_from = st.date_input("From Date", value=min_date, min_value=min_date, max_value=max_date, key="sidebar_from")
            with col_t:
                date_to = st.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date, key="sidebar_to")
            
            selected_dates = [date_from, date_to]

    # 2. Operational Unit (Hard-cleaning "Unassigned" out of the UI)
    if 'Mapped_Team' in df_base.columns:
        # Get unique teams and remove any variants of Unassigned/NaN
        raw_teams = df_base['Mapped_Team'].unique().tolist()
        available_teams = [
            t for t in raw_teams 
            if str(t).strip().lower() not in ['unassigned', 'nan', 'none', '']
        ]
        unit_options = ["All Departments"] + sorted(available_teams)
    else:
        unit_options = ["All Departments", "Software Dept", "Enterprise Team", "Service Desk"]
    
    selected_unit = st.selectbox("Operational Unit", unit_options)
    
    # 3. Customer Filter
    all_parents_list = sorted(df_base['Parent_Company'].dropna().unique().tolist())
    all_parents_options = ["All Customers"] + all_parents_list
    selected_org = st.selectbox("Select Customer", all_parents_options)
    
    st.markdown("### EXCLUSIONS")
    excluded_orgs = st.multiselect("Exclude Organizations", all_parents_list)
    
    # 4. Agent Exclusions
    all_agents = sorted(df_base[a_col].dropna().unique().tolist()) if a_col in df_base.columns else []
    excluded_agents = st.multiselect("Exclude Agents", all_agents)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("LOGOUT SESSION", use_container_width=True):
        st.session_state.data = pd.DataFrame()
        st.rerun()

# --- 5. DASHBOARD FILTERING LOGIC ---

# 1. INITIALIZE VARIABLES (Crucial to prevent NameErrors)
df = pd.DataFrame()
df_pending = pd.DataFrame()
df_aged = pd.DataFrame()
backlog_val = 0
aged_count = 0

# Ensure selected_dates exists even if the sidebar logic was skipped
if 'selected_dates' not in locals():
    selected_dates = None

if not st.session_state.data.empty:
    df = st.session_state.data.copy()

    # 2. DATE RANGE FILTER
    # Only filter if selected_dates was successfully created in the sidebar
    if selected_dates and len(selected_dates) == 2:
        try:
            # Ensure 'Start date' is datetime objects
            df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
            
            # Filter using .date() to match the date_input format
            df = df[(df['Start date'].dt.date >= selected_dates[0]) & 
                    (df['Start date'].dt.date <= selected_dates[1])]
        except Exception as e:
            st.error(f"Date Filter Error: {e}")

    # 3. CUSTOMER FILTER
    if 'selected_org' in locals() and selected_org != "All Customers":
        df = df[df['Parent_Company'] == selected_org]

    # 4. UNIT FILTER
    if 'selected_unit' in locals() and selected_unit != "All Departments": 
        team_col = 'Mapped_Team'
        if team_col in df.columns:
            df = df[df[team_col] == selected_unit]

    # 5. EXCLUSIONS
    if 'excluded_orgs' in locals() and excluded_orgs:
        df = df[~df['Parent_Company'].isin(excluded_orgs)]

    if 'excluded_agents' in locals() and excluded_agents and a_col in df.columns:
        df = df[~df[a_col].isin(excluded_agents)]

    # 6. STATUS & AGED LOGIC
    # Using a fixed reference for "now" to keep calculations consistent
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)

    if 'Status' in df.columns:
        # Clean status for reliable filtering
        status_clean = df['Status'].astype(str).str.strip().str.lower()
        df_pending = df[status_clean == 'pending'].copy()
        
        # --- 6. STATUS & AGED LOGIC ---
now = datetime.now()
one_month_ago = now - timedelta(days=30)

# 1. Dynamically find the Start Date column to avoid KeyError
# We look for common variations of the name
date_col = next((c for c in df.columns if 'start' in c.lower() and 'date' in c.lower()), None)

if 'Status' in df.columns and date_col:
    # Normalize status for filtering
    status_clean = df['Status'].astype(str).str.strip().str.lower()
    df_pending = df[status_clean == 'pending'].copy()
    
    df_aged = pd.DataFrame()

    if not df_pending.empty:
        # Use the dynamically found date_col instead of hardcoded 'Start date'
        df_pending[date_col] = pd.to_datetime(df_pending[date_col], errors='coerce')
        
        # Ensure comparison is possible by removing timezones (tz-naive)
        temp_dates = df_pending[date_col].dt.tz_localize(None)
        df_aged = df_pending[temp_dates < one_month_ago]

    backlog_val = len(df_pending)
    aged_count = len(df_aged)
else:
    # Fallback if columns are missing
    backlog_val = 0
    aged_count = 0
    if not date_col:
        st.warning("Could not find a 'Start Date' column in the data.")

# --- SLA CALCULATIONS ---
total_v = len(df)

# Use the columns created by master_data_sync.py to show real-time breaches
tto_met_count = int(df['TTO MET'].sum()) if 'TTO MET' in df.columns else 0
ttr_met_count = int(df['TTR MET'].sum()) if 'TTR MET' in df.columns else 0

# Breaches are the remaining tickets from the total volume
tto_breach_count = total_v - tto_met_count
ttr_breach_count = total_v - ttr_met_count

# Calculate real-time percentages
tto_perf_pct = (tto_met_count / total_v * 100) if total_v > 0 else 0
ttr_perf_pct = (ttr_met_count / total_v * 100) if total_v > 0 else 0
tto_breach_pct = 100 - tto_perf_pct if total_v > 0 else 0
ttr_breach_pct = 100 - ttr_perf_pct if total_v > 0 else 0

# --- MAIN INTERFACE ---
if aged_count > 0:
    st.markdown(f'<div class="critical-alert-box">⚠️ CRITICAL ALERT: {aged_count} Pending tickets have been open for more than 30 days!</div>', unsafe_allow_html=True)

st.markdown(f'<div class="header-box"><h2>CXP ANALYTICS: {selected_unit.upper()}</h2></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Main Dashboard", "Personnel Performance", "Group Hierarchy", "Executive Report", "Audit History"])

# --- TAB 1: MAIN DASHBOARD ---
with tab1:
    st.markdown('<span class="section-header">Performance & Breach Overview</span>', unsafe_allow_html=True)
    
    # 1. TTO & TTR Metrics Rows
    st.markdown("#### TTO Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("TTO PERF %", f"{tto_perf_pct:.1f}%", color="#2E7D32" if tto_perf_pct >= 90 else "#FF6600")
    with c2: kpi_card("TTO MET", f"{tto_met_count}", color="#2E7D32")
    with c3: kpi_card("TTO BREACH %", f"{tto_breach_pct:.1f}%", color="#D32F2F")
    with c4: kpi_card("TTO BREACH", tto_breach_count, color="#D32F2F")

    st.markdown("#### TTR Metrics")
    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi_card("TTR PERF %", f"{ttr_perf_pct:.1f}%", color="#2E7D32" if ttr_perf_pct >= 90 else "#FF6600")
    with c6: kpi_card("TTR MET", f"{ttr_met_count}", color="#2E7D32")
    with c7: kpi_card("TTR BREACH %", f"{ttr_breach_pct:.1f}%", color="#D32F2F")
    with c8: kpi_card("TTR BREACH", ttr_breach_count, color="#D32F2F")

    # 2. Overall Metrics Row
    st.write("### Overall Metrics")
    c9, c10, c11 = st.columns(3)
    with c9: kpi_card("TOTAL VOLUME", total_v, color="#1F3B4D")
    with c10: kpi_card("TOTAL BACKLOG", backlog_val, color="#D32F2F" if backlog_val > 0 else "#1F3B4D", flash=(backlog_val > 0))
    with c11: kpi_card("AGED (>30 DAYS)", aged_count, color="#7B1FA2")

    # Dynamic Status Row (PENDING, ASSIGNED, etc.)
    if 'Status' in df.columns:
        status_counts = df['Status'].value_counts()
        stat_cols = st.columns(len(status_counts))
        for i, (name, count) in enumerate(status_counts.items()):
            with stat_cols[i]:
                kpi_card(name.upper(), count, color="#FF6600")

    # --- SAFETY CHECK FOR COLUMN NAMES ---
    # This finds 'Start date' even if it is named 'Start Date ' or 'start_date'
    sd_col = next((c for c in df.columns if 'start' in c.lower() and 'date' in c.lower()), None)
    org_col_name = next((c for c in df.columns if 'organization' in c.lower()), 'Organization Name')

    # 3. Detailed Ticket Breakdown
    st.markdown('<span class="section-header">Detailed Ticket Breakdown</span>', unsafe_allow_html=True)
    
    available_cols = [c for c in ['Ref', 'Title', sd_col, 'Agent', org_col_name, 'Pending reason'] if c and c in df.columns]
    
    col_p, col_a = st.columns(2)
    with col_p:
        st.subheader("Pending Tickets")
        if not df_pending.empty and sd_col:
            temp_p = df_pending.copy()
            # Force conversion to datetime and then format as string with Time
            temp_p[sd_col] = pd.to_datetime(temp_p[sd_col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(temp_p[available_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No pending tickets or missing date column.")
            
    with col_a:
        st.subheader("Aged Tickets (>30 Days)")
        if not df_aged.empty and sd_col:
            temp_a = df_aged.copy()
            temp_a[sd_col] = pd.to_datetime(temp_a[sd_col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(temp_a[available_cols], use_container_width=True, hide_index=True)
        else:
            st.success("No aged tickets found.")

    # 4. Top 10 Customers Chart & Table
    st.markdown('<span class="section-header">Top 10 Customers by Ticket Volume</span>', unsafe_allow_html=True)
    if org_col_name in df.columns:
        top_cust = df.groupby(org_col_name)['Ref'].count().reset_index().sort_values('Ref', ascending=False).head(10)
        top_cust.columns = ['Customer Name', 'Ticket Count']
        
        c_chart, c_table = st.columns([2, 1])
        with c_chart:
            fig_cust = px.bar(top_cust, x='Ticket Count', y='Customer Name', orientation='h', color_discrete_sequence=['#FF6600'])
            fig_cust.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cust, use_container_width=True)
        with c_table:
            st.dataframe(top_cust, use_container_width=True, hide_index=True, height=400)

    # 5. Monthly SLA Analysis Chart & Performance Table
    st.markdown('<span class="section-header">Monthly SLA Analysis</span>', unsafe_allow_html=True)
    if sd_col:
        df['Month'] = pd.to_datetime(df[sd_col], errors='coerce').dt.strftime('%Y-%m')
        monthly = df.groupby('Month').agg({'Ref':'count','TTO_Done':'sum','TTR_Done':'sum'}).reset_index()
        monthly['TTO %'] = (monthly['TTO_Done'] / monthly['Ref'] * 100).round(1)
        monthly['TTR %'] = (monthly['TTR_Done'] / monthly['Ref'] * 100).round(1)
        
        cl, cr = st.columns([2, 1])
        with cl:
            fig_sla = px.bar(monthly, x='Month', y=['TTO %', 'TTR %'], barmode='group', color_discrete_map={'TTO %': '#FF6600', 'TTR %': '#1F3B4D'})
            fig_sla.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1, x=1))
            st.plotly_chart(fig_sla, use_container_width=True)
        with cr:
            st.markdown("#### Monthly Performance Summary")
            st.dataframe(monthly[['Month', 'Ref', 'TTO %', 'TTR %']], use_container_width=True, hide_index=True, height=350)

# --- 4. DASHBOARD CONTENT WRAPPER ---
def render_dashboard_content(df):
    """
    Wrap all your metrics, tabs, and charts in this function.
    This is what the fragment will refresh every 30 seconds.
    """
    # 1. KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tickets", len(df))

with tab2:
    
    if not df.empty and 'Agent' in df.columns:
        # A. Aggregate Data by Agent
        agent_stats = df.groupby('Agent').agg(
            Total_Tickets=('Agent', 'count'),
            TTO_Met=('TTO_Done', 'sum'),
            TTR_Met=('TTR_Done', 'sum')
        ).reset_index()

        # B. Calculate Percentages
        agent_stats['TTO %'] = (agent_stats['TTO_Met'] / agent_stats['Total_Tickets'] * 100).round(1)
        agent_stats['TTR %'] = (agent_stats['TTR_Met'] / agent_stats['Total_Tickets'] * 100).round(1)
        
        # Sort by total volume for the first view
        agent_stats = agent_stats.sort_values(by='Total_Tickets', ascending=False)

        # C. Visualization - Bar Chart
        fig_agent = px.bar(
            agent_stats, 
            x='Agent', 
            y=['TTO %', 'TTR %'],
            barmode='group',
            title="SLA Achievement by Technician",
            color_discrete_map={'TTO %': '#FF6600', 'TTR %': '#1F3B4D'},
            labels={'value': 'Percentage (%)', 'variable': 'Metric'}
        )
        # Add a target line for your 83.7% goal
        fig_agent.add_hline(y=83.7, line_dash="dot", line_color="red", annotation_text="Target 83.7%")
        
        st.plotly_chart(fig_agent, use_container_width=True)

        # D. Summary Table
        st.markdown("### Individual Performance Breakdown")
        st.dataframe(
            agent_stats[['Agent', 'Total_Tickets', 'TTO %', 'TTR %']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TTO %": st.column_config.ProgressColumn("TTO Performance", min_value=0, max_value=100, format="%.1f%%"),
                "TTR %": st.column_config.ProgressColumn("TTR Performance", min_value=0, max_value=100, format="%.1f%%")
            }
        )
    else:
        st.warning("No Personnel data found. Please ensure 'Agent' exists in your data source.")
# --- TAB 3: GROUP HIERARCHY ---
    with tab3:
        st.markdown('<div class="section-header" style="color:#FF6600; font-size:1.5rem; font-weight:bold; margin-bottom:20px;">Conglomerate & Parent Group Explorer</div>', unsafe_allow_html=True)
        
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
    
    # 1. Safe Date Label (Prevents TypeError: 'NoneType' object is not subscriptable)
    if 'selected_dates' in locals() and isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
        date_label = f"{selected_dates[0]} to {selected_dates[1]}"
    else:
        date_label = "Full Operational Range"

    st.caption(f"Operational Scope: {selected_unit} | Period: {date_label}")

    # 2. Performance Metrics Calculation
    # Uses column names established in your master_data_sync script
    current_total = len(df) if 'df' in locals() else 0
    
    # Dynamic column mapping to match your MySQL 'analytics_data' table
    tto_col = 'TTO MET' if 'TTO MET' in df.columns else 'TTO_Done'
    ttr_col = 'TTR MET' if 'TTR MET' in df.columns else 'TTR_Done'

    rep_tto = (df[tto_col].sum() / current_total * 100) if current_total > 0 and tto_col in df.columns else 0
    rep_ttr = (df[ttr_col].sum() / current_total * 100) if current_total > 0 and ttr_col in df.columns else 0

    # Display Top Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Selected Volume", f"{current_total:,}")
    m2.metric("TTO Compliance", f"{rep_tto:.1f}%")
    m3.metric("TTR Compliance", f"{rep_ttr:.1f}%")
    m4.metric("Aged Backlog", aged_count if 'aged_count' in locals() else 0)

    st.divider()

    # 3. Risk Analysis Section
    col_risk, col_drivers = st.columns(2)
    
    with col_risk:
        st.error(f"### Critical Risks\n* **Aged Tickets:** {aged_count if 'aged_count' in locals() else 0}\n* **SLA Breaches:** {current_total - df[ttr_col].sum() if ttr_col in df.columns else 0}")
    
    with col_drivers:
        st.info("### Delay Drivers\nTop factors currently impacting resolution times include pending vendor feedback and high-complexity service holds.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Board Assets (PDF Generation)
    st.subheader("Board Meeting Assets")
    if st.button("PREPARE PDF REPORT", use_container_width=True):
        # Calculation for breach count to pass into PDF
        ttr_breach_count = (current_total - df[ttr_col].sum()) if ttr_col in df.columns else 0
        
        pdf_bytes = generate_board_pdf(
            current_total, 
            0, 
            rep_tto, 
            rep_ttr, 
            aged_count if 'aged_count' in locals() else 0, 
            ttr_breach_count, 
            selected_unit, 
            date_label, 
            "General Analysis"
        )
        st.download_button(
            label="📄 DOWNLOAD BOARD-READY PDF BROCHURE",
            data=pdf_bytes,
            file_name=f"Executive_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- TAB 5: AUDIT HISTORY ---
with tab5:
    st.markdown('<span class="section-header">Full Ticket Status Audit Trail</span>', unsafe_allow_html=True)
    
    view_mode = st.radio("Select View Mode:", ["Search Specific Ticket", "View Entire Historical Log"], horizontal=True, key="audit_view_radio")

    try:
        # Use the SQLAlchemy engine instead of sqlite3.connect(DB_FILE)
        with engine.connect() as conn:
            if view_mode == "Search Specific Ticket":
                search_ref = st.text_input("Enter Ticket Ref ID:", placeholder="e.g. R-154009", key="ticket_search_input")
                
                if search_ref:
                    # Using text() for MySQL compatibility and security
                    query = text("SELECT Status_Log_Date, Ref, Current_Status, Agent FROM history_table WHERE Ref = :ref ORDER BY Status_Log_Date ASC")
                    history_df = pd.read_sql(query, conn, params={"ref": search_ref.strip()})
                    
                    if not history_df.empty:
                        # 1. Calculate Duration Logic
                        history_df['Status_Log_Date'] = pd.to_datetime(history_df['Status_Log_Date'])
                        history_df['Duration'] = history_df['Status_Log_Date'].diff().shift(-1)
                        
                        def format_duration(td):
                            if pd.isna(td): return "Active Now"
                            days = td.days
                            hours, remainder = divmod(td.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            return f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

                        history_df['Time Spent'] = history_df['Duration'].apply(format_duration)
                        
                        # Prepare for display
                        display_df = history_df.sort_values(by='Status_Log_Date', ascending=False).copy()
                        display_df.rename(columns={'Status_Log_Date': 'Date & Time', 'Current_Status': 'Status', 'Ref': 'Ticket ID'}, inplace=True)
                        display_df['Date & Time'] = display_df['Date & Time'].dt.strftime('%Y-%m-%d %H:%M:%S')

                        # 2. High-Contrast Styling
                        def apply_hc_style(val):
                            s = str(val).strip().lower()
                            if 'resolved' in s: return 'background-color: #28a745; color: white; font-weight: bold;'
                            if 'pending' in s: return 'background-color: #ffc107; color: black; font-weight: bold;'
                            if 'assigned' in s: return 'background-color: #007bff; color: white; font-weight: bold;'
                            if 'escalated' in s: return 'background-color: #dc3545; color: white; font-weight: bold;'
                            return ''

                        st.dataframe(
                            display_df[['Date & Time', 'Status', 'Time Spent', 'Agent']].style.applymap(apply_hc_style, subset=['Status']),
                            use_container_width=True, 
                            hide_index=True
                        )
                    else:
                        st.warning(f"No records found for Ticket ID: {search_ref}")

            else:
                # Full Log View (Limited to 1000 for performance)
                full_query = text("SELECT Status_Log_Date as 'Date & Time', Ref as 'Ticket ID', Current_Status as 'Status', Agent FROM history_table ORDER BY Status_Log_Date DESC LIMIT 1000")
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
                    
                    csv = full_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Export Audit Trail (CSV)", csv, "audit_trail.csv", "text/csv")
                else:
                    st.info("The history table is currently empty.")

    except Exception as e:
        st.error(f"MySQL Audit Error: {str(e)}")

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
        
        # IMPORTANT: You must call your dashboard UI inside here
        render_dashboard_content(st.session_state.data)
    else:
        st.warning("Database currently empty. Please click 'Refresh & Wipe'.")

# --- 5. MAIN APP EXECUTION ---
if not st.session_state.data.empty:
    # This calls the auto-sync loop
    sync_dashboard_ui()
else:
    st.info("No data available. Click 'REFRESH & WIPE DB' to import data from Excel.")
