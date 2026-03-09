import pandas as pd
import sqlite3
import os
import requests

# --- 1. DYNAMIC PATH & REMOTE CONFIGURATION ---
# Use absolute paths to ensure the script works correctly on cxp.navigo.lk
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'data.xlsx')
DB_FILE = os.path.join(BASE_DIR, 'sits_analytics.db')

# GitHub Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/SITS-SWNAVIGO/cxp_dashboard/cxp_dashboard_malki/data.xlsx"
GITHUB_TOKEN = None  # If private repo, replace with your Personal Access Token (PAT)

def get_operational_unit(agent_name, org_name):
    """
    Categorizes tickets into the 5 specific operational units.
    """
    agent = str(agent_name).strip()
    org = str(org_name).strip()

    # Agent-Specific Lists
    service_desk = [
        "Mariyadas Melisha", "Apeksha Nilupuli", "Sahan Dananjaya", 
        "Pathum Malshan", "Sasanka Madusith", "Ositha Buddika"
    ]
    gamma_it = [
        "Madhuka Gunaweera", "Vijay Philipkumar", "Chamal Dakshana", 
        "Jeevan Indrajith", "Preshan Silva", "Kavindu Basilu", 
        "Nimna Mendis", "Janindu Hewaalankarage", "Hasitha Munasinghe", 
        "Gamma IT Group", "Maduka Pramoditha", "Sameera Rukshan", "Hashan Madushanka"
    ]
    sits_support = [
        "L.V Sudesh Dilhan", "Nuwan Weerasekara", 
        "Mahela Ekanayaka", "Anushka Nayanatharu"
    ]

    # Mapping Logic Hierarchy
    if agent in service_desk:
        return "Service Desk"
    if agent in gamma_it or "Gamma" in org:
        return "Gamma IT"
    if agent in sits_support or "SITS IT" in org:
        return "SITS IT Support"
    if "Software" in org or "Dev" in org:
        return "Software Dept"
    if "Enterprise" in org:
        return "Enterprise Team"
    
    return "Other / Unassigned"

def download_latest_file():
    """Downloads the latest data.xlsx from GitHub."""
    print("Connecting to GitHub to fetch latest data.xlsx...")
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        response = requests.get(GITHUB_RAW_URL, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(EXCEL_FILE, 'wb') as f:
                f.write(response.content)
            print("Successfully downloaded latest data.xlsx.")
            return True
        else:
            print(f"GitHub Error: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"Network Error: {e}")
        return False

def find_column(df, keywords):
    for col in df.columns:
        if any(key.lower() in str(col).lower() for key in keywords):
            return col
    return None

def map_sla_performance(val):
    if pd.isna(val):
        return 'breached'
    clean_val = str(val).lower().strip()
    success_keywords = ['no', 'breach', 'out', 'failed']
    return 'met' if any(k in clean_val for k in success_keywords) else 'breached'

def process_data():
    # Fetch data first
    download_success = download_latest_file()
    
    if not os.path.exists(EXCEL_FILE):
        print(f"Error: {EXCEL_FILE} missing.")
        return

    try:
        # Load and find header
        df_raw = pd.read_excel(EXCEL_FILE, header=None)
        header_mask = df_raw.eq('Ref').any(axis=1)
        if not header_mask.any():
            raise ValueError("Could not find 'Ref' column.")
        
        header_idx = df_raw.index[header_mask].tolist()[0]
        df = pd.read_excel(EXCEL_FILE, skiprows=header_idx)
        df.columns = [str(col).strip() for col in df.columns]

        # Process SLA
        mapping_config = {
            'TTO': (['SLA tto p', 'SLA tto passed'], 'SLA tto passed', 'TTO_Done'),
            'TTR': (['SLA ttr pa', 'SLA ttr passed'], 'SLA ttr passed', 'TTR_Done')
        }

        for key, (keys, target_col, numeric_col) in mapping_config.items():
            found = find_column(df, keys)
            if found:
                df[target_col] = df[found].apply(map_sla_performance)
                df[numeric_col] = df[target_col].apply(lambda x: 1 if x == 'met' else 0)

        # Map Metadata & Units
        agent_col = find_column(df, ['Agent Name', 'Agent'])
        org_col = find_column(df, ['Organization', 'Team'])
        
        # Temporary columns for mapping
        temp_agent = df[agent_col].fillna('Unknown') if agent_col else 'Unknown'
        temp_org = df[org_col].fillna('N/A') if org_col else 'N/A'

        # Apply standardized operational units
        df['Agent'] = temp_agent
        df['Mapped_Team'] = df.apply(lambda x: get_operational_unit(temp_agent.loc[x.name], temp_org.loc[x.name]), axis=1)

        # Handle Dates
        date_col = find_column(df, ['Start date'])
        if date_col:
            df['Start date'] = pd.to_datetime(df[date_col], errors='coerce')

        # Database Persistence
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            df.to_sql('analytics_data', conn, if_exists='replace', index=False)
            try:
                os.chmod(DB_FILE, 0o664)
            except:
                pass

        print(f"--- CXP LIVE SYNC COMPLETE ---")
        print(f"Source: {'GitHub' if download_success else 'Local Cache'}")
        print(f"Units mapped: 5 Operational Units applied to {len(df)} rows.")

    except Exception as e:
        print(f"Critical Sync Error: {e}")

if __name__ == "__main__":
    process_data()
