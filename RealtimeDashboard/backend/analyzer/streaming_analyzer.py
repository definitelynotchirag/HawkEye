import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

class StreamingAPIAnalyzer:
    def __init__(self, window_size=500):
        self.n_neighbors = 15
        self.contamination = 0.1
        self.window_size = window_size
        
        self.api_data = pd.DataFrame(columns=[
            'timestamp', 'endpoint', 'latency_ms', 
            'status_code', 'request_size', 'user_id'
        ])
        
        self.colors = {
            'normal': '\033[92m',
            'warning': '\033[93m',
            'error': '\033[91m',
            'critical': '\033[91;1m',
            'end': '\033[0m'
        }
        
        self.scaler = StandardScaler()
        self.lof = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            contamination=self.contamination,
            novelty=False
        )
    
    def process_log(self, log):
        self.api_data = pd.concat([self.api_data, pd.DataFrame([log])], ignore_index=True)
        
        if len(self.api_data) > self.window_size:
            self.api_data = self.api_data.iloc[-self.window_size:]
        
        if len(self.api_data) >= self.n_neighbors:
            self.detect_anomalies()
            self.display_last_result()
    
    def detect_anomalies(self):
        self.api_data['is_error'] = (self.api_data['status_code'] >= 400).astype(int)
        self.api_data['endpoint_risk'] = self.api_data['endpoint'].apply(
            lambda x: 0.9 if 'admin' in x or 'debug' in x else 0.1)
        
        features = self.api_data[['latency_ms', 'request_size', 'is_error', 'endpoint_risk']]
        features_scaled = self.scaler.fit_transform(features)
        
        self.api_data['anomaly_score'] = self.lof.fit_predict(features_scaled)
        self.api_data['is_anomaly'] = (self.api_data['anomaly_score'] == -1).astype(int)
        
        conditions = [
            (self.api_data['is_anomaly'] == 0),
            (self.api_data['status_code'] < 400) & (self.api_data['is_anomaly'] == 1),
            (self.api_data['status_code'] >= 400) & (self.api_data['is_anomaly'] == 1),
            (self.api_data['status_code'] >= 500) & (self.api_data['is_anomaly'] == 1)
        ]
        choices = ['normal', 'warning', 'error', 'critical']
        self.api_data['severity'] = np.select(conditions, choices, default='normal')
    
    def display_last_result(self):
        last_log = self.api_data.iloc[-1]
        color = self.colors[last_log['severity']]
        print(f"{color}[{last_log['severity'].upper()}] {last_log['timestamp']} - {last_log['endpoint']}{self.colors['end']}")
        print(f"  Status: {last_log['status_code']} | Latency: {last_log['latency_ms']:.0f}ms | Size: {last_log['request_size']:.0f} bytes")
        print(f"  User: {last_log['user_id']} | Anomaly score: {last_log['anomaly_score']}")
    
    def stream_logs(self, interval=1):
        endpoints = ['/api/users', '/api/products', '/api/orders', '/auth/login', '/auth/refresh', '/admin/export']
        while True:
            log = {
                'timestamp': datetime.now(),
                'endpoint': np.random.choice(endpoints),
                'latency_ms': np.random.normal(50, 10) if np.random.rand() > 0.05 else np.random.normal(500, 100),
                'status_code': np.random.choice([200, 201, 304, 400, 401, 403, 404, 500], p=[0.75, 0.1, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02]),
                'request_size': np.random.normal(1024, 256) if np.random.rand() > 0.05 else np.random.normal(10240, 2048),
                'user_id': np.random.randint(1000, 1100)
            }
            self.process_log(log)
            time.sleep(interval)