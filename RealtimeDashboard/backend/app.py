from flask import Flask, Response, jsonify
from flask_cors import CORS
import json
from analyzer.streaming_analyzer import StreamingAPIAnalyzer
import time
from datetime import datetime
import numpy as np

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
analyzer = StreamingAPIAnalyzer()

@app.route('/logs')
def stream_logs():
    def generate():
        endpoints = ['/api/users', '/api/products', '/api/orders', '/auth/login', '/auth/refresh', '/admin/export']
        while True:
            # Generate a log entry
            log = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': np.random.choice(endpoints),
                'latency_ms': int(np.random.normal(50, 10) if np.random.rand() > 0.05 else np.random.normal(500, 100)),
                'status_code': int(np.random.choice([200, 201, 304, 400, 401, 403, 404, 500], 
                                               p=[0.75, 0.1, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02])),
                'request_size': int(np.random.normal(1024, 256) if np.random.rand() > 0.05 else np.random.normal(10240, 2048)),
                'user_id': f"user_{np.random.randint(1000, 1100)}",
                'anomaly_score': float(np.random.uniform(-1, 1))
            }
            
            # Process log for anomaly detection
            analyzer.process_log(log)
            
            # Format for SSE
            yield f"data: {json.dumps(log)}\n\n"
            time.sleep(2)  # Send data every 2 seconds
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/status')
def get_status():
    statuses = ['normal', 'warning', 'error', 'critical']
    weights = [0.7, 0.2, 0.07, 0.03]  # Probabilities for each status
    status = np.random.choice(statuses, p=weights)
    return jsonify({'status': status})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)