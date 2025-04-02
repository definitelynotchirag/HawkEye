import { formatDistanceToNow } from 'date-fns';

export const formatTimestamp = (timestamp) => {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
};

export const formatLatency = (latency) => {
    return `${latency} ms`;
};

export const formatRequestSize = (size) => {
    return size < 1024 ? `${size} bytes` : `${(size / 1024).toFixed(2)} KB`;
};

export const formatStatusCode = (statusCode) => {
    if (statusCode >= 200 && statusCode < 300) {
        return 'Success';
    } else if (statusCode >= 400 && statusCode < 500) {
        return 'Client Error';
    } else if (statusCode >= 500) {
        return 'Server Error';
    }
    return 'Unknown Status';
};