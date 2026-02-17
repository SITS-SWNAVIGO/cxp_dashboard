# src/data_processing.py
import pandas as pd
import requests
from io import BytesIO
import streamlit as st

# -----------------------------
# LIVE DATA FETCH
# -----------------------------
def fetch_live_data():
    """
    Fetch live ticket data from the CXP web service link.
    Returns a pandas DataFrame.
    """
    url = "https://cxp.sits.lk/webservices/export-v2.php?format=spreadsheet&login_mode=basic&date_format=Y-m-d+H%3Ai%3As&query=15"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error if request fails

        # Read Excel content into DataFrame
        df = pd.read_excel(BytesIO(response.content))
        return df

    except Exception as e:
        st.error(f"Failed to load live data: {e}")
        return pd.DataFrame()  # return empty DataFrame if failed

# -----------------------------
# DATA CLEANING
# -----------------------------
def clean_name(data, col):
    """Remove IDs from names"""
    if col in data.columns:
        return data[col].astype(str).str.replace(r'[\s_-]*\d+$', '', regex=True).str.strip()
    return None

# -----------------------------
# KPI COMPUTATION
# -----------------------------
def compute_kpis(data):
    """Add KPI columns"""
    data['Done Tasks'] = data['Status'].apply(lambda x: 1 if str(x).lower() in ['done', 'closed'] else 0) if 'Status' in data.columns else 0
    data['Pending Tasks'] = data['Status'].apply(lambda x: 1 if str(x).lower() not in ['done', 'closed'] else 0) if 'Status' in data.columns else 0
    data['SLA TTO Done'] = data['SLA tto passed'].apply(lambda x: 1 if str(x).lower() == 'yes' else 0) if 'SLA tto passed' in data.columns else 0
    data['SLA TTO Violations'] = data['SLA tto over'].apply(lambda x: 1 if str(x).lower() == 'yes' else 0) if 'SLA tto over' in data.columns else 0
    data['SLA TTR Done'] = data['SLA ttr passed'].apply(lambda x: 1 if str(x).lower() == 'yes' else 0) if 'SLA ttr passed' in data.columns else 0
    data['SLA TTR Violations'] = data['SLA ttr over'].apply(lambda x: 1 if str(x).lower() == 'yes' else 0) if 'SLA ttr over' in data.columns else 0

    if 'Closed date' in data.columns and 'Start date' in data.columns:
        data['Closed date'] = pd.to_datetime(data['Closed date'], errors='coerce')
        data['Start date'] = pd.to_datetime(data['Start date'], errors='coerce')
        data['Duration (days)'] = (data['Closed date'] - data['Start date']).dt.days
    else:
        data['Duration (days)'] = None
    return data

