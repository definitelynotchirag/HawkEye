import pandas as pd
import numpy as np
import json
import sqlite3
from datetime import datetime, timedelta
import re

def process_log_data(log_data, log_format="json"):
    """
    Process API log data from various formats into a standardized structure
    
    Args:
        log_data: The raw log data to process
        log_format: Format of the logs (json, csv, plain text)
        
    Returns:
        DataFrame with processed log data
    """
    if log_format == "json":
        return process_json_logs(log_data)
    elif log_format == "csv":
        return process_csv_logs(log_data)
    elif log_format == "text":
        return process_text_logs(log_data)
    else:
        raise ValueError(f"Unsupported log format: {log_format}")

def process_json_logs(json_logs):
    """Process JSON formatted logs"""
    if isinstance(json_logs, str):
        try:
            data = json.loads(json_logs)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
        except json.JSONDecodeError:
            # Handle multi-line JSON
            lines = json_logs.strip().split('\n')
            records = [json.loads(line) for line in lines]
            df = pd.DataFrame(records)
    else:
        df = pd.DataFrame(json_logs)
    
    # Standardize column names
    column_mapping = {
        'response_time': 'response_time',
        'responseTime': 'response_time',
        'resp_time': 'response_time',
        'status': 'status_code',
        'status_code': 'status_code',
        'statusCode': 'status_code',
        'api': 'api_name',
        'api_name': 'api_name',
        'apiName': 'api_name',
        'endpoint': 'api_name',
        'environment': 'environment',
        'env': 'environment',
        'timestamp': 'timestamp',
        'time': 'timestamp',
        'date': 'timestamp'
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # Ensure required columns exist
    required_columns = ['api_name', 'response_time', 'status_code', 'environment', 'timestamp']
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Convert timestamp to datetime if it's not already
    if 'timestamp' in df.columns and df['timestamp'].dtype != 'datetime64[ns]':
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Add error flag column (status code >= 400 is an error)
    if 'status_code' in df.columns:
        df['is_error'] = df['status_code'].apply(lambda x: 1 if x >= 400 else 0)
    
    return df

def process_csv_logs(csv_logs):
    """Process CSV formatted logs"""
    if isinstance(csv_logs, str):
        df = pd.read_csv(pd.StringIO(csv_logs))
    else:
        df = pd.read_csv(csv_logs)
    
    # Apply same standardization as JSON logs
    column_mapping = {
        'response_time': 'response_time',
        'responseTime': 'response_time',
        'resp_time': 'response_time',
        'status': 'status_code',
        'status_code': 'status_code',
        'statusCode': 'status_code',
        'api': 'api_name',
        'api_name': 'api_name',
        'apiName': 'api_name',
        'endpoint': 'api_name',
        'environment': 'environment',
        'env': 'environment',
        'timestamp': 'timestamp',
        'time': 'timestamp',
        'date': 'timestamp'
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # Ensure required columns exist
    required_columns = ['api_name', 'response_time', 'status_code', 'environment', 'timestamp']
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Convert timestamp to datetime if it's not already
    if 'timestamp' in df.columns and df['timestamp'].dtype != 'datetime64[ns]':
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Add error flag column (status code >= 400 is an error)
    if 'status_code' in df.columns:
        df['is_error'] = df['status_code'].apply(lambda x: 1 if x >= 400 else 0)
    
    return df

def process_text_logs(text_logs):
    """Process plain text logs using regex patterns"""
    # Define common log patterns
    patterns = [
        # Apache-like log pattern
        r'(?P<ip>[\d\.]+) .* \[(?P<timestamp>.*?)\] "(?P<method>\w+) (?P<api_name>[^\s"]+) HTTP/[\d\.]+?" (?P<status_code>\d+) (?P<bytes>\d+) "(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)" (?P<response_time>[\d\.]+)ms',
        
        # Simple API log pattern
        r'(?P<timestamp>[\d\-:T\.Z]+) \[(?P<environment>\w+)\] (?P<api_name>[^\s]+) - (?P<status_code>\d+) - (?P<response_time>[\d\.]+)ms',
        
        # JSON-like pattern in text
        r'timestamp=(?P<timestamp>[^,]+), api=(?P<api_name>[^,]+), status=(?P<status_code>\d+), response_time=(?P<response_time>[\d\.]+), environment=(?P<environment>[^,\s]+)'
    ]
    
    parsed_logs = []
    lines = text_logs.strip().split('\n')
    
    for line in lines:
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                log_entry = match.groupdict()
                parsed_logs.append(log_entry)
                break
    
    if not parsed_logs:
        raise ValueError("Could not parse text logs with available patterns")
    
    df = pd.DataFrame(parsed_logs)
    
    # Convert data types
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    if 'response_time' in df.columns:
        df['response_time'] = pd.to_numeric(df['response_time'], errors='coerce')
    
    if 'status_code' in df.columns:
        df['status_code'] = pd.to_numeric(df['status_code'], errors='coerce')
        df['is_error'] = df['status_code'].apply(lambda x: 1 if x >= 400 else 0)
    
    return df

def calculate_api_metrics(df, time_window=None):
    """
    Calculate key metrics for each API
    
    Args:
        df: DataFrame with processed log data
        time_window: Optional time window to filter data (e.g., '1h', '1d')
        
    Returns:
        DataFrame with API metrics
    """
    if time_window:
        # Filter data by time window
        cutoff_time = pd.Timestamp.now() - pd.Timedelta(time_window)
        df = df[df['timestamp'] >= cutoff_time]
    
    # Group by API and calculate metrics
    metrics = df.groupby('api_name').agg(
        total_calls=pd.NamedAgg(column='api_name', aggfunc='count'),
        avg_response_time=pd.NamedAgg(column='response_time', aggfunc='mean'),
        min_response_time=pd.NamedAgg(column='response_time', aggfunc='min'),
        max_response_time=pd.NamedAgg(column='response_time', aggfunc='max'),
        p95_response_time=pd.NamedAgg(column='response_time', aggfunc=lambda x: np.percentile(x, 95)),
        error_count=pd.NamedAgg(column='is_error', aggfunc='sum')
    ).reset_index()
    
    # Calculate error rate
    metrics['error_rate'] = (metrics['error_count'] / metrics['total_calls']) * 100
    
    return metrics

def save_logs_to_db(df, db_path='api_monitor.db'):
    """
    Save processed logs to SQLite database
    
    Args:
        df: DataFrame with processed log data
        db_path: Path to SQLite database
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(db_path)
        # Format datetime for SQLite
        df['timestamp'] = df['timestamp'].astype(str)
        df.to_sql('api_logs', conn, if_exists='append', index=False)
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving logs to database: {e}")
        return False

def get_log_data_by_environment(environment, time_window=None, db_path='api_monitor.db'):
    """
    Retrieve log data filtered by environment
    
    Args:
        environment: Environment to filter by (e.g., 'aws', 'on-premises')
        time_window: Optional time window to filter data (e.g., '1h', '1d')
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with filtered log data
    """
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM api_logs WHERE environment = ?"
    params = [environment]
    
    if time_window:
        cutoff_time = (datetime.now() - timedelta(hours=int(time_window[:-1]))).isoformat()
        query += " AND timestamp >= ?"
        params.append(cutoff_time)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Convert timestamp back to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def get_api_health_overview(db_path='api_monitor.db'):
    """
    Get overall health metrics for all APIs
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with overall health metrics
    """
    conn = sqlite3.connect(db_path)
    
    # Get data for the last 24 hours
    cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
    df = pd.read_sql_query(
        "SELECT * FROM api_logs WHERE timestamp >= ?", 
        conn, 
        params=[cutoff_time]
    )
    conn.close()
    
    if df.empty:
        return {
            'total_apis': 0,
            'total_calls': 0,
            'avg_response_time': 0,
            'error_rate': 0,
            'anomaly_count': 0
        }
    
    # Calculate metrics
    total_apis = df['api_name'].nunique()
    total_calls = len(df)
    avg_response_time = df['response_time'].mean()
    error_count = df['is_error'].sum()
    error_rate = (error_count / total_calls) * 100 if total_calls > 0 else 0
    
    # For anomaly count, we'd need to join with the anomalies table
    # This is a simplified version
    conn = sqlite3.connect(db_path)
    anomaly_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM anomalies WHERE detected_at >= ?", 
        conn, 
        params=[cutoff_time]
    ).iloc[0]['count']
    conn.close()
    
    return {
        'total_apis': total_apis,
        'total_calls': total_calls,
        'avg_response_time': round(avg_response_time, 2),
        'error_rate': round(error_rate, 2),
        'anomaly_count': anomaly_count
    }
