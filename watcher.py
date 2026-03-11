import sqlite3
import pandas as pd

def sync_db_to_excel():
    # Connect to your database
    conn = sqlite3.connect('sits_analytics.db')
    
    # Query the data you need
    df = pd.read_sql_query("SELECT * FROM your_table_name", conn)
    
    # Export to Excel
    df.to_excel('sits_live_report.xlsx', index=False)
    
    conn.close()
    print("Excel sheet updated.")
