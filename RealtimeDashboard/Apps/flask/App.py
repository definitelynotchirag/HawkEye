from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import json
import time
import boto3
from datetime import datetime, timedelta
import os
import logging
import random
import requests

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure OpenTelemetry
resource = Resource(attributes={SERVICE_NAME: "flask-cloudfront-service"})
trace_provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"))
trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

app = Flask(__name__)
CORS(app)

# Initialize OpenTelemetry instrumentation
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Configure AWS CloudFront client
cloudfront = boto3.client(
    'cloudfront',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Configure AWS CloudWatch Logs client for log retrieval
logs = boto3.client(
    'logs',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def get_distribution_id():
    """Get the first CloudFront distribution ID or return None"""
    try:
        response = cloudfront.list_distributions()
        distributions = response.get('DistributionList', {}).get('Items', [])
        if distributions:
            return distributions[0]['Id']
        else:
            return None
    except Exception as e:
        logging.error(f"Error retrieving CloudFront distributions: {e}")
        return None

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/call-express')
def call_express():
    with tracer.start_as_current_span("call-express-service") as span:
        try:
            # Use requests library to call Express service
            response = requests.get("http://express-service:3000/api/data")
            return jsonify({"status": "success", "express_data": response.json()})
        except Exception as e:
            span.record_exception(e)
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cloudfront/distributions')
def get_distributions():
    with tracer.start_as_current_span("get_cloudfront_distributions") as span:
        try:
            response = cloudfront.list_distributions()
            distributions = response.get('DistributionList', {}).get('Items', [])
            result = []
            
            for dist in distributions:
                result.append({
                    'id': dist['Id'],
                    'domain_name': dist['DomainName'],
                    'enabled': dist['Enabled'],
                    'status': dist['Status']
                })
                
            span.set_attribute("distributions.count", len(result))
            return jsonify({"distributions": result})
        except Exception as e:
            span.record_exception(e)
            logging.error(f"Error listing CloudFront distributions: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/logs/cloudfront')
def stream_cloudfront_logs():
    distribution_id = get_distribution_id()
    
    def generate():
        with tracer.start_as_current_span("stream_cloudfront_logs"):
            if not distribution_id:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "flask-service",
                    "message": "No CloudFront distribution found. Using simulated data.",
                    "level": "warning"
                }
                yield f"data: {json.dumps(log_entry)}\n\n"
                time.sleep(1)
                
            # If no distribution found or error occurs, fallback to simulated data
            while True:
                try:
                    # Try to get real CloudFront logs if available
                    log_entry = get_next_log_entry(distribution_id)
                except Exception as e:
                    # If error, create a simulated log entry
                    log_entry = create_simulated_log_entry()
                    
                yield f"data: {json.dumps(log_entry)}\n\n"
                time.sleep(1)  # Send data every second
    
    return Response(generate(), mimetype='text/event-stream')

def get_next_log_entry(distribution_id):
    """Try to fetch a real CloudFront log entry"""
    # In a real implementation, you would fetch from CloudWatch Logs where CloudFront logs are stored
    # This is a simplified example - actual implementation depends on your CloudFront logging setup
    
    log_group_name = f"/aws/cloudfront/{distribution_id}"
    
    try:
        # Try to find log streams
        response = logs.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if not response['logStreams']:
            raise Exception("No log streams found")
            
        log_stream_name = response['logStreams'][0]['logStreamName']
        
        # Get log events
        events = logs.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            limit=1,
            startFromHead=False
        )
        
        if not events['events']:
            raise Exception("No log events found")
            
        log_event = events['events'][0]
        
        # Parse the CloudFront log into desired format
        # This is simplified - actual parsing depends on your log format
        return {
            'timestamp': datetime.fromtimestamp(log_event['timestamp']/1000).isoformat(),
            'message': log_event['message'],
            'source': 'cloudfront',
            'distribution_id': distribution_id,
            'type': 'real'
        }
    except Exception as e:
        logging.warning(f"Could not fetch real CloudFront logs: {e}")
        raise e

def create_simulated_log_entry():
    """Create a simulated CloudFront log entry for demo purposes"""
    paths = ['/images/banner.jpg', '/api/products', '/index.html', '/css/main.css', '/js/app.js']
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    status_codes = [200, 200, 200, 200, 301, 302, 304, 400, 403, 404, 500]
    status_weights = [0.7, 0.05, 0.05, 0.03, 0.02, 0.02, 0.05, 0.02, 0.02, 0.03, 0.01]
    
    edge_locations = ['IAD53-C1', 'DFW50-C2', 'LHR62-C1', 'NRT57-C3', 'SYD1-C2']
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36'
    ]
    
    client_ips = [f"192.168.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(5)]
    
    timestamp = datetime.now()
    path = random.choice(paths)
    method = random.choice(methods)
    status = random.choices(status_codes, weights=status_weights)[0]
    bytes_sent = random.randint(500, 150000)
    response_time = random.randint(10, 500)
    
    return {
        'timestamp': timestamp.isoformat(),
        'edge_location': random.choice(edge_locations),
        'bytes_sent': bytes_sent,
        'client_ip': random.choice(client_ips),
        'method': method,
        'host': 'example-distribution.cloudfront.net',
        'path': path,
        'status': status,
        'referrer': 'https://www.example.com/',
        'user_agent': random.choice(user_agents),
        'query_string': 'v=1.0' if random.random() > 0.7 else '',
        'cookie': 'session=abc123' if random.random() > 0.5 else '',
        'result_type': 'Hit' if random.random() > 0.3 else 'Miss',
        'request_id': f"{format(random.getrandbits(64), 'x')}",
        'host_header': 'example.com',
        'protocol': 'https',
        'request_bytes': random.randint(200, 5000),
        'time_taken': response_time,
        'forwarded_for': '',
        'ssl_protocol': 'TLSv1.2',
        'ssl_cipher': 'ECDHE-RSA-AES128-GCM-SHA256',
        'response_result_type': 'Hit' if random.random() > 0.2 else 'Miss',
        'http_version': 'HTTP/2.0',
        'fle_status': '-',
        'fle_encrypted_fields': '-',
        'source': 'cloudfront',
        'type': 'simulated',
        'anomaly_score': random.uniform(-1, 1)
    }

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)