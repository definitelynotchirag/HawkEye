import React from 'react';

const StatusIndicator = ({ status }) => {
    const getStatusColor = (status) => {
        switch (status) {
            case 'normal':
                return 'green';
            case 'warning':
                return 'yellow';
            case 'error':
                return 'red';
            case 'critical':
                return 'darkred';
            default:
                return 'gray';
        }
    };

    return (
        <div style={{ color: getStatusColor(status), fontWeight: 'bold' }}>
            Status: {status.toUpperCase()}
        </div>
    );
};

export default StatusIndicator;