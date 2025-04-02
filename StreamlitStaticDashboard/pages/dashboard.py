import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

from utils.data_processor import get_api_health_overview
from utils.db_manager import get_api_names, get_environments

st.set_page_config(
    page_title="API Monitoring - Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize database connection
conn = sqlite3.connect('api_monitor.db')

# Page title
st.title("📊 API Monitoring Dashboard")

# Time range selector in sidebar
with st.sidebar:
    st.header("Filters")
    
    time_range = st.select_slider(
        "Time Range",
        options=["Last hour", "Last 6 hours", "Last 24 hours", "Last 7 days", "Last 30 days"],
        value="Last 24 hours"
    )
    
    # Convert time range to hours for filtering
    time_range_hours = {
        "Last hour": 1,
        "Last 6 hours": 6,
        "Last 24 hours": 24,
        "Last 7 days": 24 * 7,
        "Last 30 days": 24 * 30
    }[time_range]
    
    # Environment filter
    environments = ["All"] + get_environments()
    selected_env = st.multiselect(
        "Environments",
        options=environments,
        default=["All"]
    )
    
    if "All" in selected_env:
        env_filter = get_environments()
    else:
        env_filter = selected_env
    
    # API filter
    apis = ["All"] + get_api_names()
    selected_apis = st.multiselect(
        "APIs",
        options=apis,
        default=["All"]
    )
    
    if "All" in selected_apis:
        api_filter = get_api_names()
    else:
        api_filter = selected_apis

# Health overview section
st.header("System Health Overview")

# Get overall health metrics
health_metrics = get_api_health_overview()

# Create health metrics in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="API Response Time",
        value=f"{health_metrics['avg_response_time']} ms",
        delta="-12 ms"
    )

with col2:
    st.metric(
        label="Error Rate",
        value=f"{health_metrics['error_rate']}%",
        delta="0.5%",
        delta_color="inverse"
    )

with col3:
    st.metric(
        label="Active Anomalies",
        value=health_metrics['anomaly_count'],
        delta="3"
    )

with col4:
    st.metric(
        label="APIs Monitored",
        value=health_metrics['total_apis']
    )

# Query for response time over time
cutoff_time = (datetime.now() - timedelta(hours=time_range_hours)).isoformat()

# Build query with filters
query_params = [cutoff_time]
env_condition = ""
api_condition = ""

if env_filter:
    placeholders = ", ".join(["?"] * len(env_filter))
    env_condition = f"AND environment IN ({placeholders})"
    query_params.extend(env_filter)

if api_filter:
    placeholders = ", ".join(["?"] * len(api_filter))
    api_condition = f"AND api_name IN ({placeholders})"
    query_params.extend(api_filter)

# Response time over time
st.subheader("Response Time Trends")

if env_filter and api_filter:
    response_time_query = f"""
    SELECT 
        strftime('%Y-%m-%d %H:%M', timestamp) as time_bucket,
        api_name,
        environment,
        AVG(response_time) as avg_response_time
    FROM api_logs
    WHERE timestamp >= ? {env_condition} {api_condition}
    GROUP BY time_bucket, api_name, environment
    ORDER BY time_bucket
    """
    
    response_time_df = pd.read_sql_query(response_time_query, conn, params=query_params)
    
    if not response_time_df.empty:
        response_time_df['time_bucket'] = pd.to_datetime(response_time_df['time_bucket'])
        
        fig = px.line(
            response_time_df, 
            x='time_bucket', 
            y='avg_response_time',
            color='api_name',
            facet_row='environment',
            labels={
                'time_bucket': 'Time',
                'avg_response_time': 'Response Time (ms)',
                'api_name': 'API'
            },
            title='Average Response Time by API and Environment'
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No response time data available for the selected filters")

# Error rate over time
st.subheader("Error Rate Trends")

if env_filter and api_filter:
    error_rate_query = f"""
    SELECT 
        strftime('%Y-%m-%d %H:%M', timestamp) as time_bucket,
        api_name,
        environment,
        SUM(is_error) as error_count,
        COUNT(*) as total_count
    FROM api_logs
    WHERE timestamp >= ? {env_condition} {api_condition}
    GROUP BY time_bucket, api_name, environment
    ORDER BY time_bucket
    """
    
    error_rate_df = pd.read_sql_query(error_rate_query, conn, params=query_params)
    
    if not error_rate_df.empty:
        error_rate_df['time_bucket'] = pd.to_datetime(error_rate_df['time_bucket'])
        error_rate_df['error_rate'] = (error_rate_df['error_count'] / error_rate_df['total_count']) * 100
        
        fig = px.line(
            error_rate_df, 
            x='time_bucket', 
            y='error_rate',
            color='api_name',
            facet_row='environment',
            labels={
                'time_bucket': 'Time',
                'error_rate': 'Error Rate (%)',
                'api_name': 'API'
            },
            title='Error Rate by API and Environment'
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No error rate data available for the selected filters")

# API Traffic Volume
st.subheader("API Traffic Volume")

if env_filter and api_filter:
    traffic_query = f"""
    SELECT 
        strftime('%Y-%m-%d %H', timestamp) as hour_bucket,
        api_name,
        COUNT(*) as call_count
    FROM api_logs
    WHERE timestamp >= ? {env_condition} {api_condition}
    GROUP BY hour_bucket, api_name
    ORDER BY hour_bucket
    """
    
    traffic_df = pd.read_sql_query(traffic_query, conn, params=query_params)
    
    if not traffic_df.empty:
        traffic_df['hour_bucket'] = pd.to_datetime(traffic_df['hour_bucket'])
        
        fig = px.bar(
            traffic_df, 
            x='hour_bucket', 
            y='call_count',
            color='api_name',
            labels={
                'hour_bucket': 'Time',
                'call_count': 'Number of Calls',
                'api_name': 'API'
            },
            title='API Call Volume Over Time'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No traffic data available for the selected filters")

# API Performance Comparison
st.subheader("API Performance Comparison")

if env_filter and api_filter:
    performance_query = f"""
    SELECT 
        api_name,
        environment,
        AVG(response_time) as avg_response_time,
        MIN(response_time) as min_response_time,
        MAX(response_time) as max_response_time,
        SUM(is_error) * 100.0 / COUNT(*) as error_rate,
        COUNT(*) as call_count
    FROM api_logs
    WHERE timestamp >= ? {env_condition} {api_condition}
    GROUP BY api_name, environment
    """
    
    performance_df = pd.read_sql_query(performance_query, conn, params=query_params)
    
    if not performance_df.empty:
        # Display as a table
        st.dataframe(
            performance_df.style.format({
                'avg_response_time': '{:.2f} ms',
                'min_response_time': '{:.2f} ms',
                'max_response_time': '{:.2f} ms',
                'error_rate': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        # Create a radar chart for API performance comparison
        performance_df['performance_score'] = (
            (1 - performance_df['avg_response_time'] / performance_df['avg_response_time'].max()) * 50 + 
            (1 - performance_df['error_rate'] / 100) * 50
        )
        
        fig = px.scatter(
            performance_df,
            x='avg_response_time',
            y='error_rate',
            size='call_count',
            color='api_name',
            hover_name='api_name',
            facet_col='environment',
            labels={
                'avg_response_time': 'Avg Response Time (ms)',
                'error_rate': 'Error Rate (%)',
                'call_count': 'Call Volume',
                'api_name': 'API'
            },
            title='API Performance Matrix'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No performance data available for the selected filters")

# Recent anomalies
st.subheader("Recent Anomalies")

anomalies_query = """
SELECT 
    anomalies.id,
    anomalies.api_name,
    anomalies.environment,
    anomalies.anomaly_type,
    anomalies.anomaly_value,
    anomalies.detected_at,
    anomalies.is_acknowledged
FROM anomalies
WHERE detected_at >= ?
ORDER BY detected_at DESC
LIMIT 10
"""

anomalies_df = pd.read_sql_query(anomalies_query, conn, params=[cutoff_time])

if not anomalies_df.empty:
    anomalies_df['detected_at'] = pd.to_datetime(anomalies_df['detected_at'])
    anomalies_df['acknowledged'] = anomalies_df['is_acknowledged'].apply(lambda x: 'Yes' if x == 1 else 'No')
    
    # Format for display
    display_df = anomalies_df[['api_name', 'environment', 'anomaly_type', 'anomaly_value', 'detected_at', 'acknowledged']]
    display_df = display_df.rename(columns={
        'api_name': 'API',
        'environment': 'Environment',
        'anomaly_type': 'Anomaly Type',
        'anomaly_value': 'Value',
        'detected_at': 'Detected At',
        'acknowledged': 'Acknowledged'
    })
    
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("No anomalies detected in the selected time range")

# Close the database connection
conn.close()
