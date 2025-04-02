import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

def initialize_db(db_path='api_monitor.db'):
    """
    Initialize database with required tables
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create API logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            response_time REAL,
            status_code INTEGER,
            is_error INTEGER,
            environment TEXT,
            timestamp TIMESTAMP,
            request_id TEXT,
            user_id TEXT,
            additional_info TEXT
        )
        ''')
        
        # Create anomalies table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            environment TEXT,
            anomaly_type TEXT,
            anomaly_value REAL,
            anomaly_score REAL,
            detected_at TIMESTAMP,
            is_acknowledged INTEGER DEFAULT 0
        )
        ''')
        
        # Create alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            environment TEXT,
            alert_type TEXT,
            alert_message TEXT,
            alert_value REAL,
            created_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            severity TEXT
        )
        ''')
        
        # Create alert rules table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            environment TEXT,
            rule_type TEXT,
            threshold REAL,
            time_window INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')
        
        # Create prediction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            environment TEXT,
            prediction_type TEXT,
            predicted_value REAL,
            confidence REAL,
            predicted_at TIMESTAMP,
            prediction_for TIMESTAMP
        )
        ''')
        
        # Add some default alert rules if table is empty
        cursor.execute('SELECT COUNT(*) FROM alert_rules')
        if cursor.fetchone()[0] == 0:
            default_rules = [
                ('*', '*', 'response_time', 500.0, 15, 1, datetime.now().isoformat(), datetime.now().isoformat()),
                ('*', '*', 'error_rate', 5.0, 15, 1, datetime.now().isoformat(), datetime.now().isoformat()),
                ('*', '*', 'pattern_change', 30.0, 1440, 1, datetime.now().isoformat(), datetime.now().isoformat())
            ]
            
            cursor.executemany('''
            INSERT INTO alert_rules (api_name, environment, rule_type, threshold, 
            time_window, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', default_rules)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def add_alert_rule(api_name, environment, rule_type, threshold, time_window, db_path='api_monitor.db'):
    """
    Add a new alert rule
    
    Args:
        api_name: API name ('*' for all APIs)
        environment: Environment ('*' for all environments)
        rule_type: Type of rule ('response_time', 'error_rate', 'pattern_change')
        threshold: Threshold value
        time_window: Time window in minutes
        db_path: Path to SQLite database
        
    Returns:
        ID of the new rule or None on failure
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
        INSERT INTO alert_rules (api_name, environment, rule_type, threshold, 
        time_window, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        ''', (api_name, environment, rule_type, threshold, time_window, now, now))
        
        rule_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return rule_id
    except Exception as e:
        print(f"Error adding alert rule: {e}")
        return None

def update_alert_rule(rule_id, threshold=None, time_window=None, is_active=None, db_path='api_monitor.db'):
    """
    Update an existing alert rule
    
    Args:
        rule_id: ID of the rule to update
        threshold: New threshold value (optional)
        time_window: New time window in minutes (optional)
        is_active: New active state (optional)
        db_path: Path to SQLite database
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if threshold is not None:
            updates.append("threshold = ?")
            params.append(threshold)
        
        if time_window is not None:
            updates.append("time_window = ?")
            params.append(time_window)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return True  # Nothing to update
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        # Add rule_id to params
        params.append(rule_id)
        
        cursor.execute(f'''
        UPDATE alert_rules 
        SET {', '.join(updates)}
        WHERE id = ?
        ''', params)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating alert rule: {e}")
        return False

def delete_alert_rule(rule_id, db_path='api_monitor.db'):
    """
    Delete an alert rule
    
    Args:
        rule_id: ID of the rule to delete
        db_path: Path to SQLite database
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting alert rule: {e}")
        return False

def get_alert_rules(api_name=None, environment=None, rule_type=None, db_path='api_monitor.db'):
    """
    Get alert rules with optional filters
    
    Args:
        api_name: Filter by API name (optional)
        environment: Filter by environment (optional)
        rule_type: Filter by rule type (optional)
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with alert rules
    """
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM alert_rules"
    conditions = []
    params = []
    
    if api_name:
        conditions.append("(api_name = ? OR api_name = '*')")
        params.append(api_name)
    
    if environment:
        conditions.append("(environment = ? OR environment = '*')")
        params.append(environment)
    
    if rule_type:
        conditions.append("rule_type = ?")
        params.append(rule_type)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Convert timestamps to datetime
    for col in ['created_at', 'updated_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    return df

def create_alert(api_name, environment, alert_type, alert_message, alert_value, severity='medium', db_path='api_monitor.db'):
    """
    Create a new alert
    
    Args:
        api_name: API name
        environment: Environment
        alert_type: Type of alert
        alert_message: Alert message
        alert_value: Value causing the alert
        severity: Alert severity ('low', 'medium', 'high', 'critical')
        db_path: Path to SQLite database
        
    Returns:
        ID of the new alert or None on failure
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if a similar alert is already active
        cursor.execute('''
        SELECT id FROM alerts 
        WHERE api_name = ? AND environment = ? AND alert_type = ? AND is_active = 1
        AND created_at >= ?
        ''', (
            api_name, 
            environment, 
            alert_type,
            (datetime.now() - timedelta(hours=1)).isoformat()  # Look for alerts in the last hour
        ))
        
        existing_alert = cursor.fetchone()
        
        if existing_alert:
            # Update existing alert
            cursor.execute('''
            UPDATE alerts
            SET alert_message = ?, alert_value = ?, severity = ?, created_at = ?
            WHERE id = ?
            ''', (
                alert_message,
                alert_value,
                severity,
                datetime.now().isoformat(),
                existing_alert[0]
            ))
            alert_id = existing_alert[0]
        else:
            # Create new alert
            cursor.execute('''
            INSERT INTO alerts (api_name, environment, alert_type, alert_message, 
            alert_value, created_at, is_active, severity)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ''', (
                api_name,
                environment,
                alert_type,
                alert_message,
                alert_value,
                datetime.now().isoformat(),
                severity
            ))
            alert_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return alert_id
    except Exception as e:
        print(f"Error creating alert: {e}")
        return None

def resolve_alert(alert_id, db_path='api_monitor.db'):
    """
    Mark an alert as resolved (not active)
    
    Args:
        alert_id: ID of the alert to resolve
        db_path: Path to SQLite database
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE alerts SET is_active = 0
        WHERE id = ?
        ''', (alert_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error resolving alert: {e}")
        return False

def get_active_alerts(api_name=None, environment=None, db_path='api_monitor.db'):
    """
    Get active alerts with optional filters
    
    Args:
        api_name: Filter by API name (optional)
        environment: Filter by environment (optional)
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with active alerts
    """
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM alerts WHERE is_active = 1"
    params = []
    
    if api_name:
        query += " AND api_name = ?"
        params.append(api_name)
    
    if environment:
        query += " AND environment = ?"
        params.append(environment)
    
    query += " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Convert timestamp to datetime
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    
    return df

def store_prediction(api_name, environment, prediction_type, predicted_value, confidence, prediction_for, db_path='api_monitor.db'):
    """
    Store a prediction for future reference
    
    Args:
        api_name: API name
        environment: Environment
        prediction_type: Type of prediction
        predicted_value: Predicted value
        confidence: Confidence level (0-1)
        prediction_for: Timestamp for which the prediction is made
        db_path: Path to SQLite database
        
    Returns:
        ID of the new prediction or None on failure
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO predictions (api_name, environment, prediction_type, predicted_value, 
        confidence, predicted_at, prediction_for)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            api_name,
            environment,
            prediction_type,
            predicted_value,
            confidence,
            datetime.now().isoformat(),
            prediction_for.isoformat() if isinstance(prediction_for, datetime) else prediction_for
        ))
        
        prediction_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return prediction_id
    except Exception as e:
        print(f"Error storing prediction: {e}")
        return None

def get_recent_predictions(prediction_type=None, api_name=None, environment=None, limit=100, db_path='api_monitor.db'):
    """
    Get recent predictions with optional filters
    
    Args:
        prediction_type: Filter by prediction type (optional)
        api_name: Filter by API name (optional)
        environment: Filter by environment (optional)
        limit: Maximum number of predictions to return
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with recent predictions
    """
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM predictions"
    conditions = []
    params = []
    
    if prediction_type:
        conditions.append("prediction_type = ?")
        params.append(prediction_type)
    
    if api_name:
        conditions.append("api_name = ?")
        params.append(api_name)
    
    if environment:
        conditions.append("environment = ?")
        params.append(environment)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY predicted_at DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Convert timestamps to datetime
    for col in ['predicted_at', 'prediction_for']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    return df

def get_api_names(db_path='api_monitor.db'):
    """
    Get list of all API names in the database
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        List of API names
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT api_name FROM api_logs')
        names = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return names
    except Exception as e:
        print(f"Error getting API names: {e}")
        return []

def get_environments(db_path='api_monitor.db'):
    """
    Get list of all environments in the database
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        List of environments
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT environment FROM api_logs')
        environments = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return environments
    except Exception as e:
        print(f"Error getting environments: {e}")
        return []

def clean_old_data(days_to_keep=30, db_path='api_monitor.db'):
    """
    Remove old data from the database
    
    Args:
        days_to_keep: Number of days of data to keep
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with counts of deleted records
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        # Delete old logs
        cursor.execute('DELETE FROM api_logs WHERE timestamp < ?', (cutoff_date,))
        logs_deleted = cursor.rowcount
        
        # Delete old anomalies
        cursor.execute('DELETE FROM anomalies WHERE detected_at < ?', (cutoff_date,))
        anomalies_deleted = cursor.rowcount
        
        # Delete old alerts
        cursor.execute('DELETE FROM alerts WHERE created_at < ? AND is_active = 0', (cutoff_date,))
        alerts_deleted = cursor.rowcount
        
        # Delete old predictions
        cursor.execute('DELETE FROM predictions WHERE predicted_at < ?', (cutoff_date,))
        predictions_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            'logs_deleted': logs_deleted,
            'anomalies_deleted': anomalies_deleted,
            'alerts_deleted': alerts_deleted,
            'predictions_deleted': predictions_deleted
        }
    except Exception as e:
        print(f"Error cleaning old data: {e}")
        return {
            'logs_deleted': 0,
            'anomalies_deleted': 0,
            'alerts_deleted': 0,
            'predictions_deleted': 0,
            'error': str(e)
        }
