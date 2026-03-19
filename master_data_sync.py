import pandas as pd
import os
import time
from datetime import datetime
from sqlalchemy import create_engine, text, DateTime, String
import mysql.connector

# --- 1. CONFIGURATION ---
DB_HOST = "213.210.36.220"
DB_USER = "sits"
DB_PASS = "123456"
DB_NAME = "sits_analytics"
DB_PORT = "3306"

TTO_SLA_HOURS = 4
TTR_SLA_HOURS = 24

connection_url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_url, pool_pre_ping=True)

def calculate_performance(row):
    """
    LOGIC: 
    Late tickets -> MET = 1
    On-Time tickets -> BREACH = 1
    """
    now = datetime.now()
    status = str(row.get('Status', '')).lower().strip()
    is_completed = status in ['resolved', 'closed', 'completed', 'done']
    
    start_date = row.get('Start Date')
    if pd.isna(start_date):
        return pd.Series([0, 0, 0, 0])
        
    hours_open = (now - start_date).total_seconds() / 3600

    # TTO Logic
    if not is_completed and hours_open > TTO_SLA_HOURS:
        tto_met, tto_breach = 1, 0 
    else:
        tto_met, tto_breach = 0, 1 

    # TTR Logic
    if not is_completed and hours_open > TTR_SLA_HOURS:
        ttr_met, ttr_breach = 1, 0 
    else:
        ttr_met, ttr_breach = 0, 1 
    
    return pd.Series([tto_met, tto_breach, ttr_met, ttr_breach])

def update_audit_history(df):
    """
    Automatically creates/updates the history_table for Tab 5.
    """
    try:
        # Prepare the snapshot for history
        history_snapshot = pd.DataFrame({
            'Status_Log_Date': [datetime.now()] * len(df),
            'Ref': df['Ref'],
            'Current_Status': df['Status'],
            'Agent': df['Agent']
        })

        # Define MySQL specific types for auto-creation
        dtype_map = {
            'Status_Log_Date': DateTime(),
            'Ref': String(50),
            'Current_Status': String(100),
            'Agent': String(255)
        }

        # Push to MySQL - 'append' creates the table if it's missing
        history_snapshot.to_sql(
            'history_table', 
            con=engine, 
            if_exists='append', 
            index=False,
            dtype=dtype_map
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] History table synced successfully.")
    except Exception as e:
        print(f"HISTORY SYNC ERROR: {e}")

def process_and_upload():
    print(f"\n--- Starting Sync Cycle: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    if not os.path.exists('data.xlsx'):
        print("ERROR: 'data.xlsx' not found in current directory.")
        return

    try:
        # 1. LOAD DATA
        df_raw = pd.read_excel('data.xlsx', header=None)
        header_mask = df_raw.eq('Ref').any(axis=1)
        header_idx = df_raw.index[header_mask].tolist()[0]
        df = pd.read_excel('data.xlsx', skiprows=header_idx)
        
        # 2. CLEAN & RENAME
        mapping = {
            'Agent Name': 'Agent',
            'Start date (date)': 'Start Date',
            'Organization Name': 'Customer'
        }
        df = df.rename(columns=mapping)
        df.columns = [str(col).strip() for col in df.columns]

        # 3. CONVERSION
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df = df.dropna(subset=['Ref']) # Ensure we don't process empty rows

        # 4. PERFORMANCE CALCS
        df[['TTO MET', 'TTO BREACH', 'TTR MET', 'TTR BREACH']] = df.apply(calculate_performance, axis=1)

        # 5. UPLOAD MAIN ANALYTICS DATA
        # We replace the main data entirely to keep it fresh
        df.to_sql('analytics_data', engine, if_exists='replace', index=False)
        print(f"SUCCESS: {len(df)} records uploaded to analytics_data.")

        # 6. UPLOAD AUDIT HISTORY (TAB 5)
        # We append to history to build the trail over time
        update_audit_history(df)

    except Exception as e:
        print(f"SYNC FAILED: {str(e)}")

if __name__ == "__main__":
    # Standard loop: Run every 5 minutes
    while True:
        process_and_upload()
        print("Sleeping for 300 seconds...")
        time.sleep(300)
