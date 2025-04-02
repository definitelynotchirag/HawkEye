import React, { useEffect, useState } from 'react';
import LogStream from './LogStream';
import StatusIndicator from './StatusIndicator';

const Dashboard = () => {
    const [status, setStatus] = useState('Loading...');
    const [logEntries, setLogEntries] = useState([]);

    useEffect(() => {
        const fetchStatus = async () => {
            // Fetch the status from the backend
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                setStatus(data.status);
            } catch (error) {
                setStatus('Error fetching status');
            }
        };

        fetchStatus();
    }, []);

    const handleNewLogEntry = (newLogEntry) => {
        setLogEntries((prevEntries) => [...prevEntries, newLogEntry]);
    };

    return (
        <div>
            <h1>Log Streaming Dashboard</h1>
            <StatusIndicator status={status} />
            <LogStream onNewLogEntry={handleNewLogEntry} />
            <div>
                <h2>Log Entries</h2>
                <ul>
                    {logEntries.map((entry, index) => (
                        <li key={index}>{entry}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default Dashboard;