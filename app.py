# app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from src.styles import set_style, show_logo, kpi_card
from src.data_processing import clean_name, compute_kpis
from src.ppt_export import create_ppt
import plotly.express as px
import numpy as np

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="Ticket Report Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# CUSTOM STYLE
# -------------------------------
set_style()
show_logo()

# -------------------------------
# PAGE TITLE
# -------------------------------
st.title("Ticket Report Generator")
st.markdown(
    "Generate **board-ready ticket KPI reports** with filtering, anonymization, "
    "monthly comparison, and export to **Excel & PowerPoint**."
)

# =====================================================
# 1️⃣ UPLOAD
# =====================================================
st.markdown("## Upload Ticket Data")
uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type="xlsx")

if uploaded_file:
    data = pd.read_excel(uploaded_file)

    with st.expander("Preview Uploaded Data"):
        st.dataframe(data.head(), use_container_width=True)

    # =====================================================
    # 2️⃣ CLEANING
    # =====================================================
    st.markdown("## Data Cleaning & Filtering")
    data['Company Name'] = clean_name(data, 'Organization->Name')
    data['Technician Name'] = clean_name(data, 'Agent->Full name')
    data['Caller Name'] = clean_name(data, 'Caller->Full name')

    col1, col2 = st.columns(2)
    with col1:
        if 'Company Name' in data.columns:
            companies_to_remove = st.multiselect(
                "Exclude Companies",
                data['Company Name'].unique()
            )
            if companies_to_remove:
                data = data[~data['Company Name'].isin(companies_to_remove)]
    with col2:
        persons_options = list(set(
            data.get('Technician Name', pd.Series()).tolist() +
            data.get('Caller Name', pd.Series()).tolist()
        ))
        if persons_options:
            persons_to_remove = st.multiselect(
                "Exclude Persons",
                persons_options
            )
            if persons_to_remove:
                mask_tech = data['Technician Name'].isin(persons_to_remove)
                mask_caller = data['Caller Name'].isin(persons_to_remove)
                data = data[~(mask_tech | mask_caller)]

    # =====================================================
    # 3️⃣ ANONYMIZATION
    # =====================================================
    st.markdown("## Data Anonymization")
    sensitive_columns = st.multiselect(
        "Select columns to anonymize",
        options=data.columns
    )
    for col in sensitive_columns:
        data[col] = [f"{col.split('->')[0]} {i+1}" for i in range(len(data))]

    # =====================================================
    # 4️⃣ TIME FILTER
    # =====================================================
    st.markdown("## Time Period")
    if 'Start date' in data.columns:
        data['Start date'] = pd.to_datetime(data['Start date'], errors='coerce')
        data['Month'] = data['Start date'].dt.to_period('M').astype(str)
    else:
        data['Month'] = 'Unknown'

    all_months = sorted(data['Month'].dropna().unique(), reverse=True)
    months_to_compare = st.selectbox(
        "Select last N months",
        options=[1, 2, 3, 4, 6, 12],
        index=2
    )
    selected_months = all_months[:months_to_compare]
    data = data[data['Month'].isin(selected_months)]

    # =====================================================
    # 5️⃣ KPI CALCULATION
    # =====================================================
    data = compute_kpis(data)
    data['Duration (days)'] = pd.to_numeric(data.get('Duration (days)', 0), errors='coerce').fillna(0)

    monthly_summary = (
        data.groupby('Month')
        .agg({
            'Ref': 'count',                 # Total Tickets
            'Done Tasks': 'sum',            # Closed Tickets
            'Pending Tasks': 'sum',         # Pending Tickets
            'SLA TTO Done': 'sum',          # SLA TTO Met
            'SLA TTR Done': 'sum',          # SLA TTR Met
            'Duration (days)': 'mean'       # Avg resolution
        })
        .rename(columns={
            'Ref': 'Total Tickets', 
            'Done Tasks': 'Closed Tickets',
            'Pending Tasks': 'Pending Tickets',
            'Duration (days)': 'Avg Resolution Days'
        })
        .reset_index()
    )

    # =====================================================
    # SLA Violations Calculation
    # =====================================================
    monthly_summary['SLA TTO Violations'] = monthly_summary['Total Tickets'] - monthly_summary['SLA TTO Done']
    monthly_summary['SLA TTR Violations'] = monthly_summary['Total Tickets'] - monthly_summary['SLA TTR Done']
    monthly_summary['SLA Violations'] = ((monthly_summary['SLA TTO Violations'] + monthly_summary['SLA TTR Violations']) / 2).round(0)

    # Closure % = Closed / Total
    monthly_summary['Closure %'] = (monthly_summary['Closed Tickets'] / monthly_summary['Total Tickets'] * 100).round(1)

    # SLA % = compliance % based on done
    monthly_summary['SLA %'] = ((monthly_summary['SLA TTO Done'] + monthly_summary['SLA TTR Done']) 
                                / (2 * monthly_summary['Total Tickets']) * 100).round(1)
    monthly_summary['Avg Resolution Days'] = monthly_summary['Avg Resolution Days'].fillna(0)

    # =====================================================
    # 6️⃣ KPI CARDS
    # =====================================================
    st.markdown("## Key Metrics")
    total_tickets = int(monthly_summary['Total Tickets'].sum())
    total_closed = int(monthly_summary['Closed Tickets'].sum())
    total_pending = int(monthly_summary['Pending Tickets'].sum())
    total_violations = int(monthly_summary['SLA Violations'].sum())
    closure_rate = round(monthly_summary['Closure %'].mean(), 1)
    sla_rate = round(monthly_summary['SLA %'].mean(), 1)
    avg_resolution = round(monthly_summary['Avg Resolution Days'].mean(), 1)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: kpi_card("Total Tickets", total_tickets)
    with c2: kpi_card("Closed Tickets", total_closed, "#22C55E")
    with c3: kpi_card("Pending Tickets", total_pending, "#F59E0B")
    with c4: kpi_card("SLA Violations", total_violations, "#EF4444")
    with c5: kpi_card("Closure %", f"{closure_rate}%", "#0EA5A4")
    with c6: kpi_card("SLA Compliance %", f"{sla_rate}%", "#06B6D4")

    # =====================================================
    # 7️⃣ TOP 5 PERFORMERS
    # =====================================================
    def sla_color(val):
        if val >= 90: return "green"
        elif val >= 75: return "orange"
        else: return "red"

    def style_sla(df, column='SLA %'):
        return df.style.applymap(lambda x: f"color:{sla_color(x)}; font-weight:bold", subset=[column])

    # Technician
    if 'Technician Name' in data.columns:
        st.markdown("## Top 5 Performing Technicians")
        tech_summary = (
            data.groupby('Technician Name')
            .agg(Tickets=('Ref','count'), Done=('Done Tasks','sum'),
                 SLA_Done=('SLA TTO Done','sum'), SLA_TTR=('SLA TTR Done','sum'))
            .reset_index()
        )
        tech_summary['SLA %'] = ((tech_summary['SLA_Done'] + tech_summary['SLA_TTR']) / (tech_summary['Tickets']*2) * 100).round(1)
        top_techs = tech_summary.sort_values(by='SLA %', ascending=False).head(5)
        fig_tech = px.bar(top_techs, x='Technician Name', y='SLA %', text='SLA %', color='SLA %', color_continuous_scale='Tealgrn')
        st.plotly_chart(fig_tech, use_container_width=True, config={'displayModeBar': False})
        st.dataframe(style_sla(top_techs[['Technician Name','Tickets','Done','SLA %']]), use_container_width=True)

    # Caller
    if 'Caller Name' in data.columns:
        st.markdown("## Top 5 Performing Caller Agents")
        caller_summary = (
            data.groupby('Caller Name')
            .agg(Tickets=('Ref','count'), Done=('Done Tasks','sum'),
                 SLA_Done=('SLA TTO Done','sum'), SLA_TTR=('SLA TTR Done','sum'))
            .reset_index()
        )
        caller_summary['SLA %'] = ((caller_summary['SLA_Done'] + caller_summary['SLA_TTR']) / (caller_summary['Tickets']*2) * 100).round(1)
        top_callers = caller_summary.sort_values(by='SLA %', ascending=False).head(5)
        fig_callers = px.bar(top_callers, x='Caller Name', y='SLA %', text='SLA %', color='SLA %', color_continuous_scale='Tealgrn')
        st.plotly_chart(fig_callers, use_container_width=True, config={'displayModeBar': False})
        st.dataframe(style_sla(top_callers[['Caller Name','Tickets','Done','SLA %']]), use_container_width=True)

    # =====================================================
    # 8️⃣ MONTHLY KPI SUMMARY TABLE
    # =====================================================
    st.markdown("## Monthly KPI Summary")
    st.dataframe(monthly_summary[
        ['Month','Total Tickets','Closed Tickets','Pending Tickets',
         'SLA Violations','SLA TTO Violations','SLA TTR Violations',
         'Closure %','SLA %','Avg Resolution Days']
    ], use_container_width=True)

    # =====================================================
    # 9️⃣ TREND CHART
    # =====================================================
    st.markdown("## Monthly KPI Trend")
    monthly_summary_sorted = monthly_summary.sort_values('Month')
    fig = px.line(monthly_summary_sorted, x='Month', y=['Closure %','SLA %'], markers=True)
    fig.update_layout(title="Monthly KPI Trend", yaxis_title="%", xaxis_title="Month")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # =====================================================
    # 🔟 EXPORT
    # =====================================================
    st.markdown("## Export Reports")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, sheet_name='Processed_Data', index=False)
        monthly_summary.to_excel(writer, sheet_name='Monthly_Summary', index=False)
        if 'tech_summary' in locals(): tech_summary.to_excel(writer, sheet_name='Technician_Summary', index=False)
        if 'caller_summary' in locals(): caller_summary.to_excel(writer, sheet_name='Caller_Summary', index=False)
    excel_data = output.getvalue()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download Excel", excel_data, file_name="ticket_report.xlsx")
    with col2:
        prs = create_ppt({
            'Monthly KPI': monthly_summary,
            'Technician-wise KPI': tech_summary if 'tech_summary' in locals() else pd.DataFrame(),
            'Caller-wise KPI': caller_summary if 'caller_summary' in locals() else pd.DataFrame()
        })
        ppt_output = BytesIO()
        prs.save(ppt_output)
        ppt_output.seek(0)
        st.download_button("Download PowerPoint", ppt_output, file_name="ticket_report.pptx")
