import streamlit as st

def apply_elegant_blue_theme():
    """
    Applies an elegant enterprise theme with a dark blue sidebar.
    """
    st.markdown("""
    <style>
        /* Main App Background */
        .stApp {
            background-color: #F4F9FF;
            color: #002D62;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        /* Top Navigation/Header Bar */
        .header-container {
            background-color: #002D62;
            padding: 20px 30px;
            border-radius: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            border-bottom: 5px solid #00A3E0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        /* --- UPDATED SIDEBAR STYLING --- */
        [data-testid="stSidebar"] {
            background-color: #002D62; /* Dark Blue Background */
            color: #FFFFFF;
        }

        /* Sidebar Text and Labels */
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stSelectbox div {
            color: #FFFFFF !important;
        }

        /* Sidebar Slider Tracks and Buttons */
        [data-testid="stSidebar"] .stButton>button {
            background-color: #00A3E0;
            color: white;
            border: 1px solid #00A3E0;
        }
        
        [data-testid="stSidebar"] .stButton>button:hover {
            background-color: #FFFFFF;
            color: #002D62;
        }
        /* ------------------------------- */

        /* KPI Card Design */
        .kpi-card {
            background-color: #FFFFFF;
            padding: 25px;
            border-radius: 12px;
            border-top: 4px solid #00A3E0;
            box-shadow: 0 5px 15px rgba(0,45,98,0.08);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .kpi-card:hover {
            transform: translateY(-5px);
        }

        .kpi-label {
            font-size: 0.9rem;
            font-weight: 600;
            color: #506784;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .kpi-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #002D62 !important;
            margin: 0;
        }

        /* Professional Buttons (Main Area) */
        .stButton>button {
            background-color: #002D62;
            color: #FFFFFF;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            letter-spacing: 0.5px;
            width: 100%;
            padding: 0.6rem;
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            background-color: #00A3E0;
            color: white;
            box-shadow: 0 4px 12px rgba(0,163,224,0.3);
        }

        /* Section Headings */
        .section-header {
            color: #002D62;
            font-weight: 700;
            font-size: 1.2rem;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 5px solid #00A3E0;
            padding-left: 15px;
            text-transform: uppercase;
        }

        /* Remove Streamlit branding */
        #MainMenu, footer, header {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True)