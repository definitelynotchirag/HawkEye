# Log Streaming Application

This project is designed to stream log data from a Python backend to a frontend application built with React. It includes a backend service that processes and analyzes log data, and a frontend interface that displays this data in real-time.

## Project Structure

```
log-streaming-app
├── backend
│   ├── app.py                # Entry point for the backend application
│   ├── requirements.txt       # Python dependencies for the backend
│   └── analyzer
│       ├── __init__.py       # Marks the analyzer directory as a package
│       └── streaming_analyzer.py # Contains the StreamingAPIAnalyzer class
├── frontend
│   ├── public
│   │   ├── index.html        # Main HTML file for the frontend
│   │   └── favicon.svg       # Favicon for the frontend application
│   ├── src
│   │   ├── App.js            # Main component of the React application
│   │   ├── components
│   │   │   ├── Dashboard.js   # Component for displaying overall status and log stream
│   │   │   ├── LogEntry.js    # Component for a single log entry
│   │   │   ├── LogStream.js    # Component for handling real-time log streaming
│   │   │   └── StatusIndicator.js # Component for visual status indication
│   │   ├── hooks
│   │   │   └── useLogStream.js # Custom hook for managing log stream connection
│   │   ├── index.js          # Entry point for the React application
│   │   └── utils
│   │       └── formatters.js  # Utility functions for formatting log data
│   ├── package.json          # Configuration file for npm
│   └── README.md             # Documentation for the frontend application
├── docker-compose.yml        # Docker configuration for multi-container setup
└── README.md                 # Documentation for the entire project
```

## Getting Started

### Prerequisites

- Python 3.x
- Node.js and npm

### Backend Setup

1. Navigate to the `backend` directory.
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the backend application:
   ```
   python app.py
   ```

### Frontend Setup

1. Navigate to the `frontend` directory.
2. Install the required npm packages:
   ```
   npm install
   ```
3. Start the frontend application:
   ```
   npm start
   ```

### Usage

Once both the backend and frontend applications are running, you can access the frontend interface in your web browser. The log data will be streamed in real-time, and you can monitor the status of API calls and any anomalies detected by the backend.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License.