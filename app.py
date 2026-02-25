import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# --- 1. PAGE CONFIGURATION ---
# This MUST be the first Streamlit command
st.set_page_config(
    page_title="SITS Analytics Portal", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. DATABASE SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "sits_analytics.db")

# check_same_thread=False is essential for Streamlit's multi-threaded nature
engine = create_engine(
    f"sqlite:///{DB_FILE}", 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

# --- 3. SYSTEM INITIALIZATION ---
def initialize_system():
    """Initializes tables and creates the primary Super Admin account if missing."""
    with engine.begin() as conn:
        # Create User Authentication Table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """))
        
        # Check if the Super User exists; if not, create it
        admin_check = conn.execute(
            text("SELECT 1 FROM users WHERE username = 'admin'")
        ).fetchone()
        
        if not admin_check:
            conn.execute(text("""
                INSERT INTO users (username, password, role) 
                VALUES ('admin', 'Admin@CXP', 'super_admin')
            """))

# Run initialization immediately
initialize_system()

# --- 4. DATA & AUTH FUNCTIONS ---

def get_db_user(username, password):
    """Authenticates credentials against the SQLite database."""
    try:
        with engine.connect() as conn:
            query = text("SELECT role FROM users WHERE username = :u AND password = :p")
            result = conn.execute(query, {"u": username, "p": password}).fetchone()
            return result[0] if result else None
    except Exception as e:
        st.error(f"Authentication System Error: {e}")
        return None

def save_to_db(df):
    """Saves the processed analytics dataframe to the database."""
    if df is not None and not df.empty:
        try:
            # We use 'replace' to ensure the dashboard always shows the freshest sync
            df.to_sql("analytics_data", engine, if_exists="replace", index=False)
            return True
        except Exception as e:
            st.error(f"Database Save Error: {e}")
    return False

def load_from_db():
    """Retrieves the stored analytics data."""
    try:
        with engine.connect() as conn:
            return pd.read_sql(text("SELECT * FROM analytics_data"), conn)
    except:
        return pd.DataFrame()

def get_db_last_updated():
    """Returns the last modified time and record count for the status bar."""
    if not os.path.exists(DB_FILE):
        return "No local database found"
    
    timestamp = os.path.getmtime(DB_FILE)
    time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM analytics_data")).scalar()
            return f"Last Sync: {time_str} ({count} Records)"
    except:
        return f"Modified: {time_str} (Storage empty)"

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

        /* 3. SIDEBAR: Brand Identity (Dark Blue) */
        [data-testid="stSidebar"] {
            background-color: #1F3B4D !important;
        }

        /* Sidebar Text: Forced white for visibility */
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
        }

        /* Sidebar Inputs: HIGH CONTRAST FIX */
        /* Forces white background and dark text for all dropdowns, inputs, and date pickers in the sidebar */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="base-input"] > input,
        [data-testid="stSidebar"] div[data-baseweb="input"] > input,
        [data-testid="stSidebar"] .stMultiSelect div[role="listbox"],
        [data-testid="stSidebar"] div[data-testid="stFileUploadDropzone"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        
        /* Ensure input text specifically is visible and black */
        [data-testid="stSidebar"] input {
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
        }

        /* 4. NAVIGATION ICONS: Hamburger & Expander visibility */
        [data-testid="stHeader"] svg, 
        button[title="Collapse sidebar"] svg, 
        button[title="Expand sidebar"] svg {
            fill: #FF6600 !important;
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
    Uses 'Aggressive Keyword Detection' to catch typos (e.g., CLOTHIG) and branches.
    """
    if pd.isna(name): return "Unassigned"
    
    # Standardize to uppercase and strip whitespace for matching
    n = str(name).strip().upper()
    
    # 1. HELA CLOTHING (Catches typos like 'CLOTHIG' and all branches)
    if any(x in n for x in ["HELA", "INDIGLOW", "CLOTHIG"]): 
        return "Hela Clothing"

    # 2. CENTRAL FINANCE (Catches 'CF' prefixes, abbreviations, and full name)
    if any(x in n for x in ["CENTRAL FINANCE", "CF ", "CF-"]) or n == "CF":
        return "Central Finance"

    # 3. MAJOR BANKS (Collapses all branches into a single Bank entity)
    if "COMMERCIAL BANK" in n or "COMBANK" in n or "CBC " in n:
        return "Commercial Bank"
    if "SAMPATH" in n:
        return "Sampath Bank"
    if "HATTON NATIONAL" in n or "HNB" in n:
        return "Hatton National Bank"
    if "SEYLAN" in n:
        return "Seylan Bank"
    if "NATIONS TRUST" in n or " NTB" in n:
        return "Nations Trust Bank"
    if "PAN ASIA" in n:
        return "Pan Asia Bank"
    if "DFCC" in n:
        return "DFCC Bank"

    # 4. JOHN KEELLS GROUP (JKH)
    if any(x in n for x in ["JKH", "KELLS", "CINNAMON", "ELEPHANT HOUSE", "UNION ASSURANCE", "WALKERS TOURS"]): 
        return "John Keells Group"

    # 5. HAYLEYS GROUP
    if any(x in n for x in ["HAYLEYS", "ADVANTIS", "SINGER", "KINGSBURY", "DIPPED PRODUCTS", "ALUMEX", "FENTONS", "HAYCARB", "AMAYA"]): 
        return "Hayleys Group"

    # 6. LOLC / BROWNS GROUP
    if any(x in n for x in ["LOLC", "BROWNS", "EDEN RESORT", "DICKWEYA", "AGSTAR", "MATURATA"]): 
        return "LOLC / Browns Group"

    # 7. VALLIBEL ONE
    if any(x in n for x in ["LB FINANCE", "ROYAL CERAMICS", "ROCELL", "LANKA TILES", "LANKA WALLTILES", "SWISSTEK", "DELMEGE"]): 
        return "Vallibel One"

    # 8. CARGILLS GROUP
    if any(x in n for x in ["CARGILLS", "FOOD CITY", "KFC", "K.F.C", "KIST", "KOTMALE"]): 
        return "Cargills Group"

    # 9. GAMMA PIZZAKRAFT (Pizza Hut / Taco Bell Branches)
    if any(x in n for x in ["PIZZA HUT", "PIZZAHUT", "TACO BELL", "TACOBELL", "GAMMA PIZZA", "PIZZAKRAFT"]): 
        return "Gamma Pizzakraft"

    # 10. ABANS GROUP
    if any(x in n for x in ["ABANS", "COLOMBO CITY CENTRE", "CCC", "MINISO", "MCDONALDS"]): 
        return "Abans Group"

    # 11. SOFTLOGIC
    if any(x in n for x in ["SOFTLOGIC", "ASIRI", "GLOMARK", "ODEL", "SKECHERS", "BURGER KING"]): 
        return "Softlogic"

    # 12. HEMAS HOLDINGS
    if any(x in n for x in ["HEMAS", "ATLAS", "MORISON", "J.L. MORISON"]): 
        return "Hemas Holdings"

    # 13. APPAREL GIANTS
    if any(x in n for x in ["MAS HOLDINGS", "MAS ACTIVE", "MAS FABRICS", "BODYLINE", "SLIMLINE"]): 
        return "MAS Holdings"
    if "BRANDIX" in n or "FORTUDE" in n: 
        return "Brandix"

    # 14. INTERNAL
    if any(x in n for x in ["SITS", "SYNERGY", "SMART INFRASTRUCTURE"]): 
        return "SITS Internal"
        
    # Return original name if no keyword matches
    return str(name).strip()
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
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    
    tto_col = next((c for c in ['SLA tto passed', 'TTO passed'] if c in df.columns), None)
    ttr_col = next((c for c in ['SLA ttr passed', 'TTR passed'] if c in df.columns), None)
    a_col = next((c for c in ['Agent->Full name', 'Agent'] if c in df.columns), None)
    c_col = next((c for c in ['Organization->Name', 'Organization'] if c in df.columns), None)
    
    df['TTO_Done'] = df[tto_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if tto_col else 0
    df['TTR_Done'] = df[ttr_col].apply(lambda x: 1 if str(x).strip().lower() == 'no' else 0) if ttr_col else 0
    
    if 'Status' in df.columns:
        df['Is_Pending'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'pending' else 0)
        df['Is_Closed'] = df['Status'].apply(lambda x: 1 if str(x).strip().lower() == 'closed' else 0)
    
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
    
    if a_col:
        df['Mapped_Team'] = df[a_col].apply(get_team_from_technician)
    
    if c_col:
        df['Parent_Company'] = df[c_col].apply(get_parent_company)
    else:
        df['Parent_Company'] = "Unassigned"
    
    if 'Ref' not in df.columns: df['Ref'] = range(len(df))
    return df

import streamlit as st
import pandas as pd
import os
import base64
import requests
from io import BytesIO
from sqlalchemy import text

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
        
        if st.button("LOGIN", width="stretch"):
            role = get_db_user(input_user, input_pass)
            if role:
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.username = input_user
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

# --- 3. POST-AUTHENTICATION DATA LOADING ---
if st.session_state.data.empty:
    nav_left, nav_right = st.columns([8, 2])
    with nav_right:
        if st.button("⬅ LOGOUT / BACK", width="stretch"):
            logout()

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        last_update = get_db_last_updated()
        st.info(f"System Storage: {last_update}")
        
        if st.session_state.user_role in ['super_admin', 'admin']:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("RESTORE FROM DATABASE", width="stretch"):
                    db_df = load_from_db()
                    if not db_df.empty:
                        st.session_state.data = process_data_safely(db_df)
                        st.rerun()
                    else:
                        st.error("No database record found.")
            with c2:
                login_up = st.file_uploader("Upload New Data", type=['xlsx', 'csv'], label_visibility="collapsed")
                if login_up:
                    try:
                        df_up = pd.read_csv(login_up, encoding='latin1') if login_up.name.endswith('.csv') else pd.read_excel(login_up)
                        processed = process_data_safely(df_up)
                        save_to_db(processed)
                        st.session_state.data = processed
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload error: {e}")
            
            st.divider()
            if st.button("CONNECT TO LIVE WEB SYNC", width="stretch", type="primary"):
                try:
                    res = requests.get(
                        "https://cxp.sits.lk/webservices/export-v2.php?format=spreadsheet&query=15", 
                        auth=(st.secrets["api"]["user"], st.secrets["api"]["password"]), 
                        verify=False, 
                        timeout=30
                    )
                    if res.status_code == 200:
                        new_df = pd.read_excel(BytesIO(res.content), engine='openpyxl')
                        st.session_state.data = process_data_safely(new_df)
                        save_to_db(st.session_state.data)
                        st.rerun()
                    else:
                        st.error(f"Sync failed. Server responded with: {res.status_code}")
                except Exception as e:
                    st.error(f"Sync Error: {e}")
        else:
            if st.button("LOAD ANALYTICS VIEW", width="stretch"):
                db_df = load_from_db()
                if not db_df.empty:
                    st.session_state.data = process_data_safely(db_df)
                    st.rerun()
                else:
                    st.warning("No data available to load.")

    # --- 4. SUPER ADMIN CONTROL PANEL ---
    if st.session_state.user_role == "super_admin":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("👤 SUPER ADMIN: CONTROL PANEL", expanded=True):
            # Reduced to 3 tabs: System Settings removed
            t1, t2, t3 = st.tabs(["Register User", "Diagnostics", "User Directory"])
            
            with t1:
                st.subheader("Add New Account")
                nu, np = st.columns(2)
                new_u = nu.text_input("Username", key="new_user_reg")
                new_p = np.text_input("Password", type="password", key="new_pass_reg")
                new_r = st.selectbox("Role", ["viewer", "manager", "admin", "super_admin"], key="new_role_reg")
                if st.button("Create User Account", width="stretch"):
                    if new_u and new_p:
                        try:
                            with engine.begin() as conn:
                                conn.execute(
                                    text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"),
                                    {"u": new_u, "p": new_p, "r": new_r}
                                )
                            st.success(f"User {new_u} successfully created!")
                        except:
                            st.error("User creation failed. Username might already exist.")

            with t2:
                st.subheader("System Health")
                if st.button("Test SMTP & DB Connection", width="stretch"):
                    try:
                        with engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        st.write("✅ Database: Connected")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

            with t3:
                st.subheader("User Management")
                try:
                    users_df = pd.read_sql(text("SELECT username, role FROM users"), engine)
                    if not users_df.empty:
                        # Fix: Replaced width=None with use_container_width=True to fix the width error
                        st.dataframe(users_df, use_container_width=True, hide_index=True)
                        user_to_delete = st.selectbox("Select user to remove", options=users_df['username'].tolist())
                        if user_to_delete != "admin":
                            if st.button(f"DELETE USER: {user_to_delete}", type="primary", width="stretch"):
                                with engine.begin() as conn:
                                    conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": user_to_delete})
                                st.success(f"User '{user_to_delete}' removed.")
                                st.rerun()
                except Exception as e:
                    st.error(f"Error loading users: {e}")
            
            # Exit button placed at the bottom of the expander
            st.divider()
            if st.button("EXIT ADMIN SESSION", width="stretch", key="exit_admin_btn"):
                logout()

    st.stop()
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
    
    # Date Filter
    selected_dates = None
    # Using 'Date_Fixed' if created by your processing, otherwise falling back to 'Start date'
    d_col = 'Date_Fixed' if 'Date_Fixed' in df_base.columns else 'Start date'
    if d_col in df_base.columns:
        valid_dates = pd.to_datetime(df_base[d_col]).dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
            selected_dates = st.date_input("Select Range", value=(min_date, max_date))

    # Unit Filter
    units = ["All Departments", "SITS IT Support", "Gamma IT", "Service Desk"]
    selected_unit = st.selectbox("Operational Unit", units)
    
    # CUSTOMER FILTER (Using the Aggressive Mapping column)
    # This ensures "Hela Clothing - Naula" etc. do NOT appear here.
    all_parents_list = sorted(df_base['Parent_Company'].dropna().unique().tolist())
    all_parents_options = ["All Customers"] + all_parents_list
    selected_org = st.selectbox("Select Customer", all_parents_options)
    
    st.markdown("### EXCLUSIONS")
    # Using the same Parent_Company list for exclusions
    excluded_orgs = st.multiselect("Exclude Organizations", all_parents_list)
    
    # Agent Exclusions
    # Ensure a_col is defined correctly before this block (e.g., a_col = "Agent")
    all_agents = sorted(df_base[a_col].dropna().unique().tolist()) if a_col in df_base.columns else []
    excluded_agents = st.multiselect("Exclude Agents", all_agents)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("LOGOUT SESSION", use_container_width=True):
        st.session_state.data = pd.DataFrame()
        st.rerun()

## --- FILTERING ---
# We wrap everything in a check to ensure data exists and user is logged in
if not st.session_state.data.empty:
    df = df_base.copy()

    # 1. Customer Filter
    if selected_org != "All Customers":
        df = df[df['Parent_Company'] == selected_org]

    # 2. Status & Aged Logic
    one_month_ago = datetime.now() - timedelta(days=30)
    df_pending = pd.DataFrame()
    df_aged = pd.DataFrame()

    if 'Status' in df.columns:
        df_pending = df[df['Status'].astype(str).str.strip().str.lower() == 'pending']
        if 'Start date' in df.columns:
            # Ensure 'Start date' is datetime for comparison
            temp_start_date = pd.to_datetime(df_pending['Start date'], errors='coerce')
            df_aged = df_pending[temp_start_date < one_month_ago]

    backlog_val = len(df_pending)
    aged_count = len(df_aged)

    # 3. Date Range Filter
    if selected_dates and len(selected_dates) == 2:
        # Convert column to date for a fair comparison with the picker
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
        df = df[(df['Start date'].dt.date >= selected_dates[0]) & 
                (df['Start date'].dt.date <= selected_dates[1])]

    # 4. Unit Filter
    if selected_unit != "All Departments" and t_col in df.columns: 
        df = df[df[t_col] == selected_unit]

    # 5. Organization Exclusions
    if excluded_orgs:
        df = df[~df['Parent_Company'].isin(excluded_orgs)]

    # 6. Agent Exclusions
    if excluded_agents and a_col in df.columns:
        df = df[~df[a_col].isin(excluded_agents)]

else:
    # If no data is loaded, create empty variables so the rest of the app doesn't crash
    df = pd.DataFrame()
    backlog_val = 0
    aged_count = 0

# --- SLA CALCULATIONS ---
total_v = len(df)
tto_met_count = df['TTO_Done'].sum() if 'TTO_Done' in df.columns else 0
ttr_met_count = df['TTR_Done'].sum() if 'TTR_Done' in df.columns else 0
tto_breach_count = total_v - tto_met_count
ttr_breach_count = total_v - ttr_met_count

tto_perf_pct = (tto_met_count / total_v * 100) if total_v > 0 else 0
ttr_perf_pct = (ttr_met_count / total_v * 100) if total_v > 0 else 0
tto_breach_pct = 100 - tto_perf_pct if total_v > 0 else 0
ttr_breach_pct = 100 - ttr_perf_pct if total_v > 0 else 0

# --- MAIN INTERFACE ---
if aged_count > 0:
    st.markdown(f'<div class="critical-alert-box">⚠️ CRITICAL ALERT: {aged_count} Pending tickets have been open for more than 30 days!</div>', unsafe_allow_html=True)

st.markdown(f'<div class="header-box"><h2>CXP ANALYTICS: {selected_unit.upper()}</h2></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Main Dashboard", "Personnel Performance", "Group Hierarchy", "Executive Report"])

with tab1:
    st.markdown('<span class="section-header">Performance & Breach Overview</span>', unsafe_allow_html=True)
    
    st.markdown("#### TTO Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("TTO Perf %", f"{tto_perf_pct:.1f}%", color="#2E7D32" if tto_perf_pct >= 90 else "#FF6600")
    with c2: kpi_card("TTO Met", f"{tto_met_count}", color="#2E7D32")
    with c3: kpi_card("TTO Breach %", f"{tto_breach_pct:.1f}%", color="#D32F2F")
    with c4: kpi_card("TTO Breach", tto_breach_count, color="#D32F2F")

    st.markdown("#### TTR Metrics")
    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi_card("TTR Perf %", f"{ttr_perf_pct:.1f}%", color="#2E7D32" if ttr_perf_pct >= 90 else "#FF6600")
    with c6: kpi_card("TTR Met", f"{ttr_met_count}", color="#2E7D32")
    with c7: kpi_card("TTR Breach %", f"{ttr_breach_pct:.1f}%", color="#D32F2F")
    with c8: kpi_card("TTR Breach", ttr_breach_count, color="#D32F2F")

    st.write("### Overall Metrics")
    c9, c10, c11, _ = st.columns([1,1,1,1])
    with c9: kpi_card("Total Volume", total_v, color="#1F3B4D")
    with c10: kpi_card("Total Backlog", backlog_val, color="#D32F2F" if backlog_val > 0 else "#1F3B4D", flash=(backlog_val > 0))
    with c11: kpi_card("Aged (>30 Days)", aged_count, color="#7B1FA2")

    if 'Status' in df.columns:
        status_counts = df['Status'].value_counts()
        if not status_counts.empty:
            stat_cols = st.columns(len(status_counts))
            for i, (name, count) in enumerate(status_counts.items()):
                with stat_cols[i]:
                    s_color = "#2E7D32" if name.lower() == 'closed' else "#1976D2" if name.lower() == 'assigned' else "#FBC02D" if name.lower() == 'resolved' else "#FF6600"
                    kpi_card(name, count, color=s_color)

    st.markdown('<span class="section-header">Detailed Ticket Breakdown</span>', unsafe_allow_html=True)
    
    display_cols = ['Ref', 'Title', 'Start date', a_col, org_col]
    if pr_col:
        display_cols.append(pr_col)
    
    available_cols = [c for c in display_cols if c in df_base.columns]
    
    col_p, col_a = st.columns(2)
    with col_p:
        st.subheader("Pending Tickets")
        if not df_pending.empty:
            st.dataframe(df_pending[available_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No pending tickets found.")
            
    with col_a:
        st.subheader("Aged Tickets (>30 Days)")
        if not df_aged.empty:
            st.dataframe(df_aged[available_cols], use_container_width=True, hide_index=True)
        else:
            st.success("No aged tickets found.")

    if org_col in df.columns:
        st.markdown('<span class="section-header">Top 10 Customers by Ticket Volume</span>', unsafe_allow_html=True)
        top_cust = df.groupby(org_col)['Ref'].count().reset_index().sort_values('Ref', ascending=False).head(10)
        top_cust.columns = ['Customer Name', 'Ticket Count']
        c_chart, c_table = st.columns([1.5, 1])
        with c_chart:
            fig_cust = px.bar(top_cust, x='Ticket Count', y='Customer Name', orientation='h', color_discrete_sequence=['#FF6600'])
            fig_cust.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cust, use_container_width=True)
        with c_table:
            st.dataframe(top_cust, use_container_width=True, hide_index=True, height=300)

    if 'Start date' in df.columns and not df.empty:
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
            st.dataframe(monthly[['Month', 'Ref', 'TTO %', 'TTR %']], use_container_width=True, hide_index=True, height=280)

with tab2:
    # Ensure columns exist and clean up any potential whitespace issues
    df.columns = [str(c).strip() for c in df.columns]
    
    # Verify both columns are present to prevent the KeyError
    if a_col in df.columns and t_col in df.columns:
        # Group and aggregate
        perf_data = df.groupby([a_col, t_col]).agg({
            'Ref': 'count', 
            'TTO_Done': 'sum', 
            'TTR_Done': 'sum'
        }).reset_index()

        # Calculate Breach counts
        perf_data['TTO_Br'] = perf_data['Ref'] - perf_data['TTO_Done']
        perf_data['TTR_Br'] = perf_data['Ref'] - perf_data['TTR_Done']
        
        # Calculate Percentages (using fillna(0) to handle potential division by zero)
        perf_data['TTO_Pct'] = (perf_data['TTO_Done'] / perf_data['Ref'] * 100).round(1).fillna(0)
        perf_data['TTR_Pct'] = (perf_data['TTR_Done'] / perf_data['Ref'] * 100).round(1).fillna(0)
        perf_data['TTO_Br_Pct'] = (100 - perf_data['TTO_Pct']).round(1)
        perf_data['TTR_Br_Pct'] = (100 - perf_data['TTR_Pct']).round(1)

        # Map display column names
        perf_data.columns = [
            'Agent', 'Department', 'Total', 'TTO Met', 'TTR Met', 
            'TTO Breach', 'TTR Breach', 'TTO %', 'TTR %', 'TTO Br %', 'TTR Br %'
        ]

        depts = ["SITS IT Support", "Gamma IT", "Service Desk"]
        for dept in depts:
            # Filter and sort
            dept_df = perf_data[perf_data['Department'] == dept].sort_values('Total', ascending=False)
            
            if not dept_df.empty:
                st.markdown(f'<div class="section-header">{dept.upper()} PERSONNEL PERFORMANCE</div>', unsafe_allow_html=True)
                
                # Define the column display order
                cols_to_show = [
                    'Agent', 'Total', 'TTO Met', 'TTO Breach', 'TTO %', 
                    'TTO Br %', 'TTR Met', 'TTR Breach', 'TTR %', 'TTR Br %'
                ]
                
                st.dataframe(
                    dept_df[cols_to_show], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "TTO %": st.column_config.NumberColumn(format="%.1f%%"),
                        "TTO Br %": st.column_config.NumberColumn(format="%.1f%%"),
                        "TTR %": st.column_config.NumberColumn(format="%.1f%%"),
                        "TTR Br %": st.column_config.NumberColumn(format="%.1f%%")
                    }
                )
    else:
        st.error(f"Mapping Error: Column '{a_col}' or '{t_col}' not found in the uploaded file.")
with tab3:
    st.markdown('<span class="section-header">Conglomerate & Parent Group Explorer</span>', unsafe_allow_html=True)
    
    parent_summary = df_base.groupby('Parent_Company').agg({'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'}).reset_index().sort_values('Ref', ascending=False)
    parent_summary['TTO %'] = (parent_summary['TTO_Done'] / parent_summary['Ref'] * 100).round(1)
    parent_summary.columns = ['Parent Conglomerate', 'Total Volume', 'TTO Met', 'TTR Met', 'TTO Compliance %']
    
    st.write("#### Top Customers by Parent Group")
    st.dataframe(parent_summary, use_container_width=True, hide_index=True)
    st.markdown("---")
    
    st.write("#### Parent Group Ticket Distribution")
    parent_list = sorted(df_base['Parent_Company'].unique().tolist())
    target_parent = st.selectbox("Select Parent Conglomerate", parent_list)
    
    if target_parent and org_col in df_base.columns:
        hierarchy_df = df_base[df_base['Parent_Company'] == target_parent]
        subsidiaries = hierarchy_df.groupby(org_col).agg({'Ref': 'count', 'TTO_Done': 'sum', 'TTR_Done': 'sum'}).reset_index().sort_values('Ref', ascending=False)
        subsidiaries['TTO %'] = (subsidiaries['TTO_Done'] / subsidiaries['Ref'] * 100).round(1)
        subsidiaries['TTR %'] = (subsidiaries['TTR_Done'] / subsidiaries['Ref'] * 100).round(1)
        subsidiaries.columns = ['Subsidiary/Brand', 'Ticket Count', 'TTO Met', 'TTR Met', 'TTO Compliance %', 'TTR Compliance %']
        
        c_left, c_right = st.columns([1, 1.2])
        with c_left:
            st.metric(f"Total Tickets: {target_parent}", len(hierarchy_df))
            st.dataframe(subsidiaries, use_container_width=True, hide_index=True)
        with c_right:
            fig_sub = px.bar(subsidiaries.head(10), x='Ticket Count', y='Subsidiary/Brand', orientation='h', title=f"Top 10 Customers in {target_parent}", color_discrete_sequence=['#FF6600'])
            fig_sub.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_sub, use_container_width=True)

import streamlit as st
from fpdf import FPDF
from datetime import datetime

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
    pdf = SITS_Report()
    pdf.add_page()
    
    # Section I: Executive Overview
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(31, 59, 77)
    pdf.cell(0, 10, f'Executive Summary: {unit}', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(50, 50, 50)
    # Replaced special quotes/bullets with standard characters to prevent encoding errors
    intro_text = (f"This comprehensive operational audit covers the period: {dates}. "
                  f"The data reflects a total processing volume of {total_v:,} tickets. "
                  "This report is intended for board-level review to assess resource efficiency and SLA adherence.")
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
        pdf.cell(47, 10, row[0], 1)
        pdf.cell(47, 10, row[1], 1, 0, 'C')
        pdf.cell(47, 10, row[2], 1, 0, 'C')
        pdf.cell(47, 10, row[3], 1, 1, 'C')
    pdf.ln(10)

    # Section III: Risk Analysis
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(211, 47, 47)
    pdf.cell(0, 10, 'II. Critical Risk Assessment', 0, 1, 'L')
    
    pdf.set_fill_color(255, 245, 245)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    
    # Clean string encoding for reasons to avoid hidden characters
    clean_reasons = str(reasons).replace("'", "").replace("[", "").replace("]", "")
    risk_summary = (f"Analysis identifies {aged} aged tickets exceeding the 30-day threshold. "
                    f"Additionally, {breaches:,} total SLA breaches were recorded. "
                    f"Priority intervention is required for: {clean_reasons}")
    pdf.multi_cell(0, 7, risk_summary, 0, 'L', True)
    
    # Return as safe latin-1 bytes
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 2. STREAMLIT UI CODE ---
with tab4:
    st.markdown('<h2 style="color: #FF6600; margin-bottom: 0;">EXECUTIVE SUMMARY</h2>', unsafe_allow_html=True)
    st.caption(f"Operational Scope: {selected_unit}")

    # Calculate Data
    top_reasons_text = "No pending tickets."
    if not df_pending.empty and pr_col:
        top_reasons = df_pending[pr_col].value_counts().head(3).index.tolist()
        top_reasons_text = ", ".join(top_reasons)

    # KPI Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Volume", f"{total_v:,}")
    m2.metric("Backlog", backlog_val)
    m3.metric("TTO %", f"{tto_perf_pct:.1f}%")
    m4.metric("TTR %", f"{ttr_perf_pct:.1f}%")

    st.divider()

    # Cards Section
    c1, c2 = st.columns(2)
    with c1:
        st.error(f"**Critical Risks**\n- Aged Tickets: {aged_count}\n- SLA Breaches: {ttr_breach_count:,}")
    with c2:
        st.warning(f"**Top Delay Drivers**\n{top_reasons_text}")

    # PDF Download
    st.subheader("Board Meeting Assets")
    date_range = f"{selected_dates[0]} to {selected_dates[1]}" if selected_dates else "N/A"
    
    pdf_output = generate_board_pdf(
        total_v, backlog_val, tto_perf_pct, ttr_perf_pct, 
        aged_count, ttr_breach_count, selected_unit, 
        date_range, top_reasons_text
    )

    st.download_button(
        label="📄 DOWNLOAD BOARD-READY PDF BROCHURE",
        data=pdf_output,
        file_name=f"SITS_Executive_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
