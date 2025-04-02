import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
from utils.db_manager import initialize_db
from utils.api_simulator import simulate_api_calls
from utils.data_processor import process_log_data

# Set up page configuration
st.set_page_config(page_title="API Monitoring & Anomaly Detection",
                   page_icon="🔍",
                   layout="wide")

# Initialize database if it doesn't exist
initialize_db()

# Main page header
st.title("🔍 API Monitoring & Anomaly Detection System")

# Introduction section
st.markdown("""
This AI-powered system monitors API performance across distributed environments, 
detects anomalies in response times and error rates, and provides predictive analytics 
to help prevent service disruptions before they occur.
""")

# Dashboard overview
st.header("System Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="APIs Monitored", value="28")

with col2:
    st.metric(label="Anomalies (Last 24h)", value="7", delta="3")

with col3:
    st.metric(label="Overall Health", value="94%", delta="-2%")

# Quick stats in expandable section
with st.expander("Quick Stats"):
    # Create three columns for metrics
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

    with stat_col1:
        st.metric(label="Avg Response Time", value="187ms", delta="-12ms")

    with stat_col2:
        st.metric(label="Error Rate",
                  value="0.4%",
                  delta="0.1%",
                  delta_color="inverse")

    with stat_col3:
        st.metric(label="Total API Calls", value="2.8M")

    with stat_col4:
        st.metric(label="Predicted Issues", value="3", delta="1")

# Demo data generator sidebar
with st.sidebar:
    st.header("Demo Controls")

    if st.button("Generate Demo Data"):
        with st.spinner("Generating sample API log data..."):
            simulate_api_calls(100)
            st.success("Demo data has been generated!")

    # Environment filter
    st.subheader("Environment Filter")
    env_options = st.multiselect(
        "Select environments to view",
        ["On-premises", "AWS Cloud", "Azure Cloud", "Google Cloud"],
        default=["On-premises", "AWS Cloud", "Azure Cloud", "Google Cloud"])

    # Time range selector
    st.subheader("Time Range")
    time_range = st.select_slider("Select time range",
                                  options=[
                                      "Last hour", "Last 6 hours",
                                      "Last 24 hours", "Last 7 days",
                                      "Last 30 days"
                                  ],
                                  value="Last 24 hours")

    # Anomaly threshold adjustment
    st.subheader("Sensitivity Settings")
    anomaly_threshold = st.slider(
        "Anomaly Detection Threshold",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.1,
        help=
        "Lower values increase sensitivity (more alerts), higher values decrease sensitivity (fewer alerts)"
    )

# Recent activity section
st.header("Recent Activity")

# Connect to the database and fetch recent logs
conn = sqlite3.connect('api_monitor.db')
try:
    recent_logs = pd.read_sql_query(
        "SELECT * FROM api_logs ORDER BY timestamp DESC LIMIT 10", conn)
    st.dataframe(recent_logs, use_container_width=True)
except Exception as e:
    st.info(
        "No recent activity data available. Generate demo data to see activity."
    )

conn.close()

# Feature navigation cards
st.header("Navigation")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📊 Dashboard
    View real-time metrics and performance data for all monitored APIs.
    
    [Go to Dashboard](/dashboard)
    """)

with col2:
    st.markdown("""
    ### 🚨 Anomaly Detection
    Explore detected anomalies and investigate performance issues.
    
    [View Anomalies](/anomaly_detection)
    """)

with col3:
    st.markdown("""
    ### ⚠️ Alerts
    Configure and manage alert settings and notifications.
    
    [Manage Alerts](/alerts)
    """)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🔮 Predictive Analytics
    See forecasts of potential API issues before they occur.
    
    [View Predictions](/prediction)
    """)

with col2:
    st.markdown("""
    ### ⚙️ Settings
    Configure system settings and thresholds.
    
    [Open Settings](/settings)
    """)

# Footer
st.markdown("---")
st.markdown("© 2023 API Monitoring & Anomaly Detection System")
