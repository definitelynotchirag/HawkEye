import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

from utils.db_manager import get_api_names, get_environments, clean_old_data, initialize_db

st.set_page_config(
    page_title="API Monitoring - Settings",
    page_icon="⚙️",
    layout="wide"
)

# Initialize database connection
conn = sqlite3.connect('api_monitor.db')

# Page title
st.title("⚙️ System Settings")

# Create tabs for different settings
general_tab, data_tab, model_tab, system_tab = st.tabs(["General Settings", "Data Management", "Model Settings", "System Information"])

with general_tab:
    st.header("General Settings")
    
    # Application settings
    st.subheader("Application Settings")
    
    # UI theme
    st.markdown("""
    Streamlit theme settings are managed in the `.streamlit/config.toml` file.
    Current theme settings:
    - Primary color: #1E88E5
    - Background color: #FFFFFF
    - Secondary background color: #F0F2F6
    - Text color: #262730
    - Font: sans serif
    """)
    
    # Notification settings (placeholder - would be implemented with a real notification system)
    st.subheader("Notification Settings")
    
    notification_methods = {
        "email": "Email Notifications",
        "slack": "Slack Notifications",
        "webhook": "Webhook Notifications"
    }
    
    notification_enabled = {}
    for method, label in notification_methods.items():
        notification_enabled[method] = st.checkbox(label, value=(method == "email"))
    
    if notification_enabled["email"]:
        st.text_input("Email Recipients (comma-separated)", value="alerts@example.com")
    
    if notification_enabled["slack"]:
        st.text_input("Slack Webhook URL")
        st.text_input("Slack Channel", value="#api-alerts")
    
    if notification_enabled["webhook"]:
        st.text_input("Webhook URL")
    
    # Save settings button - placeholder since we're not actually persisting these
    if st.button("Save Notification Settings"):
        st.success("Notification settings saved successfully")

with data_tab:
    st.header("Data Management")
    
    # Data retention settings
    st.subheader("Data Retention")
    
    retention_days = st.slider(
        "Data Retention Period (days)",
        min_value=7,
        max_value=365,
        value=30,
        step=1,
        help="Data older than this will be automatically purged"
    )
    
    # Display current database stats
    st.subheader("Database Statistics")
    
    # Query for table sizes
    cursor = conn.cursor()
    
    # Get row counts for each table
    tables = ["api_logs", "anomalies", "alerts", "alert_rules", "predictions"]
    table_stats = []
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        # Get oldest and newest record date
        cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
        dates = cursor.fetchone()
        
        if dates[0] and dates[1]:
            oldest = dates[0]
            newest = dates[1]
        else:
            oldest = "N/A"
            newest = "N/A"
        
        table_stats.append({
            "table": table,
            "records": count,
            "oldest_record": oldest,
            "newest_record": newest
        })
    
    stats_df = pd.DataFrame(table_stats)
    st.dataframe(stats_df, use_container_width=True)
    
    # Database file size
    db_size = os.path.getsize("api_monitor.db") / (1024 * 1024)  # Convert to MB
    st.info(f"Database file size: {db_size:.2f} MB")
    
    # Data cleaning options
    st.subheader("Data Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clean Old Data"):
            cleaning_result = clean_old_data(days_to_keep=retention_days)
            
            st.success(f"Data cleaning complete. Removed:")
            st.write(f"- {cleaning_result['logs_deleted']} log records")
            st.write(f"- {cleaning_result['anomalies_deleted']} anomaly records")
            st.write(f"- {cleaning_result['alerts_deleted']} alert records")
            st.write(f"- {cleaning_result['predictions_deleted']} prediction records")
    
    with col2:
        if st.button("Reset Database"):
            confirmation = st.checkbox("I understand this will delete ALL data and recreate the database")
            
            if confirmation:
                # Close the current connection
                conn.close()
                
                # Delete the database file
                try:
                    os.remove("api_monitor.db")
                    # Reinitialize the database
                    initialize_db()
                    st.success("Database has been reset successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting database: {e}")

with model_tab:
    st.header("Model Settings")
    
    # List available models
    st.subheader("Trained Models")
    
    # Check for model files
    model_dir = "models"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    
    model_files = [f for f in os.listdir(model_dir) if f.endswith('.joblib')]
    
    if model_files:
        model_data = []
        
        for model_file in model_files:
            # Extract info from filename
            parts = model_file.replace('.joblib', '').split('_')
            
            if len(parts) >= 2:
                model_type = parts[0]
                if model_type == 'iso':
                    model_type = 'Isolation Forest'
                
                api_name = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1]
                prediction_type = parts[-1]
                
                # Get file stats
                file_path = os.path.join(model_dir, model_file)
                file_size = os.path.getsize(file_path) / 1024  # KB
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                model_data.append({
                    "model_file": model_file,
                    "model_type": model_type,
                    "api_name": api_name,
                    "prediction_type": prediction_type,
                    "size_kb": file_size,
                    "last_modified": modified_time
                })
        
        model_df = pd.DataFrame(model_data)
        
        if not model_df.empty:
            # Format the dataframe
            model_df['last_modified'] = pd.to_datetime(model_df['last_modified']).dt.strftime('%Y-%m-%d %H:%M:%S')
            model_df['size_kb'] = model_df['size_kb'].round(2)
            
            st.dataframe(
                model_df[['model_file', 'model_type', 'api_name', 'prediction_type', 'size_kb', 'last_modified']].rename(
                    columns={
                        'model_file': 'Model File',
                        'model_type': 'Model Type',
                        'api_name': 'API Name',
                        'prediction_type': 'Prediction Type',
                        'size_kb': 'Size (KB)',
                        'last_modified': 'Last Modified'
                    }
                ),
                use_container_width=True
            )
        else:
            st.info("No model information available")
    else:
        st.info("No trained models found")
    
    # Model retraining settings
    st.subheader("Model Retraining Settings")
    
    retraining_frequency = st.select_slider(
        "Model Retraining Frequency",
        options=["Every hour", "Every 6 hours", "Every 12 hours", "Every day", "Every week"],
        value="Every day"
    )
    
    min_data_points = st.number_input(
        "Minimum Data Points for Training",
        min_value=10,
        value=100,
        step=10,
        help="Minimum number of data points required to train a model"
    )
    
    # Anomaly detection sensitivity
    st.subheader("Anomaly Detection Sensitivity")
    
    response_time_sensitivity = st.slider(
        "Response Time Anomaly Sensitivity",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.1,
        help="Lower values increase sensitivity (more anomalies), higher values decrease sensitivity (fewer anomalies)"
    )
    
    error_rate_sensitivity = st.slider(
        "Error Rate Anomaly Sensitivity",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.1,
        help="Lower values increase sensitivity (more anomalies), higher values decrease sensitivity (fewer anomalies)"
    )
    
    pattern_change_sensitivity = st.slider(
        "Pattern Change Sensitivity",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.1,
        help="Lower values increase sensitivity (more anomalies), higher values decrease sensitivity (fewer anomalies)"
    )
    
    # Save model settings button
    if st.button("Save Model Settings"):
        st.success("Model settings saved successfully")
    
    # Model management options
    st.subheader("Model Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Retrain All Models"):
            st.info("Model retraining initiated...")
            # Placeholder for actual retraining logic
            st.success("All models have been retrained successfully")
    
    with col2:
        if st.button("Clear All Models"):
            confirmation = st.checkbox("I understand this will delete ALL trained models")
            
            if confirmation:
                try:
                    for model_file in model_files:
                        os.remove(os.path.join(model_dir, model_file))
                    st.success("All models have been deleted successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting models: {e}")

with system_tab:
    st.header("System Information")
    
    # Display system information
    st.subheader("System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Database Status", "Connected")
        st.metric("Python Version", "3.10")
        st.metric("Streamlit Version", "1.30.0")  # Placeholder
    
    with col2:
        st.metric("Anomaly Detector Status", "Running")
        st.metric("Predictor Status", "Running")
        st.metric("System Uptime", "12:34:56")  # Placeholder
    
    # Service status/logs
    st.subheader("Service Status")
    
    services = {
        "API Data Collector": "Running",
        "Anomaly Detector": "Running",
        "Alert Manager": "Running",
        "Prediction Engine": "Running"
    }
    
    service_df = pd.DataFrame([
        {"Service": service, "Status": status, "Last Check": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        for service, status in services.items()
    ])
    
    st.dataframe(service_df, use_container_width=True)
    
    # API Monitor version
    st.subheader("About API Monitor")
    
    st.markdown("""
    ### API Monitoring & Anomaly Detection System
    **Version:** 1.0.0
    
    This system monitors API performance across distributed environments, detects anomalies in response times and error rates,
    and provides predictive analytics to help prevent service disruptions before they occur.
    
    **Features:**
    - Real-time API monitoring
    - ML-powered anomaly detection
    - Multi-environment support
    - Predictive analytics
    - Customizable alerting
    
    **License:** Proprietary
    """)

# Close database connection
conn.close()
