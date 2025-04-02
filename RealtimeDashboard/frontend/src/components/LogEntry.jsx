import React from 'react';

const LogEntry = ({ log }) => {
    return (
        <div className={`log-entry ${log.severity}`}>
            <div className="log-timestamp">{new Date(log.timestamp).toLocaleString()}</div>
            <div className="log-details">
                <div className="log-endpoint">{log.endpoint}</div>
                <div className="log-status">Status: {log.status_code}</div>
                <div className="log-latency">Latency: {log.latency_ms} ms</div>
                <div className="log-size">Size: {log.request_size} bytes</div>
                <div className="log-user">User: {log.user_id}</div>
                <div className="log-anomaly-score">Anomaly Score: {log.anomaly_score}</div>
            </div>
        </div>
    );
};

export default LogEntry;