# app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from src.styles import set_style, show_logo, kpi_card
from src.data_processing import clean_name, compute_kpis
from src.ppt_export import create_ppt
import plotly.express as px
import plotly.figure_factory as ff
import numpy as np

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="SITS Analytics BI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# CUSTOM STYLE & LOGO
# -------------------------------
set_style()
show_logo()

# -------------------------------
# SESSION STATE DEFAULTS
# -------------------------------
for key, default in {
    "data": pd.DataFrame(),
    "monthly_summary": pd.DataFrame(),
    "tech_summary": pd.DataFrame(),
    "caller_summary": pd.DataFrame(),
    "show_kpis": True,
    "show_trends": True,
    "anonymize_data": False,
    "theme": "Light",
    "decimal_places": 1,
    "default_format": "Excel",
    "show_tooltips": True
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("Navigation")

# ===== UNIVERSAL SEARCH BAR =====
st.sidebar.markdown("### Universal Search")
universal_search = st.sidebar.text_input("Search Technician, Caller, or Company")

page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Advanced Analytics", "Data Explorer", "Export Center", "Settings"]
)

# Reset Session
if st.sidebar.button("Reset Session"):
    for key in st.session_state.keys():
        st.session_state[key] = None
    st.experimental_rerun()

# =====================================================
# FILE UPLOAD FUNCTION
# =====================================================
def upload_file():
    st.markdown("## Upload Ticket Data")
    uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type="xlsx")
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.session_state.data = df.copy()
        with st.expander("Preview Uploaded Data"):
            st.dataframe(df.head(), use_container_width=True)
        return df
    else:
        st.info("Please upload an Excel file to continue.")
        st.stop()

# =====================================================
# DATA CLEANING & ANONYMIZATION
# =====================================================
def clean_data(df):
    df['Company Name'] = clean_name(df, 'Organization->Name') if 'Organization->Name' in df.columns else ""
    df['Technician Name'] = clean_name(df, 'Agent->Full name') if 'Agent->Full name' in df.columns else ""
    df['Caller Name'] = clean_name(df, 'Caller->Full name') if 'Caller->Full name' in df.columns else ""
    return df

def anonymize(df, columns):
    for col in columns:
        df[col] = [f"{col.split('->')[0]} {i+1}" for i in range(len(df))]
    return df

# =====================================================
# KPI & SUMMARY FUNCTIONS
# =====================================================
def calculate_monthly_summary(df):
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
        df['Month'] = df['Start date'].dt.to_period('M').astype(str)
    else:
        df['Month'] = 'Unknown'

    df = compute_kpis(df)
    df['Duration (days)'] = pd.to_numeric(df.get('Duration (days)', 0), errors='coerce').fillna(0)

    monthly_summary = (
        df.groupby('Month')
        .agg({
            'Ref': 'count',
            'Done Tasks': 'sum',
            'Pending Tasks': 'sum',
            'SLA TTO Done': 'sum',
            'SLA TTR Done': 'sum',
            'Duration (days)': 'mean'
        })
        .rename(columns={
            'Ref': 'Total Tickets',
            'Done Tasks': 'Closed Tickets',
            'Pending Tasks': 'Pending Tickets',
            'Duration (days)': 'Avg Resolution Days'
        })
        .reset_index()
    )

    monthly_summary['SLA TTO Violations'] = monthly_summary['Total Tickets'] - monthly_summary['SLA TTO Done']
    monthly_summary['SLA TTR Violations'] = monthly_summary['Total Tickets'] - monthly_summary['SLA TTR Done']
    monthly_summary['SLA Violations'] = ((monthly_summary['SLA TTO Violations'] + monthly_summary['SLA TTR Violations']) / 2).round(0)
    monthly_summary['Closure %'] = (monthly_summary['Closed Tickets'] / monthly_summary['Total Tickets'] * 100).round(1)
    monthly_summary['SLA %'] = ((monthly_summary['SLA TTO Done'] + monthly_summary['SLA TTR Done']) / (2 * monthly_summary['Total Tickets']) * 100).round(1)
    monthly_summary['Avg Resolution Days'] = monthly_summary['Avg Resolution Days'].fillna(0)

    return df, monthly_summary

def top_performers(df, role_col):
    summary = (
        df.groupby(role_col)
        .agg(Tickets=('Ref','count'), Done=('Done Tasks','sum'),
             SLA_Done=('SLA TTO Done','sum'), SLA_TTR=('SLA TTR Done','sum'))
        .reset_index()
    )
    summary['SLA %'] = ((summary['SLA_Done'] + summary['SLA_TTR']) / (summary['Tickets']*2) * 100).round(1)
    top5 = summary.sort_values('SLA %', ascending=False).head(5)
    return summary, top5

def style_sla(df, column='SLA %'):
    def color(val):
        if val >= 90: return "green"
        elif val >= 75: return "orange"
        else: return "red"
    return df.style.applymap(lambda x: f"color:{color(x)}; font-weight:bold", subset=[column])

# =====================================================
# UNIVERSAL SEARCH
# =====================================================
def apply_universal_search(df):
    if universal_search:
        df = df[
            df['Technician Name'].str.contains(universal_search, case=False, na=False) |
            df['Caller Name'].str.contains(universal_search, case=False, na=False) |
            df['Company Name'].str.contains(universal_search, case=False, na=False)
        ]
    return df

# =====================================================
# FILTER DATA - LAST 3 MONTHS ONLY
# =====================================================
def filter_last_3_months(df):
    if 'Start date' in df.columns:
        df['Start date'] = pd.to_datetime(df['Start date'], errors='coerce')
        today = pd.Timestamp.today()
        three_months_ago = today - pd.DateOffset(months=3)
        df_filtered = df[df['Start date'] >= three_months_ago]
        return df_filtered
    else:
        return df

# =====================================================
# PREPARE DATA FUNCTION
# =====================================================
def prepare_data():
    data = st.session_state.data if not st.session_state.data.empty else upload_file()
    data = clean_data(data)
    data = apply_universal_search(data)
    data = filter_last_3_months(data)  # <-- last 3 months only
    return data

# =====================================================
# DASHBOARD PAGE
# =====================================================
if page == "Dashboard":
    st.markdown('<h1 class="page-title">DASHBOARD OVERVIEW</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="page-subtitle">Your real-time BI insights at a glance</h4>', unsafe_allow_html=True)

    data = prepare_data()

    # EXCLUDE FILTERS
    col1, col2 = st.columns(2)
    with col1:
        companies_to_remove = st.multiselect("Exclude Companies", data['Company Name'].dropna().unique())
        if companies_to_remove:
            data = data[~data['Company Name'].isin(companies_to_remove)]
    with col2:
        persons_options = list(set(data['Technician Name'].tolist() + data['Caller Name'].tolist()))
        persons_to_remove = st.multiselect("Exclude Persons", persons_options)
        if persons_to_remove:
            mask_tech = data['Technician Name'].isin(persons_to_remove)
            mask_caller = data['Caller Name'].isin(persons_to_remove)
            data = data[~(mask_tech | mask_caller)]

    # ANONYMIZATION
    if st.session_state.anonymize_data:
        sensitive_columns = st.multiselect("Select columns to anonymize", options=data.columns)
        data = anonymize(data, sensitive_columns)

    # CALCULATE KPI SUMMARY
    data, monthly_summary = calculate_monthly_summary(data)
    st.session_state.data = data
    st.session_state.monthly_summary = monthly_summary

    # SLA ALERT
    if 'SLA %' in monthly_summary.columns:
        avg_sla = monthly_summary['SLA %'].mean()
        if avg_sla < 75:
            st.warning(f"⚠️ SLA Compliance is low: {avg_sla:.1f}%")
        elif avg_sla < 90:
            st.info(f"ℹ️ SLA Compliance is moderate: {avg_sla:.1f}%")
        else:
            st.success(f"✅ SLA Compliance is excellent: {avg_sla:.1f}%")

    # KPI CARDS
    if st.session_state.show_kpis:
        st.markdown("## Key Metrics")
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Total Tickets", int(monthly_summary['Total Tickets'].sum()))
        c2.metric("Closed Tickets", int(monthly_summary['Closed Tickets'].sum()))
        c3.metric("Pending Tickets", int(monthly_summary['Pending Tickets'].sum()))
        c4.metric("SLA Violations", int(monthly_summary['SLA Violations'].sum()))
        c5.metric("Closure %", f"{monthly_summary['Closure %'].mean():.1f}%")
        c6.metric("SLA Compliance %", f"{monthly_summary['SLA %'].mean():.1f}%")

    # KPI SUMMARY TABLE
    st.markdown("## KPI Summary")
    st.dataframe(monthly_summary, use_container_width=True)

    # PIE CHART
    if 'Closed Tickets' in monthly_summary.columns and 'Pending Tickets' in monthly_summary.columns:
        st.markdown("## Ticket Status Distribution")
        ticket_counts = monthly_summary[['Closed Tickets','Pending Tickets']].sum()
        fig_pie = px.pie(
            names=ticket_counts.index,
            values=ticket_counts.values,
            color=ticket_counts.index,
            color_discrete_map={'Closed Tickets':'green','Pending Tickets':'orange'},
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # TOP PERFORMERS
    if 'Technician Name' in data.columns:
        st.markdown("## Top 5 Technicians")
        tech_summary, top_techs = top_performers(data, 'Technician Name')
        st.plotly_chart(px.bar(top_techs, x='Technician Name', y='SLA %', text='SLA %', color='SLA %', color_continuous_scale='Tealgrn'))
        st.dataframe(style_sla(top_techs), use_container_width=True)
        st.session_state.tech_summary = tech_summary

    if 'Caller Name' in data.columns:
        st.markdown("## Top 5 Callers")
        caller_summary, top_callers = top_performers(data, 'Caller Name')
        st.plotly_chart(px.bar(top_callers, x='Caller Name', y='SLA %', text='SLA %', color='SLA %', color_continuous_scale='Tealgrn'))
        st.dataframe(style_sla(top_callers), use_container_width=True)
        st.session_state.caller_summary = caller_summary

    # MONTHLY TREND
    if st.session_state.show_trends:
        st.markdown("## Monthly KPI Trend")
        fig = px.line(monthly_summary.sort_values('Month'), x='Month', y=['Closure %','SLA %'], markers=True)
        st.plotly_chart(fig, use_container_width=True)

    # DOWNLOAD FILTERED CSV
    if not data.empty:
        st.markdown("## Download Filtered Data as CSV")
        csv_output = data.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv_output, "filtered_data.csv", "text/csv")

# =====================================================
# ADVANCED ANALYTICS PAGE
# =====================================================
elif page == "Advanced Analytics":
    st.markdown('<h1 class="page-title">ADVANCED ANALYTICS</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="page-subtitle">Explore trends, correlations, and performance metrics</h4>', unsafe_allow_html=True)

    data = prepare_data()
    data, monthly_summary = calculate_monthly_summary(data)

    # SLA vs Duration Scatter
    st.markdown("## SLA vs Resolution Days")
    if 'Duration (days)' in data.columns and 'SLA TTO Done' in data.columns:
        fig = px.scatter(data, x='Duration (days)', y='SLA TTO Done',
                         color='Technician Name' if 'Technician Name' in data.columns else None,
                         size='Done Tasks' if 'Done Tasks' in data.columns else None,
                         hover_data=['Company Name'] if 'Company Name' in data.columns else None)
        st.plotly_chart(fig, use_container_width=True)

    # Technician SLA Heatmap
    st.markdown("## Technician SLA Heatmap")
    if 'Technician Name' in data.columns and 'Month' in data.columns:
        pivot = data.pivot_table(
            index='Technician Name',
            columns='Month',
            values='SLA TTO Done',
            aggfunc='sum',
            fill_value=0
        )
        fig_heat = ff.create_annotated_heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale='YlOrRd',
            showscale=True,
            font_colors=['black'],
            annotation_text=pivot.values,
            hoverinfo='z'
        )
        fig_heat.update_layout(
            xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
            yaxis=dict(tickfont=dict(size=8)),
            margin=dict(l=200, r=50, t=50, b=150),
            height=max(600, 30*len(pivot.index)),
        )
        fig_heat.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_heat, use_container_width=True)

    # Correlation Analysis
    st.markdown("## Correlation Matrix")
    numeric_cols = data.select_dtypes(include=np.number).columns.tolist()
    if numeric_cols:
        corr = data[numeric_cols].corr()
        fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', aspect="auto")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("No numeric columns available for correlation analysis.")

# =====================================================
# DATA EXPLORER PAGE
# =====================================================
elif page == "Data Explorer":
    st.markdown('<h1 class="page-title">DATA EXPLORER</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="page-subtitle">Search, filter, and download your ticket data</h4>', unsafe_allow_html=True)

    data = prepare_data()
    data, _ = calculate_monthly_summary(data)
    st.dataframe(data, use_container_width=True)

    # Download Filtered
    st.markdown("## Download Filtered Data")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, sheet_name='Filtered_Data', index=False)
    st.download_button("Download Excel", output.getvalue(), "filtered_data.xlsx")

# =====================================================
# EXPORT CENTER PAGE
# =====================================================
elif page == "Export Center":
    st.markdown('<h1 class="page-title">EXPORT CENTER</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="page-subtitle">Download processed reports and presentations</h4>', unsafe_allow_html=True)

    data = prepare_data()
    monthly_summary = st.session_state.monthly_summary
    tech_summary = st.session_state.tech_summary
    caller_summary = st.session_state.caller_summary

    st.markdown("## Download Reports")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, sheet_name='Processed_Data', index=False)
        monthly_summary.to_excel(writer, sheet_name='Monthly_Summary', index=False)
        if not tech_summary.empty: tech_summary.to_excel(writer, sheet_name='Technician_Summary', index=False)
        if not caller_summary.empty: caller_summary.to_excel(writer, sheet_name='Caller_Summary', index=False)
    st.download_button("Download Excel", output.getvalue(), "analytics_report.xlsx")

    # PowerPoint
    prs = create_ppt({
        'Monthly KPI': monthly_summary,
        'Technician-wise KPI': tech_summary,
        'Caller-wise KPI': caller_summary
    })
    ppt_output = BytesIO()
    prs.save(ppt_output)
    ppt_output.seek(0)
    st.download_button("Download PowerPoint", ppt_output, "analytics_report.pptx")

# =====================================================
# SETTINGS PAGE
# =====================================================
elif page == "Settings":
    st.markdown('<h1 class="page-title">SETTINGS</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="page-subtitle">Customize your dashboard preferences</h4>', unsafe_allow_html=True)

    st.session_state.show_kpis = st.checkbox("Show KPI Cards", value=st.session_state.show_kpis)
    st.session_state.show_trends = st.checkbox("Show Monthly Trends", value=st.session_state.show_trends)
    st.session_state.anonymize_data = st.checkbox("Anonymize Sensitive Data", value=st.session_state.anonymize_data)
    st.session_state.decimal_places = st.slider("Decimal Places in Reports", 0, 3, value=st.session_state.decimal_places)
    st.session_state.theme = st.selectbox("Theme", ["Light", "Dark"], index=0 if st.session_state.theme=="Light" else 1)
