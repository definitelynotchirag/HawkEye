import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.anomaly_detector import AnomalyDetector, run_anomaly_detection
from utils.db_manager import get_api_names, get_environments

st.set_page_config(
    page_title="API Monitoring - Anomaly Detection",
    page_icon="🚨",
    layout="wide"
)

# Initialize database connection
conn = sqlite3.connect('api_monitor.db')

# Page title
st.title("🚨 Anomaly Detection")

# Sidebar controls
with st.sidebar:
    st.header("Anomaly Detection Controls")
    
    sensitivity = st.slider(
        "Detection Sensitivity",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.1,
        help="Lower values increase sensitivity (more anomalies), higher values decrease sensitivity (fewer anomalies)"
    )
    
    time_range = st.select_slider(
        "Analysis Time Range",
        options=["Last hour", "Last 6 hours", "Last 24 hours", "Last 7 days"],
        value="Last 24 hours"
    )
    
    # Convert time range to hours for filtering
    time_range_hours = {
        "Last hour": 1,
        "Last 6 hours": 6,
        "Last 24 hours": 24,
        "Last 7 days": 24 * 7
    }[time_range]
    
    st.divider()
    
    # Filter controls
    st.header("Filters")
    
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
    
    # Anomaly type filter
    anomaly_types = ["All", "response_time", "error_rate", "pattern_change"]
    selected_types = st.multiselect(
        "Anomaly Types",
        options=anomaly_types,
        default=["All"]
    )
    
    if "All" in selected_types:
        type_filter = ["response_time", "error_rate", "pattern_change"]
    else:
        type_filter = selected_types
    
    # Run detection button
    if st.button("Run Detection Now"):
        with st.spinner("Running anomaly detection..."):
            detection_results = run_anomaly_detection(sensitivity=sensitivity)
            st.success(f"Detection complete! Found {detection_results['total_anomalies']} anomalies.")

# Main content - Anomaly Overview
st.header("Anomaly Overview")

# Get anomaly stats
anomaly_stats_query = """
SELECT 
    anomaly_type,
    COUNT(*) as count,
    SUM(CASE WHEN is_acknowledged = 1 THEN 1 ELSE 0 END) as acknowledged
FROM anomalies
WHERE detected_at >= ?
GROUP BY anomaly_type
"""

cutoff_time = (datetime.now() - timedelta(hours=time_range_hours)).isoformat()
anomaly_stats = pd.read_sql_query(anomaly_stats_query, conn, params=[cutoff_time])

# Display anomaly stats
if not anomaly_stats.empty:
    col1, col2, col3 = st.columns(3)
    
    total_anomalies = anomaly_stats['count'].sum()
    acknowledged = anomaly_stats['acknowledged'].sum()
    unacknowledged = total_anomalies - acknowledged
    
    with col1:
        st.metric(
            label="Total Anomalies",
            value=total_anomalies
        )
    
    with col2:
        st.metric(
            label="Acknowledged",
            value=acknowledged
        )
    
    with col3:
        st.metric(
            label="Unacknowledged",
            value=unacknowledged
        )
    
    # Anomaly distribution pie chart
    fig = px.pie(
        anomaly_stats, 
        values='count', 
        names='anomaly_type',
        title='Anomaly Distribution by Type',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No anomalies detected in the selected time range")

# Anomaly list
st.header("Detected Anomalies")

# Build query with filters
query = """
SELECT 
    id,
    api_name,
    environment,
    anomaly_type,
    anomaly_value,
    anomaly_score,
    detected_at,
    is_acknowledged
FROM anomalies
WHERE detected_at >= ?
"""

params = [cutoff_time]

if env_filter and "All" not in selected_env:
    placeholders = ", ".join(["?"] * len(env_filter))
    query += f" AND environment IN ({placeholders})"
    params.extend(env_filter)

if api_filter and "All" not in selected_apis:
    placeholders = ", ".join(["?"] * len(api_filter))
    query += f" AND api_name IN ({placeholders})"
    params.extend(api_filter)

if type_filter and "All" not in selected_types:
    placeholders = ", ".join(["?"] * len(type_filter))
    query += f" AND anomaly_type IN ({placeholders})"
    params.extend(type_filter)

query += " ORDER BY detected_at DESC"

anomalies = pd.read_sql_query(query, conn, params=params)

if not anomalies.empty:
    # Format data for display
    anomalies['detected_at'] = pd.to_datetime(anomalies['detected_at'])
    anomalies['Detected'] = anomalies['detected_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
    anomalies['Status'] = anomalies['is_acknowledged'].apply(lambda x: '✅ Acknowledged' if x == 1 else '⚠️ Unacknowledged')
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["List View", "Timeline View"])
    
    with tab1:
        # Convert anomaly type to more readable format
        anomalies['Type'] = anomalies['anomaly_type'].apply(lambda x: {
            'response_time': 'Response Time',
            'error_rate': 'Error Rate',
            'pattern_change': 'Pattern Change'
        }.get(x, x))
        
        # Prepare display columns
        display_df = anomalies[['api_name', 'environment', 'Type', 'anomaly_value', 'Detected', 'Status']]
        display_df = display_df.rename(columns={
            'api_name': 'API',
            'environment': 'Environment',
            'anomaly_value': 'Value'
        })
        
        st.dataframe(display_df, use_container_width=True)
        
        # Acknowledgement section
        st.subheader("Acknowledge Anomalies")
        
        unack_anomalies = anomalies[anomalies['is_acknowledged'] == 0]
        if not unack_anomalies.empty:
            selected_anomaly = st.selectbox(
                "Select anomaly to acknowledge",
                unack_anomalies.apply(
                    lambda x: f"ID: {x['id']} - {x['api_name']} ({x['environment']}) - {x['anomaly_type']} - {x['Detected']}", 
                    axis=1
                )
            )
            
            anomaly_id = int(selected_anomaly.split(' - ')[0].replace('ID: ', ''))
            
            if st.button("Acknowledge Selected Anomaly"):
                detector = AnomalyDetector()
                success = detector.acknowledge_anomaly(anomaly_id)
                
                if success:
                    st.success(f"Anomaly ID {anomaly_id} has been acknowledged")
                    st.rerun()
                else:
                    st.error("Failed to acknowledge anomaly")
        else:
            st.info("No unacknowledged anomalies")
    
    with tab2:
        # Timeline view
        fig = px.scatter(
            anomalies,
            x='detected_at',
            y='api_name',
            color='anomaly_type',
            size='anomaly_score',
            hover_name='api_name',
            hover_data={
                'detected_at': True,
                'anomaly_type': True,
                'anomaly_value': True,
                'environment': True,
                'anomaly_score': ':.2f',
                'is_acknowledged': False,
                'Status': True
            },
            labels={
                'detected_at': 'Time',
                'api_name': 'API',
                'anomaly_type': 'Anomaly Type'
            },
            title='Anomaly Timeline'
        )
        
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        # Group by API and anomaly type
        heatmap_data = anomalies.groupby(['api_name', 'anomaly_type']).size().reset_index(name='count')
        heatmap_pivot = heatmap_data.pivot(index='api_name', columns='anomaly_type', values='count').fillna(0)
        
        fig = px.imshow(
            heatmap_pivot,
            labels=dict(x="Anomaly Type", y="API", color="Count"),
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            color_continuous_scale="YlOrRd",
            title="Anomaly Heatmap by API and Type"
        )
        
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No anomalies found matching the selected filters")

# Anomaly investigation
st.header("Anomaly Investigation")

# Let user select an anomaly to investigate
if not anomalies.empty:
    selected_anomaly_id = st.selectbox(
        "Select an anomaly to investigate",
        anomalies.apply(
            lambda x: f"ID: {x['id']} - {x['api_name']} ({x['environment']}) - {x['anomaly_type']} - {x['Detected']}", 
            axis=1
        )
    )
    
    anomaly_id = int(selected_anomaly_id.split(' - ')[0].replace('ID: ', ''))
    selected_anomaly = anomalies[anomalies['id'] == anomaly_id].iloc[0]
    
    # Display anomaly details
    st.subheader("Anomaly Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API", selected_anomaly['api_name'])
    
    with col2:
        st.metric("Environment", selected_anomaly['environment'])
    
    with col3:
        st.metric("Anomaly Type", selected_anomaly['anomaly_type'])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Anomaly Value", f"{selected_anomaly['anomaly_value']:.2f}")
    
    with col2:
        st.metric("Anomaly Score", f"{selected_anomaly['anomaly_score']:.2f}")
    
    with col3:
        st.metric("Status", "Acknowledged" if selected_anomaly['is_acknowledged'] == 1 else "Unacknowledged")
    
    # Get surrounding data for context
    anomaly_time = pd.to_datetime(selected_anomaly['detected_at'])
    start_time = (anomaly_time - timedelta(hours=2)).isoformat()
    end_time = (anomaly_time + timedelta(hours=2)).isoformat()
    
    context_query = """
    SELECT 
        timestamp,
        response_time,
        status_code,
        is_error
    FROM api_logs
    WHERE api_name = ? AND environment = ? AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp
    """
    
    context_data = pd.read_sql_query(
        context_query, 
        conn, 
        params=[
            selected_anomaly['api_name'],
            selected_anomaly['environment'],
            start_time,
            end_time
        ]
    )
    
    if not context_data.empty:
        context_data['timestamp'] = pd.to_datetime(context_data['timestamp'])
        
        # Create visualizations based on anomaly type
        if selected_anomaly['anomaly_type'] == 'response_time':
            st.subheader("Response Time Context")
            
            fig = go.Figure()
            
            # Add response time line
            fig.add_trace(go.Scatter(
                x=context_data['timestamp'],
                y=context_data['response_time'],
                mode='lines',
                name='Response Time (ms)'
            ))
            
            # Add vertical line at anomaly time
            fig.add_shape(
                type='line',
                x0=anomaly_time,
                x1=anomaly_time,
                y0=0,
                y1=1,
                yref='paper',
                line=dict(
                    color='red',
                    width=2,
                    dash='dash'
                )
            )
            
            # Add annotation for the line
            fig.add_annotation(
                x=anomaly_time,
                y=1,
                yref='paper',
                text="Anomaly Detected",
                showarrow=False,
                xanchor='right',
                yanchor='top'
            )
            
            fig.update_layout(
                title="Response Time Around Anomaly",
                xaxis_title="Time",
                yaxis_title="Response Time (ms)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        elif selected_anomaly['anomaly_type'] == 'error_rate':
            st.subheader("Error Rate Context")
            
            # Calculate error rate in 5-minute buckets
            context_data['time_bucket'] = context_data['timestamp'].dt.floor('5min')
            error_buckets = context_data.groupby('time_bucket').agg(
                error_count=('is_error', 'sum'),
                total=('is_error', 'count')
            ).reset_index()
            
            error_buckets['error_rate'] = (error_buckets['error_count'] / error_buckets['total']) * 100
            
            fig = go.Figure()
            
            # Add error rate line
            fig.add_trace(go.Bar(
                x=error_buckets['time_bucket'],
                y=error_buckets['error_rate'],
                name='Error Rate (%)'
            ))
            
            # Add vertical line at anomaly time
            fig.add_shape(
                type='line',
                x0=anomaly_time,
                x1=anomaly_time,
                y0=0,
                y1=1,
                yref='paper',
                line=dict(
                    color='red',
                    width=2,
                    dash='dash'
                )
            )
            
            # Add annotation for the line
            fig.add_annotation(
                x=anomaly_time,
                y=1,
                yref='paper',
                text="Anomaly Detected",
                showarrow=False,
                xanchor='right',
                yanchor='top'
            )
            
            fig.update_layout(
                title="Error Rate Around Anomaly",
                xaxis_title="Time",
                yaxis_title="Error Rate (%)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Show raw data around anomaly
        with st.expander("View Raw Data"):
            st.dataframe(context_data, use_container_width=True)
    else:
        st.info("No context data available for this anomaly")
else:
    st.info("No anomalies available to investigate")

# Close database connection
conn.close()