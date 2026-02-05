# src/styles.py
import streamlit as st
import os

def set_style():
    """Analytics BI – Bank-grade CXP Analytics UI (Elegant, Modern, Big Fonts)"""
    st.markdown("""
    <style>

    /* ==============================
       GLOBAL APP
    ============================== */
    .stApp {
        background-color: #FFFFFF;
        color: #0A1F44;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }

    /* ==============================
       PAGE TITLES
    ============================== */
    .page-title {
        font-size: 4rem;
        font-weight: 900;
        letter-spacing: 1px;
        margin-bottom: 12px;
        color: #0A1F44;
        border-bottom: 5px solid #FF9C33;
        padding-bottom: 12px;
    }

    .page-subtitle {
        font-size: 1.5rem;
        font-weight: 600;
        color: #4B5D6B;
        margin-bottom: 28px;
    }

    .section-title {
        font-size: 2rem;
        font-weight: 800;
        margin-top: 28px;
        margin-bottom: 12px;
        color: #0A1F44;
        border-bottom: 3px solid #FFB84D;
        padding-bottom: 8px;
    }

    /* ==============================
       BODY TEXT
    ============================== */
    p, span, label, td {
        font-size: 1.15rem !important;
        font-weight: 500;
        color: #0A1F44;
    }

    /* ==============================
       KPI CARDS
    ============================== */
    .kpi-card {
        background-color: #FFB84D;
        border-left: 6px solid #FF9C33;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        margin-bottom: 16px;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }

    .kpi-title {
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
        color: #0A1F44;
    }

    .kpi-card h2 {
        font-size: 2.8rem;
        font-weight: 900;
        margin: 0;
    }

    /* ==============================
       DATAFRAMES
    ============================== */
    .stDataFrame {
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        overflow: hidden;
    }

    .stDataFrame th {
        background-color: #FF9C33;
        color: white;
        padding: 12px;
        font-weight: 700;
        font-size: 1.15rem;
        text-align: center;
    }

    .stDataFrame td {
        padding: 10px;
        font-size: 1.1rem;
    }

    /* ==============================
       SIDEBAR
    ============================== */
    section[data-testid="stSidebar"] {
        background-color: #FFB84D;
        border-right: 3px solid #FF9C33;
        padding-top: 1rem;
    }

    section[data-testid="stSidebar"] * {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    /* ==============================
       INPUTS / SELECT / TEXTAREA (Sidebar)
    ============================== */
    section[data-testid="stSidebar"] input, 
    section[data-testid="stSidebar"] select, 
    section[data-testid="stSidebar"] textarea {
        font-size: 1.15rem !important;
        padding: 0.6rem !important;
        border-radius: 12px !important;
        border: 1px solid #FFB84D !important;
        color: white !important;           /* typed text white */
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] input::placeholder,
    section[data-testid="stSidebar"] select::placeholder,
    section[data-testid="stSidebar"] textarea::placeholder {
        color: white !important;           /* placeholder white */
        opacity: 1 !important;
        font-weight: 600 !important;
    }

    /* ==============================
       BUTTONS
    ============================== */
    button {
        background-color: #FFB84D !important;
        color: #0A1F44 !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.25rem !important;
        border: none !important;
        font-size: 1.1rem !important;
        transition: all 0.2s ease;
    }

    button:hover {
        background-color: #FF9C33 !important;
        transform: translateY(-2px);
    }

    /* ==============================
       TOGGLE CHECKBOXES (Sidebar)
    ============================== */
    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] > label {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        background-color: #FFB84D !important;
        padding: 10px 14px !important;
        border-radius: 16px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] input {
        appearance: none !important;
        width: 44px !important;
        height: 24px !important;
        background-color: #e6e6e6 !important;
        border-radius: 999px !important;
        position: relative !important;
        cursor: pointer !important;
        transition: background-color 0.25s ease !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] input::before {
        content: "" !important;
        position: absolute !important;
        width: 20px !important;
        height: 20px !important;
        top: 2px !important;
        left: 2px !important;
        background-color: white !important;
        border-radius: 50% !important;
        transition: transform 0.25s ease !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] input:checked {
        background-color: #FF9C33 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] input:checked::before {
        transform: translateX(20px) !important;
    }

    /* ==============================
       PAGE PADDING
    ============================== */
    .block-container {
        padding-top: 3.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    </style>
    """, unsafe_allow_html=True)


def show_logo():
    """Display Analytics BI logo centered, without expander icon"""
    logo_path = os.path.join(os.getcwd(), "assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)


def kpi_card(title, value, color="#FFB84D"):
    """Custom KPI card"""
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color:{color}">
            <div class="kpi-title">{title}</div>
            <h2>{value}</h2>
        </div>
    """, unsafe_allow_html=True)
