import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.predictor import APIPredictor, run_predictions
from utils.db_manager import get_api_names, get_environments, get_recent_predictions

st.set_page_config(
    page_title="API Monitoring - Predictions",
    page_icon="🔮",
    layout="wide"
)

# Initialize database connection
conn = sqlite3.connect('api_monitor.db')

# Page title
st.title("🔮 Predictive Analytics")

# Sidebar controls
with st.sidebar:
    st.header("Prediction Controls")
    
    # API selection
    api_options = ["All"] + get_api_names()
    selected_api = st.selectbox(
        "Select API",
        options=api_options,
        index=0
    )
    
    api_filter = None if selected_api == "All" else selected_api
    
    # Environment selection
    env_options = ["All"] + get_environments()
    selected_env = st.selectbox(
        "Select Environment",
        options=env_options,
        index=0
    )
    
    env_filter = None if selected_env == "All" else selected_env
    
    # Prediction time range
    hours_ahead = st.slider(
        "Prediction Hours Ahead",
        min_value=1,
        max_value=24,
        value=6,
        step=1
    )
    
    # Generate predictions button
    if st.button("Generate New Predictions"):
        with st.spinner("Generating predictions..."):
            # Handle "All" case by passing None
            apis = None if api_filter is None else [api_filter]
            envs = None if env_filter is None else [env_filter]
            
            prediction_results = run_predictions(api_names=apis, environments=envs)
            
            num_predictions = (
                len(prediction_results['response_time_predictions']) +
                len(prediction_results['error_rate_predictions']) +
                len(prediction_results['journey_health_predictions'])
            )
            
            st.success(f"Generated {num_predictions} predictions successfully!")

# Main content
st.header("API Performance Predictions")

# Get recent predictions
response_time_predictions = get_recent_predictions(
    prediction_type="response_time",
    api_name=api_filter,
    environment=env_filter
)

error_rate_predictions = get_recent_predictions(
    prediction_type="error_rate",
    api_name=api_filter,
    environment=env_filter
)

# Create tabs for different prediction types
resp_time_tab, error_rate_tab, journey_tab = st.tabs(["Response Time Predictions", "Error Rate Predictions", "API Journey Predictions"])

with resp_time_tab:
    st.subheader("Response Time Predictions")
    
    if not response_time_predictions.empty:
        # Group by API and environment
        grouped_predictions = response_time_predictions.groupby(['api_name', 'environment'])
        
        for (api_name, env), group in grouped_predictions:
            st.markdown(f"### {api_name} ({env})")
            
            # Sort by prediction time
            group = group.sort_values('prediction_for')
            
            # Create a line chart
            fig = px.line(
                group,
                x='prediction_for',
                y='predicted_value',
                labels={
                    'prediction_for': 'Time',
                    'predicted_value': 'Predicted Response Time (ms)'
                },
                title=f'Predicted Response Time for {api_name} ({env})'
            )
            
            # Add confidence interval (using confidence as a simple +/- percentage)
            y_upper = group['predicted_value'] * (1 + group['confidence'] * 0.2)
            y_lower = group['predicted_value'] * (1 - group['confidence'] * 0.2)
            
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([group['prediction_for'], group['prediction_for'][::-1]]),
                    y=np.concatenate([y_upper, y_lower[::-1]]),
                    fill='toself',
                    fillcolor='rgba(0,176,246,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Confidence Interval'
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the raw prediction data
            with st.expander("View Raw Prediction Data"):
                display_df = group[['prediction_for', 'predicted_value', 'confidence', 'predicted_at']].copy()
                display_df['prediction_for'] = pd.to_datetime(display_df['prediction_for']).dt.strftime('%Y-%m-%d %H:%M:%S')
                display_df['predicted_at'] = pd.to_datetime(display_df['predicted_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                display_df = display_df.rename(columns={
                    'prediction_for': 'Prediction For',
                    'predicted_value': 'Predicted Response Time (ms)',
                    'confidence': 'Confidence',
                    'predicted_at': 'Generated At'
                })
                
                st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No response time predictions available. Generate predictions using the sidebar controls.")

with error_rate_tab:
    st.subheader("Error Rate Predictions")
    
    if not error_rate_predictions.empty:
        # Group by API and environment
        grouped_predictions = error_rate_predictions.groupby(['api_name', 'environment'])
        
        for (api_name, env), group in grouped_predictions:
            st.markdown(f"### {api_name} ({env})")
            
            # Sort by prediction time
            group = group.sort_values('prediction_for')
            
            # Create a line chart
            fig = px.line(
                group,
                x='prediction_for',
                y='predicted_value',
                labels={
                    'prediction_for': 'Time',
                    'predicted_value': 'Predicted Error Rate (%)'
                },
                title=f'Predicted Error Rate for {api_name} ({env})'
            )
            
            # Add confidence interval
            y_upper = np.minimum(group['predicted_value'] * (1 + group['confidence'] * 0.3), 100)  # Cap at 100%
            y_lower = np.maximum(group['predicted_value'] * (1 - group['confidence'] * 0.3), 0)    # Min at 0%
            
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([group['prediction_for'], group['prediction_for'][::-1]]),
                    y=np.concatenate([y_upper, y_lower[::-1]]),
                    fill='toself',
                    fillcolor='rgba(255,0,0,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Confidence Interval'
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the raw prediction data
            with st.expander("View Raw Prediction Data"):
                display_df = group[['prediction_for', 'predicted_value', 'confidence', 'predicted_at']].copy()
                display_df['prediction_for'] = pd.to_datetime(display_df['prediction_for']).dt.strftime('%Y-%m-%d %H:%M:%S')
                display_df['predicted_at'] = pd.to_datetime(display_df['predicted_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                display_df = display_df.rename(columns={
                    'prediction_for': 'Prediction For',
                    'predicted_value': 'Predicted Error Rate (%)',
                    'confidence': 'Confidence',
                    'predicted_at': 'Generated At'
                })
                
                st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No error rate predictions available. Generate predictions using the sidebar controls.")

with journey_tab:
    st.subheader("API Journey Health Predictions")
    
    # Define some common API journeys
    predefined_journeys = {
        "User Authentication Flow": ["/api/auth/login", "/api/users"],
        "Order Processing Flow": ["/api/orders", "/api/payments", "/api/products"],
        "Product Search Flow": ["/api/search", "/api/products", "/api/recommendations"]
    }
    
    # Journey selection
    selected_journey = st.selectbox(
        "Select API Journey",
        options=list(predefined_journeys.keys())
    )
    
    journey_apis = predefined_journeys[selected_journey]
    
    # Show the APIs in the journey
    st.markdown(f"**Journey APIs:** {', '.join(journey_apis)}")
    
    # Environment for journey
    journey_env = st.selectbox(
        "Select Environment for Journey",
        options=get_environments()
    )
    
    # Button to predict journey health
    if st.button("Predict Journey Health"):
        with st.spinner("Analyzing journey health..."):
            predictor = APIPredictor()
            journey_result = predictor.predict_journey_health(journey_apis, journey_env, hours_ahead=hours_ahead)
            
            if journey_result['status'] == 'success':
                # Extract predictions
                journey_predictions = journey_result['predictions']
                
                # Convert to DataFrame
                journey_df = pd.DataFrame(journey_predictions)
                journey_df['prediction_for'] = pd.to_datetime(journey_df['prediction_for'])
                
                # Create health status plot
                fig1 = px.line(
                    journey_df,
                    x='prediction_for',
                    y='health_score',
                    labels={
                        'prediction_for': 'Time',
                        'health_score': 'Health Score (lower is better)'
                    },
                    title=f'Predicted Health Score for {selected_journey}'
                )
                
                # Add color based on health status
                colors = journey_df['health_status'].map({
                    'Excellent': 'green',
                    'Good': 'blue',
                    'Fair': 'orange',
                    'Poor': 'red'
                })
                
                fig1.update_traces(marker=dict(color=colors))
                st.plotly_chart(fig1, use_container_width=True)
                
                # Create component charts
                fig2 = go.Figure()
                
                # Add response time line
                fig2.add_trace(go.Scatter(
                    x=journey_df['prediction_for'],
                    y=journey_df['total_response_time'],
                    mode='lines+markers',
                    name='Total Response Time (ms)'
                ))
                
                # Add error rate line (secondary y-axis)
                fig2.add_trace(go.Scatter(
                    x=journey_df['prediction_for'],
                    y=journey_df['max_error_rate'],
                    mode='lines+markers',
                    name='Max Error Rate (%)',
                    yaxis='y2'
                ))
                
                # Update layout for dual y-axis
                fig2.update_layout(
                    title=f'Component Metrics for {selected_journey}',
                    xaxis=dict(title='Time'),
                    yaxis=dict(
                        title='Total Response Time (ms)',
                        side='left'
                    ),
                    yaxis2=dict(
                        title='Max Error Rate (%)',
                        side='right',
                        overlaying='y',
                        range=[0, max(journey_df['max_error_rate']) * 1.2]
                    ),
                    legend=dict(x=0.01, y=0.99),
                    height=400
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Display prediction table
                st.subheader("Journey Health Predictions")
                
                # Format DataFrame for display
                display_df = journey_df.copy()
                display_df['prediction_for'] = display_df['prediction_for'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Add color coding to health status
                display_df['health_status'] = display_df['health_status'].apply(
                    lambda x: f"<span style='color: {'green' if x == 'Excellent' else 'blue' if x == 'Good' else 'orange' if x == 'Fair' else 'red'};'>{x}</span>"
                )
                
                # Display as HTML to preserve color formatting
                st.markdown(
                    display_df[['prediction_for', 'health_score', 'health_status', 'total_response_time', 'max_error_rate']].rename(
                        columns={
                            'prediction_for': 'Prediction For',
                            'health_score': 'Health Score',
                            'health_status': 'Health Status',
                            'total_response_time': 'Total Response Time (ms)',
                            'max_error_rate': 'Max Error Rate (%)'
                        }
                    ).to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )
            else:
                st.error(f"Failed to predict journey health: {journey_result['message']}")
    else:
        st.info("Click 'Predict Journey Health' to analyze the selected journey")

# Prediction accuracy section
st.header("Prediction Accuracy Analysis")

with st.expander("View Prediction Accuracy"):
    st.markdown("""
    This section compares past predictions with actual measured values to assess prediction accuracy.
    """)
    
    # Time range for accuracy analysis
    accuracy_days = st.slider(
        "Days to analyze",
        min_value=1,
        max_value=30,
        value=7,
        step=1
    )
    
    # Get historical predictions for selected API
    if api_filter:
        with st.spinner("Analyzing prediction accuracy..."):
            # Query for predictions made in the past
            past_predictions_query = """
            SELECT 
                api_name, 
                environment,
                prediction_type,
                predicted_value,
                prediction_for
            FROM predictions
            WHERE api_name = ? AND predicted_at >= ? AND prediction_for < ?
            """
            
            cutoff_date = (datetime.now() - timedelta(days=accuracy_days)).isoformat()
            now = datetime.now().isoformat()
            
            past_predictions = pd.read_sql_query(
                past_predictions_query,
                conn,
                params=[api_filter, cutoff_date, now]
            )
            
            if not past_predictions.empty:
                # Convert timestamps to datetime
                past_predictions['prediction_for'] = pd.to_datetime(past_predictions['prediction_for'])
                
                # Get actual measurements from logs
                actual_data_query = """
                SELECT 
                    timestamp,
                    AVG(response_time) as actual_response_time,
                    SUM(is_error) * 100.0 / COUNT(*) as actual_error_rate
                FROM api_logs
                WHERE api_name = ? AND timestamp >= ?
                GROUP BY strftime('%Y-%m-%d %H', timestamp)
                """
                
                actual_data = pd.read_sql_query(
                    actual_data_query,
                    conn,
                    params=[api_filter, cutoff_date]
                )
                
                if not actual_data.empty:
                    actual_data['timestamp'] = pd.to_datetime(actual_data['timestamp'])
                    
                    # Create separate dataframes for each prediction type
                    response_predictions = past_predictions[past_predictions['prediction_type'] == 'response_time']
                    error_predictions = past_predictions[past_predictions['prediction_type'] == 'error_rate']
                    
                    # Process response time predictions
                    if not response_predictions.empty:
                        # Round prediction times to the hour for joining
                        response_predictions['hour'] = response_predictions['prediction_for'].dt.floor('H')
                        actual_data['hour'] = actual_data['timestamp'].dt.floor('H')
                        
                        # Join predictions with actual data
                        merged_data = pd.merge(
                            response_predictions,
                            actual_data,
                            left_on='hour',
                            right_on='hour',
                            how='inner'
                        )
                        
                        if not merged_data.empty:
                            # Calculate prediction error
                            merged_data['prediction_error'] = abs(merged_data['predicted_value'] - merged_data['actual_response_time'])
                            merged_data['error_percentage'] = (merged_data['prediction_error'] / merged_data['actual_response_time']) * 100
                            
                            # Create accuracy visualization
                            st.subheader("Response Time Prediction Accuracy")
                            
                            fig = go.Figure()
                            
                            # Add predicted values
                            fig.add_trace(go.Scatter(
                                x=merged_data['hour'],
                                y=merged_data['predicted_value'],
                                mode='lines+markers',
                                name='Predicted Response Time',
                                line=dict(color='blue')
                            ))
                            
                            # Add actual values
                            fig.add_trace(go.Scatter(
                                x=merged_data['hour'],
                                y=merged_data['actual_response_time'],
                                mode='lines+markers',
                                name='Actual Response Time',
                                line=dict(color='green')
                            ))
                            
                            fig.update_layout(
                                title=f'Response Time Prediction Accuracy for {api_filter}',
                                xaxis_title='Time',
                                yaxis_title='Response Time (ms)',
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Display accuracy metrics
                            avg_error = merged_data['error_percentage'].mean()
                            max_error = merged_data['error_percentage'].max()
                            
                            st.metric("Average Prediction Error", f"{avg_error:.2f}%")
                            st.metric("Maximum Prediction Error", f"{max_error:.2f}%")
                        else:
                            st.info("No matching data points found for accuracy analysis")
                    else:
                        st.info("No response time predictions available for accuracy analysis")
                    
                    # Process error rate predictions
                    if not error_predictions.empty:
                        # Similar process for error rate predictions
                        error_predictions['hour'] = error_predictions['prediction_for'].dt.floor('H')
                        
                        # Join predictions with actual data
                        merged_data = pd.merge(
                            error_predictions,
                            actual_data,
                            left_on='hour',
                            right_on='hour',
                            how='inner'
                        )
                        
                        if not merged_data.empty:
                            # Calculate prediction error
                            merged_data['prediction_error'] = abs(merged_data['predicted_value'] - merged_data['actual_error_rate'])
                            merged_data['error_percentage'] = merged_data['prediction_error'] 
                            
                            # Create accuracy visualization
                            st.subheader("Error Rate Prediction Accuracy")
                            
                            fig = go.Figure()
                            
                            # Add predicted values
                            fig.add_trace(go.Scatter(
                                x=merged_data['hour'],
                                y=merged_data['predicted_value'],
                                mode='lines+markers',
                                name='Predicted Error Rate',
                                line=dict(color='red')
                            ))
                            
                            # Add actual values
                            fig.add_trace(go.Scatter(
                                x=merged_data['hour'],
                                y=merged_data['actual_error_rate'],
                                mode='lines+markers',
                                name='Actual Error Rate',
                                line=dict(color='orange')
                            ))
                            
                            fig.update_layout(
                                title=f'Error Rate Prediction Accuracy for {api_filter}',
                                xaxis_title='Time',
                                yaxis_title='Error Rate (%)',
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Display accuracy metrics
                            avg_error = merged_data['error_percentage'].mean()
                            max_error = merged_data['error_percentage'].max()
                            
                            st.metric("Average Prediction Error", f"{avg_error:.2f} percentage points")
                            st.metric("Maximum Prediction Error", f"{max_error:.2f} percentage points")
                        else:
                            st.info("No matching data points found for error rate accuracy analysis")
                    else:
                        st.info("No error rate predictions available for accuracy analysis")
                else:
                    st.info("No actual data available for comparison")
            else:
                st.info("No past predictions available for accuracy analysis")
    else:
        st.info("Select a specific API to view prediction accuracy")

# Close database connection
conn.close()
