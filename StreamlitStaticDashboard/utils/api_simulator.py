import random
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
import json

def simulate_api_calls(num_calls=100, db_path='api_monitor.db'):
    """
    Simulate API calls and store them in the database
    
    Args:
        num_calls: Number of API calls to simulate
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with simulated calls
    """
    # Define API names and environments
    api_names = [
        '/api/users', 
        '/api/products', 
        '/api/orders', 
        '/api/payments', 
        '/api/auth/login',
        '/api/auth/logout', 
        '/api/search', 
        '/api/recommendations'
    ]
    
    environments = ['on-premises', 'aws-cloud', 'azure-cloud', 'gcp-cloud']
    
    # Generate random logs
    logs = []
    now = datetime.now()
    
    for _ in range(num_calls):
        # Pick a random API and environment
        api_name = random.choice(api_names)
        environment = random.choice(environments)
        
        # Generate a timestamp within the last 24 hours
        timestamp = now - timedelta(hours=random.uniform(0, 24))
        
        # Generate response time
        # Normal distribution with occasional spikes
        if random.random() < 0.05:  # 5% chance of anomaly
            response_time = random.uniform(500, 2000)  # Abnormally high
        else:
            base_response_time = {
                '/api/users': 150,
                '/api/products': 200,
                '/api/orders': 250,
                '/api/payments': 300,
                '/api/auth/login': 180,
                '/api/auth/logout': 100,
                '/api/search': 350,
                '/api/recommendations': 400
            }.get(api_name, 200)
            
            # Add some variance based on environment
            env_factor = {
                'on-premises': 1.0,
                'aws-cloud': 0.8,
                'azure-cloud': 0.9,
                'gcp-cloud': 0.85
            }.get(environment, 1.0)
            
            # Add time-of-day pattern
            hour = timestamp.hour
            time_factor = 1.0 + 0.2 * np.sin(hour / 24 * 2 * np.pi)
            
            # Calculate final response time with some random variation
            response_time = base_response_time * env_factor * time_factor * random.uniform(0.8, 1.2)
        
        # Generate status code
        # Higher chance of errors during anomalies
        if response_time > 500 and random.random() < 0.3:
            status_code = random.choice([500, 502, 503, 504])
            is_error = 1
        elif random.random() < 0.02:  # 2% random error rate
            status_code = random.choice([400, 401, 403, 404, 500])
            is_error = 1
        else:
            status_code = 200
            is_error = 0
        
        # Create additional info as JSON
        additional_info = json.dumps({
            'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
            'path': api_name,
            'query_params': {'limit': 10, 'offset': 0} if random.random() < 0.5 else {},
            'client_ip': f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
        })
        
        # Create log entry
        log = {
            'api_name': api_name,
            'response_time': response_time,
            'status_code': status_code,
            'is_error': is_error,
            'environment': environment,
            'timestamp': timestamp.isoformat(),
            'request_id': str(uuid.uuid4()),
            'user_id': f"user_{random.randint(1, 1000)}",
            'additional_info': additional_info
        }
        
        logs.append(log)
    
    # Store logs in database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure api_logs table exists
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
        
        # Insert logs
        for log in logs:
            cursor.execute('''
            INSERT INTO api_logs (api_name, response_time, status_code, is_error, environment,
            timestamp, request_id, user_id, additional_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log['api_name'],
                log['response_time'],
                log['status_code'],
                log['is_error'],
                log['environment'],
                log['timestamp'],
                log['request_id'],
                log['user_id'],
                log['additional_info']
            ))
        
        conn.commit()
        conn.close()
        
        # Return logs as DataFrame
        return pd.DataFrame(logs)
    
    except Exception as e:
        print(f"Error simulating API calls: {e}")
        return pd.DataFrame()

def generate_log_file(num_calls=100, format='json', file_path='sample_logs.json'):
    """
    Generate a sample log file
    
    Args:
        num_calls: Number of API calls to simulate
        format: Log format ('json' or 'csv')
        file_path: Output file path
        
    Returns:
        Path to the generated file
    """
    # Simulate API calls
    logs = simulate_api_calls(num_calls).to_dict('records')
    
    try:
        if format == 'json':
            with open(file_path, 'w') as f:
                for log in logs:
                    f.write(json.dumps(log) + '\n')
        elif format == 'csv':
            df = pd.DataFrame(logs)
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return file_path
    
    except Exception as e:
        print(f"Error generating log file: {e}")
        return None

def simulate_anomaly(api_name, environment, anomaly_type, duration_minutes=30, db_path='api_monitor.db'):
    """
    Simulate an anomaly for a specific API
    
    Args:
        api_name: Name of the API to affect
        environment: Environment to affect
        anomaly_type: Type of anomaly ('response_time' or 'error_rate')
        duration_minutes: Duration of the anomaly in minutes
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with anomaly details
    """
    try:
        now = datetime.now()
        start_time = now - timedelta(minutes=duration_minutes)
        end_time = now
        
        # Number of calls to simulate during the anomaly period
        num_calls = duration_minutes * 2  # 2 calls per minute
        
        logs = []
        
        for i in range(num_calls):
            # Calculate timestamp
            progress = i / num_calls
            timestamp = start_time + timedelta(minutes=duration_minutes * progress)
            
            # Set anomaly parameters
            if anomaly_type == 'response_time':
                # Gradually increasing response time
                severity = 1 + progress * 5  # Starts at 1x, ends at 6x normal response time
                response_time = 200 * severity
                status_code = 200
                is_error = 0
            elif anomaly_type == 'error_rate':
                # Normal response time, but high error rate
                response_time = random.uniform(150, 300)
                status_code = random.choice([500, 502, 503]) if random.random() < 0.8 else 200
                is_error = 1 if status_code >= 400 else 0
            else:
                raise ValueError(f"Unsupported anomaly type: {anomaly_type}")
            
            # Create log entry
            log = {
                'api_name': api_name,
                'response_time': response_time,
                'status_code': status_code,
                'is_error': is_error,
                'environment': environment,
                'timestamp': timestamp.isoformat(),
                'request_id': str(uuid.uuid4()),
                'user_id': f"user_{random.randint(1, 1000)}",
                'additional_info': '{}'
            }
            
            logs.append(log)
        
        # Store logs in database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for log in logs:
            cursor.execute('''
            INSERT INTO api_logs (api_name, response_time, status_code, is_error, environment,
            timestamp, request_id, user_id, additional_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log['api_name'],
                log['response_time'],
                log['status_code'],
                log['is_error'],
                log['environment'],
                log['timestamp'],
                log['request_id'],
                log['user_id'],
                log['additional_info']
            ))
        
        conn.commit()
        conn.close()
        
        return {
            'api_name': api_name,
            'environment': environment,
            'anomaly_type': anomaly_type,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'num_calls': num_calls
        }
    
    except Exception as e:
        print(f"Error simulating anomaly: {e}")
        return {
            'error': str(e)
        }
