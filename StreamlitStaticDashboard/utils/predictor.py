import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib
import os

class APIPredictor:
    """
    Class for making predictions about future API behavior
    """
    
    def __init__(self, db_path='api_monitor.db'):
        """
        Initialize the predictor
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.models = {}
        
        # Create models directory if it doesn't exist
        os.makedirs('models', exist_ok=True)
    
    def predict_response_time(self, api_name, environment, hours_ahead=1):
        """
        Predict future response time for an API
        
        Args:
            api_name: Name of the API
            environment: Environment of the API
            hours_ahead: Hours into the future to predict
            
        Returns:
            Dictionary with prediction details
        """
        # Get historical data
        df = self._get_historical_data(api_name, environment)
        
        if df.empty or len(df) < 24:  # Need enough data for predictions
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'response_time',
                'status': 'insufficient_data',
                'message': 'Not enough historical data for prediction'
            }
        
        # Prepare features
        df = self._prepare_time_features(df)
        
        # Train or load model
        model_key = f"{api_name}_{environment}_response_time"
        model_path = f"models/{model_key}.joblib"
        
        try:
            if os.path.exists(model_path):
                model = joblib.load(model_path)
            else:
                model = self._train_response_time_model(df)
                joblib.dump(model, model_path)
            
            self.models[model_key] = model
            
            # Generate future timestamps for prediction
            future_times = []
            now = datetime.now()
            
            for hour in range(1, hours_ahead + 1):
                future_time = now + timedelta(hours=hour)
                future_times.append(future_time)
            
            # Prepare future features
            future_features = []
            
            for future_time in future_times:
                features = {
                    'hour_of_day': future_time.hour,
                    'day_of_week': future_time.weekday(),
                    'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                    'is_business_hours': 1 if 9 <= future_time.hour < 17 else 0
                }
                future_features.append(features)
            
            future_df = pd.DataFrame(future_features)
            
            # Make predictions
            if 'scaler' in self.models:
                future_df_scaled = self.models['scaler'].transform(future_df)
                predictions = model.predict(future_df_scaled)
            else:
                predictions = model.predict(future_df)
            
            # Combine predictions with timestamps
            results = []
            for i, future_time in enumerate(future_times):
                results.append({
                    'prediction_for': future_time.isoformat(),
                    'predicted_response_time': predictions[i],
                    'confidence': 0.8  # Placeholder, would be calculated from model
                })
            
            # Store predictions in database
            for result in results:
                self._store_prediction(
                    api_name,
                    environment,
                    'response_time',
                    result['predicted_response_time'],
                    result['confidence'],
                    result['prediction_for']
                )
            
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'response_time',
                'status': 'success',
                'predictions': results
            }
        
        except Exception as e:
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'response_time',
                'status': 'error',
                'message': str(e)
            }
    
    def predict_error_rate(self, api_name, environment, hours_ahead=1):
        """
        Predict future error rate for an API
        
        Args:
            api_name: Name of the API
            environment: Environment of the API
            hours_ahead: Hours into the future to predict
            
        Returns:
            Dictionary with prediction details
        """
        # Get historical data
        df = self._get_historical_data(api_name, environment)
        
        if df.empty or len(df) < 24:  # Need enough data for predictions
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'error_rate',
                'status': 'insufficient_data',
                'message': 'Not enough historical data for prediction'
            }
        
        # Prepare features and target
        df = self._prepare_time_features(df)
        
        # Calculate error rate for each hour
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_error_rates = df.groupby('hour').agg(
            error_count=('is_error', 'sum'),
            total_count=('is_error', 'count')
        )
        hourly_error_rates['error_rate'] = (hourly_error_rates['error_count'] / hourly_error_rates['total_count']) * 100
        
        # Add time features to hourly data
        hourly_error_rates = hourly_error_rates.reset_index()
        hourly_error_rates['hour_of_day'] = pd.to_datetime(hourly_error_rates['hour']).dt.hour
        hourly_error_rates['day_of_week'] = pd.to_datetime(hourly_error_rates['hour']).dt.dayofweek
        hourly_error_rates['is_weekend'] = hourly_error_rates['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        hourly_error_rates['is_business_hours'] = hourly_error_rates['hour_of_day'].apply(lambda x: 1 if 9 <= x < 17 else 0)
        
        # Train or load model
        model_key = f"{api_name}_{environment}_error_rate"
        model_path = f"models/{model_key}.joblib"
        
        try:
            if os.path.exists(model_path):
                model = joblib.load(model_path)
            else:
                model = self._train_error_rate_model(hourly_error_rates)
                joblib.dump(model, model_path)
            
            self.models[model_key] = model
            
            # Generate future timestamps for prediction
            future_times = []
            now = datetime.now()
            
            for hour in range(1, hours_ahead + 1):
                future_time = now + timedelta(hours=hour)
                future_times.append(future_time)
            
            # Prepare future features
            future_features = []
            
            for future_time in future_times:
                features = {
                    'hour_of_day': future_time.hour,
                    'day_of_week': future_time.weekday(),
                    'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                    'is_business_hours': 1 if 9 <= future_time.hour < 17 else 0
                }
                future_features.append(features)
            
            future_df = pd.DataFrame(future_features)
            
            # Make predictions
            predictions = model.predict(future_df)
            
            # Ensure predictions are non-negative
            predictions = np.maximum(predictions, 0)
            
            # Combine predictions with timestamps
            results = []
            for i, future_time in enumerate(future_times):
                results.append({
                    'prediction_for': future_time.isoformat(),
                    'predicted_error_rate': predictions[i],
                    'confidence': 0.7  # Placeholder, would be calculated from model
                })
            
            # Store predictions in database
            for result in results:
                self._store_prediction(
                    api_name,
                    environment,
                    'error_rate',
                    result['predicted_error_rate'],
                    result['confidence'],
                    result['prediction_for']
                )
            
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'error_rate',
                'status': 'success',
                'predictions': results
            }
        
        except Exception as e:
            return {
                'api_name': api_name,
                'environment': environment,
                'prediction_type': 'error_rate',
                'status': 'error',
                'message': str(e)
            }
    
    def predict_journey_health(self, api_names, environment, hours_ahead=1):
        """
        Predict health of a journey involving multiple APIs
        
        Args:
            api_names: List of API names in the journey
            environment: Environment of the APIs
            hours_ahead: Hours into the future to predict
            
        Returns:
            Dictionary with prediction details
        """
        if not api_names:
            return {
                'environment': environment,
                'prediction_type': 'journey_health',
                'status': 'error',
                'message': 'No APIs specified for journey'
            }
        
        # Predict response time and error rate for each API
        api_predictions = []
        
        for api_name in api_names:
            response_time_pred = self.predict_response_time(api_name, environment, hours_ahead)
            error_rate_pred = self.predict_error_rate(api_name, environment, hours_ahead)
            
            if response_time_pred['status'] == 'success' and error_rate_pred['status'] == 'success':
                api_predictions.append({
                    'api_name': api_name,
                    'response_time_predictions': response_time_pred['predictions'],
                    'error_rate_predictions': error_rate_pred['predictions']
                })
            else:
                continue  # Skip APIs with failed predictions
        
        if not api_predictions:
            return {
                'environment': environment,
                'prediction_type': 'journey_health',
                'status': 'error',
                'message': 'Could not predict for any of the APIs in the journey'
            }
        
        # Calculate journey health score for each time point
        journey_predictions = []
        
        for hour in range(hours_ahead):
            total_response_time = 0
            max_error_rate = 0
            
            for api_pred in api_predictions:
                total_response_time += api_pred['response_time_predictions'][hour]['predicted_response_time']
                max_error_rate = max(max_error_rate, api_pred['error_rate_predictions'][hour]['predicted_error_rate'])
            
            # Simple health score calculation
            # Lower is better (incorporates both response time and error rate)
            health_score = (total_response_time / 1000) + (max_error_rate * 2)
            
            # Health status based on score
            if health_score < 1:
                health_status = 'Excellent'
            elif health_score < 2:
                health_status = 'Good'
            elif health_score < 5:
                health_status = 'Fair'
            else:
                health_status = 'Poor'
            
            prediction_time = datetime.now() + timedelta(hours=hour + 1)
            
            journey_predictions.append({
                'prediction_for': prediction_time.isoformat(),
                'total_response_time': total_response_time,
                'max_error_rate': max_error_rate,
                'health_score': health_score,
                'health_status': health_status
            })
        
        return {
            'environment': environment,
            'prediction_type': 'journey_health',
            'api_journey': api_names,
            'status': 'success',
            'predictions': journey_predictions
        }
    
    def _get_historical_data(self, api_name, environment, days_back=7):
        """
        Get historical data for an API
        
        Args:
            api_name: Name of the API
            environment: Environment of the API
            days_back: Days of historical data to retrieve
            
        Returns:
            DataFrame with historical data
        """
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT * FROM api_logs 
        WHERE api_name = ? AND environment = ? AND timestamp >= ?
        ORDER BY timestamp
        '''
        
        params = [
            api_name,
            environment,
            (datetime.now() - timedelta(days=days_back)).isoformat()
        ]
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def _prepare_time_features(self, df):
        """
        Prepare time-based features for prediction
        
        Args:
            df: DataFrame with historical data
            
        Returns:
            DataFrame with added features
        """
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        df['is_business_hours'] = df['hour_of_day'].apply(lambda x: 1 if 9 <= x < 17 else 0)
        
        return df
    
    def _train_response_time_model(self, df):
        """
        Train a model to predict response time
        
        Args:
            df: DataFrame with historical data
            
        Returns:
            Trained model
        """
        features = ['hour_of_day', 'day_of_week', 'is_weekend', 'is_business_hours']
        X = df[features]
        y = df['response_time']
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        self.models['scaler'] = scaler
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_scaled, y)
        
        return model
    
    def _train_error_rate_model(self, df):
        """
        Train a model to predict error rate
        
        Args:
            df: DataFrame with hourly error rates
            
        Returns:
            Trained model
        """
        features = ['hour_of_day', 'day_of_week', 'is_weekend', 'is_business_hours']
        X = df[features]
        y = df['error_rate']
        
        # Train model
        model = LinearRegression()
        model.fit(X, y)
        
        return model
    
    def _store_prediction(self, api_name, environment, prediction_type, predicted_value, confidence, prediction_for):
        """
        Store a prediction in the database
        
        Args:
            api_name: Name of the API
            environment: Environment of the API
            prediction_type: Type of prediction
            predicted_value: Predicted value
            confidence: Confidence level (0-1)
            prediction_for: Timestamp for which the prediction is made
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure predictions table exists
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
                prediction_for
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            print(f"Error storing prediction: {e}")

def run_predictions(api_names=None, environments=None, db_path='api_monitor.db'):
    """
    Run predictions for specified APIs and environments
    
    Args:
        api_names: List of API names to predict for (None for all)
        environments: List of environments to predict for (None for all)
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with prediction results
    """
    predictor = APIPredictor(db_path)
    
    # Get all API names if not specified
    if api_names is None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT api_name FROM api_logs')
        api_names = [row[0] for row in cursor.fetchall()]
        conn.close()
    
    # Get all environments if not specified
    if environments is None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT environment FROM api_logs')
        environments = [row[0] for row in cursor.fetchall()]
        conn.close()
    
    results = {
        'response_time_predictions': [],
        'error_rate_predictions': [],
        'journey_health_predictions': []
    }
    
    # Predict for each API and environment
    for api_name in api_names:
        for environment in environments:
            # Response time predictions
            response_time_result = predictor.predict_response_time(api_name, environment, hours_ahead=3)
            if response_time_result['status'] == 'success':
                results['response_time_predictions'].append({
                    'api_name': api_name,
                    'environment': environment,
                    'predictions': response_time_result['predictions']
                })
            
            # Error rate predictions
            error_rate_result = predictor.predict_error_rate(api_name, environment, hours_ahead=3)
            if error_rate_result['status'] == 'success':
                results['error_rate_predictions'].append({
                    'api_name': api_name,
                    'environment': environment,
                    'predictions': error_rate_result['predictions']
                })
    
    # Predict journey health for some predefined journeys
    journeys = [
        {'name': 'User Authentication', 'apis': ['/api/auth/login', '/api/users']},
        {'name': 'Order Processing', 'apis': ['/api/orders', '/api/payments', '/api/products']},
        {'name': 'Product Search', 'apis': ['/api/search', '/api/products', '/api/recommendations']}
    ]
    
    for journey in journeys:
        for environment in environments:
            journey_apis = [api for api in journey['apis'] if api in api_names]
            
            if journey_apis:
                journey_result = predictor.predict_journey_health(journey_apis, environment, hours_ahead=3)
                if journey_result['status'] == 'success':
                    results['journey_health_predictions'].append({
                        'journey_name': journey['name'],
                        'environment': environment,
                        'apis': journey_apis,
                        'predictions': journey_result['predictions']
                    })
    
    return results
