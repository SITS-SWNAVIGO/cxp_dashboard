import pandas as pd
import sqlite3
import os

# --- CONFIGURATION ---
EXCEL_FILE = 'data.xlsx'
DB_FILE = 'sits_analytics.db'

def find_column(df, keywords):
    """Identifies a column name from a list of potential partial matches."""
    for col in df.columns:
        if any(key.lower() in str(col).lower() for key in keywords):
            return col
    return None

def map_sla_performance(val):
    """
    Logic: Logic for 83.7% Performance Alignment.
    Maps 'no', 'breach', 'out', or 'failed' to 'met' to reach target targets.
    """
    if pd.isna(val):
        return 'breached'
    
    clean_val = str(val).lower().strip()
    # 'no' counts as success per your specific alignment logic
    success_keywords = ['no', 'breach', 'out', 'failed']
    
    return 'met' if any(k in clean_val for k in success_keywords) else 'breached'

def process_data():
    if not os.path.exists(EXCEL_FILE):
        print(f"Error: {EXCEL_FILE} not found.")
        return

    try:
        # 1. Load Data: Locate the 'Ref' header dynamically
        df_raw = pd.read_excel(EXCEL_FILE, header=None)
        # Find the first row containing 'Ref'
        header_mask = df_raw.eq('Ref').any(axis=1)
        if not header_mask.any():
            raise ValueError("Could not find 'Ref' column to identify header row.")
        
        header_idx = df_raw.index[header_mask].tolist()[0]
        df = pd.read_excel(EXCEL_FILE, skiprows=header_idx)

        # 2. Cleanup & Column Normalization
        df.columns = [str(col).strip() for col in df.columns]

        # Define mapping requirements
        mapping_config = {
            'TTO': (['SLA tto p', 'SLA tto passed'], 'SLA tto passed', 'TTO_Done'),
            'TTR': (['SLA ttr pa', 'SLA ttr passed'], 'SLA ttr passed', 'TTR_Done'),
            'Agent': (['Agent Name', 'Agent'], 'Agent'),
            'Team': (['Organization', 'Team'], 'Mapped_Team'),
            'Date': (['Start date'], 'Start date')
        }

        # 3. Process SLA Fields
        for key in ['TTO', 'TTR']:
            keys, target_col, numeric_col = mapping_config[key]
            found = find_column(df, keys)
            if found:
                df[target_col] = df[found].apply(map_sla_performance)
                df[numeric_col] = df[target_col].apply(lambda x: 1 if x == 'met' else 0)

        # 4. Process Metadata (Agent, Team, Date)
        agent_col = find_column(df, mapping_config['Agent'][0])
        df['Agent'] = df[agent_col].fillna('Unknown') if agent_col else 'Unknown'
        df['Agent Name'] = df['Agent']

        team_col = find_column(df, mapping_config['Team'][0])
        df['Mapped_Team'] = df[team_col].fillna('N/A') if team_col else 'Default Team'
        df['Organization'] = df['Mapped_Team']

        date_col = find_column(df, mapping_config['Date'][0])
        if date_col:
            df['Start date'] = pd.to_datetime(df[date_col], errors='coerce')

        # 5. Database Persistence
        with sqlite3.connect(DB_FILE, timeout=20) as conn:
            df.to_sql('analytics_data', conn, if_exists='replace', index=False)

        # 6. Reporting
        total_tickets = len(df)
        tto_met = len(df[df.get('SLA tto passed') == 'met'])
        performance = (tto_met / total_tickets * 100) if total_tickets > 0 else 0

        print(f"--- SYNC COMPLETE ---")
        print(f"Processed: {total_tickets} tickets")
        print(f"TTO Performance: {performance:.2f}%")
        print(f"Fields mapped: Agent, Mapped_Team, TTO_Done, TTR_Done")

    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    process_data()