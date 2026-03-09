import pandas as pd
import sqlite3
import os
import sys

# --- 1. CONFIGURATION & PATHS ---
# This ensures the script always finds files in its own folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'data.xlsx') 
DB_FILE = os.path.join(BASE_DIR, 'sits_analytics.db')

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

def find_column(df, keywords):
    """Helper to find column names regardless of exact spelling/casing."""
    for col in df.columns:
        if any(key.lower() in str(col).lower() for key in keywords):
            return col
    return None

def map_sla_performance(val):
    """
    Logic: If the column contains 'no', 'breach', 'out', or 'failed', 
    it means the SLA was actually MET (based on your specific data structure).
    """
    if pd.isna(val):
        return 'breached'
    
    clean_val = str(val).lower().strip()
    # Based on your requirement: 'performance should be breach and breach should be perf'
    success_keywords = ['no', 'breach', 'out', 'failed']
    
    return 'met' if any(k in clean_val for k in success_keywords) else 'breached'

def process_data():
    """Main function to transform Excel data into a SQLite Database."""
    print("--- STARTING LOCAL DATA SYNC ---")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"Error: {EXCEL_FILE} not found. Please refresh and save your Excel file first.")
        return

    try:
        # 1. Load Excel and find the 'Ref' header row
        print("Reading Excel file...")
        df_raw = pd.read_excel(EXCEL_FILE, header=None)
        header_mask = df_raw.eq('Ref').any(axis=1)
        
        if not header_mask.any():
            raise ValueError("Could not find the 'Ref' column. Check your Excel formatting.")
        
        header_idx = df_raw.index[header_mask].tolist()[0]
        df = pd.read_excel(EXCEL_FILE, skiprows=header_idx)
        df.columns = [str(col).strip() for col in df.columns]

        # 2. Process SLA Columns (TTO & TTR)
        mapping_config = {
            'TTO': (['SLA tto p', 'SLA tto passed'], 'SLA tto passed', 'TTO_Done'),
            'TTR': (['SLA ttr pa', 'SLA ttr passed'], 'SLA ttr passed', 'TTR_Done')
        }

        for key, (keys, target_col, numeric_col) in mapping_config.items():
            found = find_column(df, keys)
            if found:
                df[target_col] = df[found].apply(map_sla_performance)
                # Numeric column for charts (1 = Met, 0 = Breached)
                df[numeric_col] = df[target_col].apply(lambda x: 1 if x == 'met' else 0)

        # 3. Map Agent Metadata & Operational Units
        agent_col = find_column(df, ['Agent Name', 'Agent'])
        org_col = find_column(df, ['Organization', 'Team'])
        
        # Ensure we have strings for mapping
        df['Agent'] = df[agent_col].fillna('Unknown').astype(str) if agent_col else 'Unknown'
        temp_org = df[org_col].fillna('N/A').astype(str) if org_col else 'N/A'

        # Apply the get_operational_unit logic
        df['Mapped_Team'] = df.apply(
            lambda row: get_operational_unit(row['Agent'], temp_org.loc[row.name]), 
            axis=1
        )

        # 4. Standardize Start Dates
        date_col = find_column(df, ['Start date'])
        if date_col:
            df['Start date'] = pd.to_datetime(df[date_col], errors='coerce')

        # 5. Save to SQLite Database
        print(f"Saving processed data to {DB_FILE}...")
        with sqlite3.connect(DB_FILE) as conn:
            df.to_sql('analytics_data', conn, if_exists='replace', index=False)

        print("--- SUCCESS: LOCAL DATABASE UPDATED ---")
        print(f"Next Step: Commit and Push '{os.path.basename(DB_FILE)}' to GitHub.")

    except Exception as e:
        print(f"Critical Error during processing: {e}")

if __name__ == "__main__":
    process_data()
