import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import joblib
import os

class AnomalyDetector:
    """
    Class for detecting anomalies in API performance metrics
    using various machine learning models.
    """
    
    def __init__(self, sensitivity=3.0, db_path='api_monitor.db'):
        """
        Initialize the anomaly detector
        
        Args:
            sensitivity: Threshold for anomaly detection (lower = more sensitive)
            db_path: Path to SQLite database
        """
        self.sensitivity = sensitivity
        self.db_path = db_path
        self.models = {}
        
        # Create models directory if it doesn't exist
        os.makedirs('models', exist_ok=True)
    
    def detect_response_time_anomalies(self, api_name=None, environment=None, hours_back=24):
        """
        Detect response time anomalies using Isolation Forest
        
        Args:
            api_name: Optional API name to filter data
            environment: Optional environment to filter data
            hours_back: Hours of historical data to analyze
            
        Returns:
            DataFrame with detected anomalies
        """
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM api_logs WHERE timestamp >= ?"
        params = [(datetime.now() - timedelta(hours=hours_back)).isoformat()]
        
        if api_name:
            query += " AND api_name = ?"
            params.append(api_name)
        
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty or len(df) < 10:  # Need enough data for detection
            return pd.DataFrame(columns=['timestamp', 'api_name', 'response_time', 'environment', 'anomaly_score'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group by API name if no specific API provided
        anomalies = []
        
        if api_name:
            api_dfs = [(api_name, df)]
        else:
            api_dfs = [(name, group) for name, group in df.groupby('api_name')]
        
        for name, api_df in api_dfs:
            if len(api_df) < 10:  # Skip APIs with too little data
                continue
                
            # Add time features to help with pattern detection
            api_df['hour_of_day'] = api_df['timestamp'].dt.hour
            api_df['day_of_week'] = api_df['timestamp'].dt.dayofweek
            
            # Prepare features
            features = ['response_time', 'hour_of_day', 'day_of_week']
            X = api_df[features].values
            
            # Standardize the data
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Load or train Isolation Forest model
            model_key = f"{name}_{environment if environment else 'all'}"
            model_path = f"models/iso_forest_{model_key}.joblib"
            
            try:
                if os.path.exists(model_path):
                    model = joblib.load(model_path)
                else:
                    model = IsolationForest(
                        contamination=0.05,  # Assume 5% of data is anomalous
                        random_state=42
                    )
                    model.fit(X_scaled)
                    joblib.dump(model, model_path)
                
                # Save model for future use
                self.models[model_key] = model
                
                # Predict anomalies
                api_df['anomaly_score'] = model.decision_function(X_scaled)
                api_df['is_anomaly'] = model.predict(X_scaled) == -1
                
                # Get anomalies based on sensitivity (more negative = more anomalous)
                threshold = -0.1 * self.sensitivity
                anomalies_df = api_df[api_df['anomaly_score'] < threshold].copy()
                
                if not anomalies_df.empty:
                    anomalies.append(anomalies_df[['timestamp', 'api_name', 'response_time', 'environment', 'anomaly_score']])
                    
                    # Save anomalies to database
                    self._save_anomalies_to_db(anomalies_df, 'response_time')
                    
            except Exception as e:
                print(f"Error detecting anomalies for {name}: {e}")
                continue
        
        if anomalies:
            return pd.concat(anomalies)
        else:
            return pd.DataFrame(columns=['timestamp', 'api_name', 'response_time', 'environment', 'anomaly_score'])
    
    def detect_error_rate_anomalies(self, api_name=None, environment=None, hours_back=24, window_minutes=10):
        """
        Detect error rate anomalies using a statistical approach
        
        Args:
            api_name: Optional API name to filter data
            environment: Optional environment to filter data
            hours_back: Hours of historical data to analyze
            window_minutes: Time window in minutes for error rate calculation
            
        Returns:
            DataFrame with detected anomalies
        """
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM api_logs WHERE timestamp >= ?"
        params = [(datetime.now() - timedelta(hours=hours_back)).isoformat()]
        
        if api_name:
            query += " AND api_name = ?"
            params.append(api_name)
        
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty or len(df) < 10:  # Need enough data for detection
            return pd.DataFrame(columns=['timestamp', 'api_name', 'error_rate', 'environment', 'anomaly_score'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group by API name and time window
        df['time_window'] = df['timestamp'].dt.floor(f'{window_minutes}min')
        
        # Calculate error rate for each window
        error_rates = df.groupby(['api_name', 'environment', 'time_window']).agg(
            total_calls=('api_name', 'count'),
            error_count=('is_error', 'sum')
        ).reset_index()
        
        error_rates['error_rate'] = (error_rates['error_count'] / error_rates['total_calls']) * 100
        
        # Group by API and detect anomalies
        anomalies = []
        
        for (name, env), group in error_rates.groupby(['api_name', 'environment']):
            if len(group) < 5:  # Need enough windows for detection
                continue
            
            # Calculate statistical measures
            mean_error_rate = group['error_rate'].mean()
            std_error_rate = group['error_rate'].std()
            
            if std_error_rate == 0:  # No variation, can't detect anomalies
                continue
            
            # Calculate Z-scores
            group['z_score'] = (group['error_rate'] - mean_error_rate) / std_error_rate
            
            # Identify anomalies based on sensitivity
            threshold = self.sensitivity
            anomalies_df = group[group['z_score'] > threshold].copy()
            
            if not anomalies_df.empty:
                anomalies_df = anomalies_df.rename(columns={'time_window': 'timestamp'})
                anomalies_df['anomaly_score'] = anomalies_df['z_score']
                anomalies.append(anomalies_df[['timestamp', 'api_name', 'error_rate', 'environment', 'anomaly_score']])
                
                # Save anomalies to database
                self._save_anomalies_to_db(anomalies_df, 'error_rate')
        
        if anomalies:
            return pd.concat(anomalies)
        else:
            return pd.DataFrame(columns=['timestamp', 'api_name', 'error_rate', 'environment', 'anomaly_score'])
    
    def detect_pattern_change(self, api_name=None, environment=None, days_back=7):
        """
        Detect pattern changes in API response time distribution
        
        Args:
            api_name: Optional API name to filter data
            environment: Optional environment to filter data
            days_back: Days of historical data to analyze
            
        Returns:
            DataFrame with detected pattern changes
        """
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM api_logs WHERE timestamp >= ?"
        params = [(datetime.now() - timedelta(days=days_back)).isoformat()]
        
        if api_name:
            query += " AND api_name = ?"
            params.append(api_name)
        
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty or len(df) < 50:  # Need enough data for pattern detection
            return pd.DataFrame(columns=['api_name', 'environment', 'pattern_change_score', 'detected_at'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Add time features
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day'] = df['timestamp'].dt.day
        
        pattern_changes = []
        
        # Group by API name and environment
        for (name, env), group in df.groupby(['api_name', 'environment']):
            if len(group) < 50:
                continue
            
            # Split into recent data (last day) and historical data
            recent_cutoff = datetime.now() - timedelta(days=1)
            recent_data = group[group['timestamp'] >= recent_cutoff]
            historical_data = group[group['timestamp'] < recent_cutoff]
            
            if len(recent_data) < 10 or len(historical_data) < 30:
                continue
            
            # Prepare features
            features = ['response_time', 'hour_of_day', 'day_of_week']
            
            # Scale the data
            scaler = StandardScaler()
            historical_scaled = scaler.fit_transform(historical_data[features])
            recent_scaled = scaler.transform(recent_data[features])
            
            # Use DBSCAN to identify patterns in historical data
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            historical_clusters = dbscan.fit_predict(historical_scaled)
            
            # Count percentage of points that would be outliers in the historical pattern
            dbscan.fit(historical_scaled)
            recent_clusters = dbscan.fit_predict(recent_scaled)
            outlier_percentage = np.sum(recent_clusters == -1) / len(recent_clusters) * 100
            
            # If outlier percentage is high, pattern has changed
            if outlier_percentage > 30:  # Adjustable threshold
                pattern_changes.append({
                    'api_name': name,
                    'environment': env,
                    'pattern_change_score': outlier_percentage,
                    'detected_at': datetime.now()
                })
                
                # Save pattern change to database
                self._save_pattern_change_to_db(name, env, outlier_percentage)
        
        return pd.DataFrame(pattern_changes)
    
    def _save_anomalies_to_db(self, anomalies_df, anomaly_type):
        """
        Save detected anomalies to database
        
        Args:
            anomalies_df: DataFrame with anomalies
            anomaly_type: Type of anomaly ('response_time' or 'error_rate')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure anomalies table exists
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
        
        # Insert anomalies
        for _, row in anomalies_df.iterrows():
            value_col = 'response_time' if anomaly_type == 'response_time' else 'error_rate'
            
            # Check if this anomaly already exists
            cursor.execute('''
            SELECT id FROM anomalies 
            WHERE api_name = ? AND environment = ? AND anomaly_type = ? 
            AND detected_at >= ? AND detected_at <= ?
            ''', (
                row['api_name'],
                row['environment'],
                anomaly_type,
                (row['timestamp'] - timedelta(minutes=5)).isoformat(),
                (row['timestamp'] + timedelta(minutes=5)).isoformat()
            ))
            
            if cursor.fetchone() is None:  # No duplicate found
                cursor.execute('''
                INSERT INTO anomalies (api_name, environment, anomaly_type, anomaly_value, 
                anomaly_score, detected_at, is_acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    row['api_name'],
                    row['environment'],
                    anomaly_type,
                    float(row[value_col]),
                    float(row['anomaly_score']),
                    row['timestamp'].isoformat()
                ))
        
        conn.commit()
        conn.close()
    
    def _save_pattern_change_to_db(self, api_name, environment, pattern_change_score):
        """
        Save detected pattern changes to database
        
        Args:
            api_name: Name of the API
            environment: Environment of the API
            pattern_change_score: Score indicating magnitude of pattern change
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure anomalies table exists
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
        
        # Check if this pattern change already exists
        cursor.execute('''
        SELECT id FROM anomalies 
        WHERE api_name = ? AND environment = ? AND anomaly_type = ? 
        AND detected_at >= ?
        ''', (
            api_name,
            environment,
            'pattern_change',
            (datetime.now() - timedelta(hours=24)).isoformat()
        ))
        
        if cursor.fetchone() is None:  # No duplicate found
            cursor.execute('''
            INSERT INTO anomalies (api_name, environment, anomaly_type, anomaly_value, 
            anomaly_score, detected_at, is_acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (
                api_name,
                environment,
                'pattern_change',
                0.0,  # No specific value for pattern changes
                float(pattern_change_score),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def get_recent_anomalies(self, hours_back=24):
        """
        Get recent anomalies from database
        
        Args:
            hours_back: Hours of historical anomalies to retrieve
            
        Returns:
            DataFrame with recent anomalies
        """
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT * FROM anomalies 
        WHERE detected_at >= ? 
        ORDER BY detected_at DESC
        '''
        
        params = [(datetime.now() - timedelta(hours=hours_back)).isoformat()]
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['detected_at'] = pd.to_datetime(df['detected_at'])
        
        return df
    
    def acknowledge_anomaly(self, anomaly_id):
        """
        Mark an anomaly as acknowledged
        
        Args:
            anomaly_id: ID of the anomaly to acknowledge
            
        Returns:
            Boolean indicating success
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE anomalies SET is_acknowledged = 1
            WHERE id = ?
            ''', (anomaly_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error acknowledging anomaly: {e}")
            return False

def run_anomaly_detection(sensitivity=3.0, db_path='api_monitor.db'):
    """
    Run a full anomaly detection cycle
    
    Args:
        sensitivity: Threshold for anomaly detection
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with detection results
    """
    detector = AnomalyDetector(sensitivity=sensitivity, db_path=db_path)
    
    # Detect response time anomalies
    response_time_anomalies = detector.detect_response_time_anomalies()
    
    # Detect error rate anomalies
    error_rate_anomalies = detector.detect_error_rate_anomalies()
    
    # Detect pattern changes
    pattern_changes = detector.detect_pattern_change()
    
    return {
        'response_time_anomalies': len(response_time_anomalies),
        'error_rate_anomalies': len(error_rate_anomalies),
        'pattern_changes': len(pattern_changes),
        'total_anomalies': len(response_time_anomalies) + len(error_rate_anomalies) + len(pattern_changes)
    }
