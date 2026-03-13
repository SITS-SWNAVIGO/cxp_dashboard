import pandas as pd
import mysql.connector
import os
from datetime import datetime

# --- 1. CONFIGURATION ---
# These variables should be set in your Easypanel Environment tab
DB_HOST = os.getenv("DB_HOST", "213.210.36.220")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = "sits_analytics"

EXCEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.xlsx')

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def find_column(df, keywords):
    for col in df.columns:
        if any(key.lower() in str(col).lower() for key in keywords):
            return col
    return None

def map_sla_performance(val):
    if pd.isna(val): return 'breached'
    clean_val = str(val).lower().strip()
    # 'no' or 'failed' indicates a successful 'Met' status per user logic
    success_keywords = ['no', 'breach', 'out', 'failed']
    return 'met' if any(k in clean_val for k in success_keywords) else 'breached'

def process_data():
    print("--- STARTING DATABASE SYNC (MYSQL) ---")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"Error: {EXCEL_FILE} not found.")
        return

    try:
        # 1. Load Excel
        df_raw = pd.read_excel(EXCEL_FILE, header=None)
        header_mask = df_raw.eq('Ref').any(axis=1)
        header_idx = df_raw.index[header_mask].tolist()[0]
        df_new = pd.read_excel(EXCEL_FILE, skiprows=header_idx)
        df_new.columns = [str(col).strip() for col in df_new.columns]

        # 2. Identify Columns
        ref_col = find_column(df_new, ['ref']) or 'Ref'
        status_col = find_column(df_new, ['status', 'state']) or 'Status'
        agent_col = find_column(df_new, ['agent']) or 'Agent'
        sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        
        # 3. Create History Table with UNIQUE constraint to prevent duplicates
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history_table (
                Ref VARCHAR(50), 
                Current_Status VARCHAR(50), 
                Agent VARCHAR(100), 
                Status_Log_Date DATETIME,
                UNIQUE KEY unique_status (Ref, Current_Status)
            )
        """)

        # 4. Prepare Data
        df_current = df_new.copy()
        df_current['Current_Status'] = df_current[status_col].fillna('Unknown').astype(str)
        df_current['Agent'] = df_current[agent_col].fillna('Unknown').astype(str)
        df_current['Ref'] = df_current[ref_col].astype(str)

        # 5. Detect Changes by checking what ALREADY exists in history_table
        # This prevents the "3 New entries" issue
        existing_history = pd.read_sql("SELECT Ref, Current_Status FROM history_table", conn)
        
        # Merge to find rows that don't exist in the DB yet
        comparison = df_current.merge(existing_history, on=['Ref', 'Current_Status'], how='left', indicator=True)
        new_changes = comparison[comparison['_merge'] == 'left_only'].copy()

        if not new_changes.empty:
            new_changes['Status_Log_Date'] = sync_time
            history_entries = new_changes[['Ref', 'Current_Status', 'Agent', 'Status_Log_Date']]
            
            # Use SQLAlchemy or manual insert for MySQL
            from sqlalchemy import create_engine
            engine = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
            history_entries.to_sql('history_table', engine, if_exists='append', index=False)
            print(f">>> SUCCESS: Logged {len(history_entries)} new status updates.")
        else:
            print(">>> INFO: No new status changes to log.")

        # 6. Update main Analytics table
        for key, keywords in [('SLA tto passed', ['sla tto p']), ('SLA ttr passed', ['sla ttr pa'])]:
            found = find_column(df_current, keywords)
            if found:
                df_current[key] = df_current[found].apply(map_sla_performance)

        df_current.to_sql('analytics_data', engine, if_exists='replace', index=False)
        conn.commit()
        conn.close()
        print("--- DATABASE SYNC FINISHED ---")

    except Exception as e:
        print(f"Sync Error: {e}")

if __name__ == "__main__":
    process_data()

