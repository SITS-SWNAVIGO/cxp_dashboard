# src/charts.py
import streamlit as st
import pandas as pd

def display_summary(df, title):
    st.write(f"### {title}")
    st.dataframe(df)
