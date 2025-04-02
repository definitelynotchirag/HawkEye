Collecting workspace information# HAWKEYE: Advanced API Monitoring & Anomaly Detection System

Hawkeye is a comprehensive monitoring solution that provides real-time visibility into API performance across distributed environments. It leverages machine learning to detect anomalies in response times and error rates, and offers predictive analytics to help prevent service disruptions before they occur.

## Features

### 1. Real-Time API Monitoring
- Track response times, error rates, and traffic patterns across multiple environments
- Filter by API endpoints, environments, and time ranges
- Interactive dashboards with dynamic visualizations

### 2. ML-Powered Anomaly Detection
- Automatically identify abnormal API behavior using machine learning algorithms
- Detect unusual response times, error rates, and pattern changes
- Customizable sensitivity settings to balance detection accuracy

### 3. Predictive Analytics
- Forecast API performance issues before they affect users
- Predict response times and error rates using time-series analysis
- API Journey Health predictions for multi-step user flows

### 4. Multi-Environment Support
- Monitor APIs across on-premises, AWS, Azure, and Google Cloud environments
- Compare performance metrics across different deployment environments
- Unified view across your entire API ecosystem

### 5. Customizable Alerting
- Configure alert rules based on anomaly types and severity
- Multiple notification methods (email, Slack, webhooks)
- Alert acknowledgement and management workflow

## Architecture

Hawkeye consists of multiple components:

1. **Static Dashboard (Streamlit)**: A data-focused dashboard for historical analysis and reporting
2. **Realtime Dashboard (React + Flask/Express)**: A live monitoring interface with SSE for real-time updates
3. **Backend Services**: Data processing, anomaly detection, and prediction engines

## Key Components

### Utils

- `db_manager.py`: Database initialization and query functions
- `anomaly_detector.py`: ML-based anomaly detection algorithms
- `predictor.py`: Time-series prediction for API metrics
- `api_simulator.py`: Generates realistic API traffic data for demo purposes

### Pages

- dashboard.py: Main monitoring dashboard with key metrics
- `anomaly_detection.py`: Anomaly investigation and management
- prediction.py: Future API performance forecasting
- settings.py: System configuration and maintenance

## Unique Ideas

1. **API Journey Health Analysis**: Analyzes the combined health of multiple API endpoints that form a common user journey
2. **Multi-Environment Correlation**: Identifies patterns across different environments to detect deployment issues
3. **Adaptive Anomaly Detection**: Self-adjusting sensitivity based on historical patterns and false positives

## How to Run

### Static Dashboard (Streamlit)

1. Navigate to the StreamlitStaticDashboard directory:
   ```
   cd StreamlitStaticDashboard
   ```

2. Create and activate a virtual environment (if not already done):
   ```
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

5. Access the dashboard at http://localhost:8501

### Realtime Dashboard

1. Navigate to the RealtimeDashboard directory:
   ```
   cd RealtimeDashboard
   ```

2. Start the services using Docker Compose:
   ```
   cd backend && python3 app.py 
   cd ..
   cd frontend && npm run dev
   ```

3. Access the dashboard at http://localhost:3000

## Demo Data Generation

To populate the system with sample data:

1. Click the "Generate Demo Data" button in the sidebar of the main dashboard
2. This will create realistic API logs with various patterns, including normal traffic and anomalies

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request

## License

© 2023 API Monitoring & Anomaly Detection System