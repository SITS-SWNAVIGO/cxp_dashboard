# src/styles.py
import streamlit as st
from PIL import Image
import os

def set_style():
    """Apply Cyan-Green Power BI Style Theme"""
    st.markdown(
        """
        <style>

        /* ===============================
           GLOBAL BACKGROUND (CYAN → GREEN)
        ===============================*/
        .stApp {
            background: linear-gradient(135deg, #00C9A7, #2EE59D);
            color: #0F172A;
            font-family: 'Segoe UI', sans-serif;
        }

        /* ===============================
           HEADERS
        ===============================*/
        h1, h2, h3, h4 {
            color: #0F172A;
            font-weight: 600;
        }

        h1 {
            border-bottom: 3px solid #0EA5A4;
            padding-bottom: 8px;
            margin-bottom: 20px;
        }

        /* ===============================
           DESCRIPTION TEXT
        ===============================*/
        .stMarkdown p {
            color: #064E3B;
            font-size: 14px;
        }

        /* ===============================
           KPI CARDS
        ===============================*/
        .kpi-card {
            background-color: #ECFEFF;
            border-radius: 10px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 6px 14px rgba(0,0,0,0.15);
            border-left: 6px solid #14B8A6;
            margin-bottom: 16px;
        }

        .kpi-card h4 {
            font-size: 13px;
            color: #047857;
            margin-bottom: 6px;
        }

        .kpi-card h2 {
            font-size: 30px;
            color: #0F766E;
            margin: 0;
        }

        /* ===============================
           DATAFRAMES
        ===============================*/
        .stDataFrame {
            background-color: #ECFEFF;
            border-radius: 10px;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .stDataFrame table {
            border-collapse: collapse;
            width: 100%;
            font-size: 13px;
        }

        .stDataFrame th {
            background-color: #0EA5A4;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
        }

        .stDataFrame td {
            padding: 8px;
            border-bottom: 1px solid #A7F3D0;
            color: #064E3B;
        }

        .stDataFrame tr:nth-child(even) {
            background-color: #D1FAE5;
        }

        .stDataFrame tr:hover {
            background-color: #99F6E4;
        }

        /* ===============================
           SIDEBAR (SLICERS)
        ===============================*/
        section[data-testid="stSidebar"] {
            background-color: #ECFEFF;
            border-right: 2px solid #5EEAD4;
        }

        /* ===============================
           INPUTS
        ===============================*/
        input, textarea, select {
            background-color: #F0FDFA !important;
            color: #064E3B !important;
            border-radius: 6px !important;
            border: 1px solid #5EEAD4 !important;
        }

        /* ===============================
           BUTTONS
        ===============================*/
        button {
            background: linear-gradient(135deg, #06B6D4, #22C55E) !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 0.55em 1.4em !important;
            font-weight: 600 !important;
            border: none !important;
            transition: all 0.2s ease-in-out;
        }

        button:hover {
            background: linear-gradient(135deg, #0891B2, #16A34A) !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.25);
            transform: translateY(-1px);
        }

        /* ===============================
           DOWNLOAD BUTTONS
        ===============================*/
        div.stDownloadButton > button {
            background: linear-gradient(135deg, #16A34A, #22C55E) !important;
        }

        div.stDownloadButton > button:hover {
            background: linear-gradient(135deg, #15803D, #16A34A) !important;
        }

        /* ===============================
           PAGE PADDING
        ===============================*/
        .block-container {
            padding-top: 1.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

def show_logo():
    """Display a logo from assets folder"""
    logo_path = os.path.join(os.getcwd(), "assets", "logo.png")
    try:
        img = Image.open(logo_path)
        st.image(img, width=150)
    except FileNotFoundError:
        st.warning("Logo file not found in assets/logo.png")

def kpi_card(title, value, color="#14B8A6"):
    """Cyan-Green KPI card"""
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color:{color}">
            <h4>{title}</h4>
            <h2>{value}</h2>
        </div>
    """, unsafe_allow_html=True)
