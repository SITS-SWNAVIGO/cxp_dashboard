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
DB_PORT = "3309"

TTO_SLA_HOURS = 4
TTR_SLA_HOURS = 24

connection_url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_url, pool_pre_ping=True)

def calculate_performance(row):
    """
    LOGIC: 
    If time exceeded and ticket is not completed -> BREACH = 1, MET = 0
    Otherwise -> MET = 1, BREACH = 0
    """
    now = datetime.now()
    status = str(row.get('Status', '')).lower().strip()
    is_completed = status in ['resolved', 'closed', 'completed', 'done']
    
    start_date = row.get('Start Date')
    if pd.isna(start_date):
        return pd.Series([0, 0, 0, 0])
        
    hours_open = (now - start_date).total_seconds() / 3600

    # TTO Logic: If hours > 4, it is a BREACH (1). Otherwise MET (1).
    if not is_completed and hours_open > TTO_SLA_HOURS:
        tto_met, tto_breach = 0, 1 
    else:
        tto_met, tto_breach = 1, 0 

    # TTR Logic: If hours > 24, it is a BREACH (1). Otherwise MET (1).
    if not is_completed and hours_open > TTR_SLA_HOURS:
        ttr_met, ttr_breach = 0, 1 
    else:
        ttr_met, ttr_breach = 1, 0 
    
    return pd.Series([tto_met, tto_breach, ttr_met, ttr_breach])

def update_audit_history(df):
    """
    Automatically creates/updates the history_table for the Audit Trail.
    """
    try:
        # Prepare the snapshot for history
        history_snapshot = pd.DataFrame({
            'Status_Log_Date': [datetime.now()] * len(df),
            'Ref': df['Ref'],
            'Current_Status': df['Status'],
            'Agent': df['Agent']
        })

        # Define MySQL specific types
        dtype_map = {
            'Status_Log_Date': DateTime(),
            'Ref': String(50),
            'Current_Status': String(100),
            'Agent': String(255)
        }

        # Push to MySQL - 'append' builds the historical trail
        history_snapshot.to_sql(
            'history_table', 
            con=engine, 
            if_exists='append', 
            index=False,
            dtype=dtype_map
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] History table synced.")
    except Exception as e:
        print(f"HISTORY SYNC ERROR: {e}")

def process_and_upload():
    print(f"\n--- Starting Sync Cycle: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    if not os.path.exists('data.xlsx'):
        print("ERROR: 'data.xlsx' not found.")
        return

    try:
        # 1. LOAD DATA
        # Reading raw to find header row dynamically
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
        df = df.dropna(subset=['Ref']) 

        # 4. PERFORMANCE CALCS
        # This populates TTO MET, TTO BREACH, TTR MET, TTR BREACH
        df[['TTO MET', 'TTO BREACH', 'TTR MET', 'TTR BREACH']] = df.apply(calculate_performance, axis=1)

        # 5. UPLOAD MAIN ANALYTICS DATA
        # 'replace' ensures we always have the latest snapshot in the main table
        df.to_sql('analytics_data', engine, if_exists='replace', index=False)
        print(f"SUCCESS: {len(df)} records uploaded to analytics_data.")

        # 6. UPLOAD AUDIT HISTORY
        update_audit_history(df)

    except Exception as e:
        print(f"SYNC FAILED: {str(e)}")

if __name__ == "__main__":
    # Runs every 5 minutes (300 seconds)
    while True:
        process_and_upload()
        print("Waiting for next cycle (5 minutes)...")
        time.sleep(300)