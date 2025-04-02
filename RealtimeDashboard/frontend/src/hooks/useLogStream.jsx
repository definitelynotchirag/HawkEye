import { useEffect, useState } from 'react';

const useLogStream = () => {
    const [logs, setLogs] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const eventSource = new EventSource('http://localhost:5000/logs'); // Adjust the URL as needed

        eventSource.onmessage = (event) => {
            const newLog = JSON.parse(event.data);
            setLogs((prevLogs) => [...prevLogs, newLog]);
        };

        eventSource.onerror = (err) => {
            setError('Error connecting to log stream');
            eventSource.close();
        };

        setLoading(false);

        return () => {
            eventSource.close();
        };
    }, []);

    return { logs, error, loading };
};

export default useLogStream;