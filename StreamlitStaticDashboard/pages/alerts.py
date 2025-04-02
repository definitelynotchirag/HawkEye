import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta

from utils.db_manager import get_api_names, get_environments, get_alert_rules, add_alert_rule, update_alert_rule, delete_alert_rule, get_active_alerts, resolve_alert

st.set_page_config(
    page_title="API Monitoring - Alerts",
    page_icon="⚠️",
    layout="wide"
)

# Initialize database connection
conn = sqlite3.connect('api_monitor.db')

# Page title
st.title("⚠️ Alerts Management")

# Create tabs for different alert functions
alert_tab, config_tab = st.tabs(["Active Alerts", "Alert Configuration"])

with alert_tab:
    st.header("Active Alerts")
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Environment filter
        environments = ["All"] + get_environments()
        selected_env = st.selectbox(
            "Filter by Environment",
            options=environments,
            index=0
        )
        
        env_filter = None if selected_env == "All" else selected_env
    
    with col2:
        # API filter
        apis = ["All"] + get_api_names()
        selected_api = st.selectbox(
            "Filter by API",
            options=apis,
            index=0
        )
        
        api_filter = None if selected_api == "All" else selected_api
    
    with col3:
        # Severity filter
        severity_options = ["All", "low", "medium", "high", "critical"]
        selected_severity = st.selectbox(
            "Filter by Severity",
            options=severity_options,
            index=0
        )
        
        severity_filter = None if selected_severity == "All" else selected_severity
    
    # Get active alerts
    alerts_df = get_active_alerts(api_name=api_filter, environment=env_filter)
    
    # Filter by severity if needed
    if severity_filter and not alerts_df.empty:
        alerts_df = alerts_df[alerts_df['severity'] == severity_filter]
    
    # Display active alerts
    if not alerts_df.empty:
        # Add severity color coding
        severity_colors = {
            'low': 'blue',
            'medium': 'orange',
            'high': 'red',
            'critical': 'purple'
        }
        
        alerts_df['severity_upper'] = alerts_df['severity'].str.upper()
        
        # Format created_at
        alerts_df['created_at_fmt'] = pd.to_datetime(alerts_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Display in a table
        st.dataframe(
            alerts_df[['id', 'api_name', 'environment', 'alert_type', 'alert_message', 'alert_value', 'created_at_fmt', 'severity_upper']].rename(
                columns={
                    'id': 'ID',
                    'api_name': 'API',
                    'environment': 'Environment',
                    'alert_type': 'Alert Type',
                    'alert_message': 'Message',
                    'alert_value': 'Value',
                    'created_at_fmt': 'Created At',
                    'severity_upper': 'Severity'
                }
            ),
            use_container_width=True
        )
        
        # Severity distribution
        st.subheader("Alert Severity Distribution")
        
        severity_count = alerts_df['severity'].value_counts().reset_index()
        severity_count.columns = ['severity', 'count']
        
        # Sort by severity level
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        severity_count['severity_order'] = severity_count['severity'].map(severity_order)
        severity_count = severity_count.sort_values('severity_order')
        
        fig = px.bar(
            severity_count,
            x='severity',
            y='count',
            color='severity',
            color_discrete_map={
                'low': 'green',
                'medium': 'orange',
                'high': 'red',
                'critical': 'purple'
            },
            labels={
                'severity': 'Severity',
                'count': 'Number of Alerts'
            },
            title='Alerts by Severity'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Allow resolving alerts
        st.subheader("Resolve Alerts")
        
        selected_alert = st.selectbox(
            "Select alert to resolve",
            alerts_df.apply(
                lambda x: f"ID: {x['id']} - {x['api_name']} ({x['environment']}) - {x['alert_type']} - {x['severity']}",
                axis=1
            )
        )
        
        alert_id = int(selected_alert.split(' - ')[0].replace('ID: ', ''))
        
        if st.button("Resolve Selected Alert"):
            success = resolve_alert(alert_id)
            
            if success:
                st.success(f"Alert ID {alert_id} has been resolved")
                st.rerun()
            else:
                st.error("Failed to resolve alert")
    else:
        st.info("No active alerts match the selected filters")
    
    # Alert history section
    with st.expander("View Alert History"):
        st.subheader("Alert History (Last 7 Days)")
        
        # Query for alert history
        history_query = """
        SELECT *
        FROM alerts
        WHERE is_active = 0 AND created_at >= ?
        ORDER BY created_at DESC
        """
        
        cutoff_time = (datetime.now() - timedelta(days=7)).isoformat()
        history_df = pd.read_sql_query(history_query, conn, params=[cutoff_time])
        
        if not history_df.empty:
            # Format created_at
            history_df['created_at'] = pd.to_datetime(history_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Display in a table
            st.dataframe(
                history_df[['id', 'api_name', 'environment', 'alert_type', 'alert_message', 'alert_value', 'created_at', 'severity']].rename(
                    columns={
                        'id': 'ID',
                        'api_name': 'API',
                        'environment': 'Environment',
                        'alert_type': 'Alert Type',
                        'alert_message': 'Message',
                        'alert_value': 'Value',
                        'created_at': 'Created At',
                        'severity': 'Severity'
                    }
                ),
                use_container_width=True
            )
        else:
            st.info("No alert history available for the last 7 days")

with config_tab:
    st.header("Alert Rules Configuration")
    
    # Display existing rules
    rules_df = get_alert_rules()
    
    if not rules_df.empty:
        # Format timestamps
        rules_df['created_at'] = pd.to_datetime(rules_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        rules_df['updated_at'] = pd.to_datetime(rules_df['updated_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Format active status
        rules_df['status'] = rules_df['is_active'].apply(lambda x: "✅ Active" if x == 1 else "❌ Inactive")
        
        # Display in a table
        st.dataframe(
            rules_df[['id', 'api_name', 'environment', 'rule_type', 'threshold', 'time_window', 'status', 'updated_at']].rename(
                columns={
                    'id': 'ID',
                    'api_name': 'API',
                    'environment': 'Environment',
                    'rule_type': 'Rule Type',
                    'threshold': 'Threshold',
                    'time_window': 'Time Window (min)',
                    'status': 'Status',
                    'updated_at': 'Last Updated'
                }
            ),
            use_container_width=True
        )
    else:
        st.info("No alert rules defined yet")
    
    # Manage rules
    st.subheader("Manage Alert Rules")
    
    # Create tabs for different rule management functions
    create_tab, edit_tab, delete_tab = st.tabs(["Create Rule", "Edit Rule", "Delete Rule"])
    
    with create_tab:
        st.subheader("Create New Alert Rule")
        
        # API selection
        api_list = ["*"] + get_api_names()
        new_api = st.selectbox(
            "Select API (or * for all)",
            options=api_list,
            index=0,
            key="new_api"
        )
        
        # Environment selection
        env_list = ["*"] + get_environments()
        new_env = st.selectbox(
            "Select Environment (or * for all)",
            options=env_list,
            index=0,
            key="new_env"
        )
        
        # Rule type
        rule_types = {
            "response_time": "Response Time Threshold (ms)",
            "error_rate": "Error Rate Threshold (%)",
            "pattern_change": "Pattern Change Threshold (%)"
        }
        
        new_rule_type = st.selectbox(
            "Rule Type",
            options=list(rule_types.keys()),
            format_func=lambda x: rule_types[x],
            key="new_rule_type"
        )
        
        # Threshold value
        default_thresholds = {
            "response_time": 500.0,
            "error_rate": 5.0,
            "pattern_change": 30.0
        }
        
        new_threshold = st.number_input(
            "Threshold Value",
            min_value=0.1,
            value=default_thresholds[new_rule_type],
            step=0.1,
            key="new_threshold"
        )
        
        # Time window
        default_windows = {
            "response_time": 15,
            "error_rate": 15,
            "pattern_change": 1440
        }
        
        new_window = st.number_input(
            "Time Window (minutes)",
            min_value=1,
            value=default_windows[new_rule_type],
            step=1,
            key="new_window"
        )
        
        # Create button
        if st.button("Create Alert Rule"):
            rule_id = add_alert_rule(new_api, new_env, new_rule_type, new_threshold, new_window)
            
            if rule_id:
                st.success(f"Alert rule created successfully with ID: {rule_id}")
                st.rerun()
            else:
                st.error("Failed to create alert rule")
    
    with edit_tab:
        st.subheader("Edit Existing Rule")
        
        if not rules_df.empty:
            # Select rule to edit
            edit_rule_id = st.selectbox(
                "Select rule to edit",
                options=rules_df['id'],
                format_func=lambda x: f"ID: {x} - {rules_df[rules_df['id'] == x]['api_name'].values[0]} - {rules_df[rules_df['id'] == x]['environment'].values[0]} - {rules_df[rules_df['id'] == x]['rule_type'].values[0]}"
            )
            
            # Get selected rule
            selected_rule = rules_df[rules_df['id'] == edit_rule_id].iloc[0]
            
            # Edit fields
            edit_threshold = st.number_input(
                "Threshold Value",
                min_value=0.1,
                value=float(selected_rule['threshold']),
                step=0.1,
                key="edit_threshold"
            )
            
            edit_window = st.number_input(
                "Time Window (minutes)",
                min_value=1,
                value=int(selected_rule['time_window']),
                step=1,
                key="edit_window"
            )
            
            edit_active = st.checkbox(
                "Active",
                value=bool(selected_rule['is_active']),
                key="edit_active"
            )
            
            # Update button
            if st.button("Update Rule"):
                success = update_alert_rule(
                    edit_rule_id,
                    threshold=edit_threshold,
                    time_window=edit_window,
                    is_active=edit_active
                )
                
                if success:
                    st.success(f"Rule ID {edit_rule_id} updated successfully")
                    st.rerun()
                else:
                    st.error("Failed to update rule")
        else:
            st.info("No rules available to edit")
    
    with delete_tab:
        st.subheader("Delete Rule")
        
        if not rules_df.empty:
            # Select rule to delete
            delete_rule_id = st.selectbox(
                "Select rule to delete",
                options=rules_df['id'],
                format_func=lambda x: f"ID: {x} - {rules_df[rules_df['id'] == x]['api_name'].values[0]} - {rules_df[rules_df['id'] == x]['environment'].values[0]} - {rules_df[rules_df['id'] == x]['rule_type'].values[0]}"
            )
            
            # Confirmation and delete button
            st.warning("⚠️ This action cannot be undone!")
            confirm = st.checkbox("I understand that deleting this rule cannot be undone")
            
            if confirm and st.button("Delete Rule"):
                success = delete_alert_rule(delete_rule_id)
                
                if success:
                    st.success(f"Rule ID {delete_rule_id} deleted successfully")
                    st.rerun()
                else:
                    st.error("Failed to delete rule")
        else:
            st.info("No rules available to delete")

# Alert testing section
with st.expander("Test Alert Generation"):
    st.subheader("Generate Test Alert")
    
    # API selection
    test_api = st.selectbox(
        "Select API",
        options=get_api_names(),
        key="test_api"
    )
    
    # Environment selection
    test_env = st.selectbox(
        "Select Environment",
        options=get_environments(),
        key="test_env"
    )
    
    # Alert type
    test_alert_types = {
        "response_time": "Response Time Alert",
        "error_rate": "Error Rate Alert",
        "pattern_change": "Pattern Change Alert"
    }
    
    test_alert_type = st.selectbox(
        "Alert Type",
        options=list(test_alert_types.keys()),
        format_func=lambda x: test_alert_types[x],
        key="test_alert_type"
    )
    
    # Severity
    test_severity = st.select_slider(
        "Alert Severity",
        options=["low", "medium", "high", "critical"],
        value="medium",
        key="test_severity"
    )
    
    # Generate button
    if st.button("Generate Test Alert"):
        # Import here to avoid circular imports
        from utils.db_manager import create_alert
        
        alert_messages = {
            "response_time": f"High response time detected for {test_api}",
            "error_rate": f"Elevated error rate detected for {test_api}",
            "pattern_change": f"Unusual pattern change detected for {test_api}"
        }
        
        alert_values = {
            "response_time": 500.0,
            "error_rate": 15.0,
            "pattern_change": 50.0
        }
        
        alert_id = create_alert(
            test_api,
            test_env,
            test_alert_type,
            alert_messages[test_alert_type],
            alert_values[test_alert_type],
            severity=test_severity
        )
        
        if alert_id:
            st.success(f"Test alert created successfully with ID: {alert_id}")
            st.rerun()
        else:
            st.error("Failed to create test alert")

# Close database connection
conn.close()
