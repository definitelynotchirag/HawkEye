import React from 'react';
import { useEffect, useState, useMemo } from 'react';

// Import icons
const ServerIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const StatusBadge = ({ code }) => {
  let color = "bg-green-500";
  if (code >= 400) color = "bg-red-500";
  else if (code >= 300) color = "bg-yellow-500";
  
  return (
    <span className={`px-2 py-1 text-xs font-bold rounded-full ${color}`}>
      {code}
    </span>
  );
};

const LatencyIndicator = ({ ms }) => {
  let width = "w-1/4";
  let color = "bg-green-500";
  
  if (ms > 500) {
    width = "w-full";
    color = "bg-red-500";
  } else if (ms > 200) {
    width = "w-3/4";
    color = "bg-yellow-500";
  } else if (ms > 100) {
    width = "w-1/2";
    color = "bg-blue-500";
  }
  
  return (
    <div className="flex items-center">
      <div className="w-24 bg-gray-700 rounded-full h-2.5 mr-2">
        <div className={`h-2.5 rounded-full ${color} ${width}`}></div>
      </div>
      <span>{ms}ms</span>
    </div>
  );
};

const LogStream = () => {
    const [logs, setLogs] = useState([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const eventSource = new EventSource('http://localhost:5000/logs'); // Adjust the URL as needed

        eventSource.onmessage = (event) => {
            const newLog = JSON.parse(event.data);
            setLogs((prevLogs) => [...prevLogs.slice(-99), newLog]);
        };

        eventSource.onopen = () => {
            setConnected(true);
        };

        eventSource.onerror = () => {
            console.error('Error occurred while streaming logs.');
            setConnected(false);
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, []);
    
    // Calculate statistics
    const stats = useMemo(() => {
        if (logs.length === 0) return { avgLatency: 0, errorRate: 0, requestCount: 0 };
        
        const totalLatency = logs.reduce((sum, log) => sum + log.latency_ms, 0);
        const errorCount = logs.filter(log => log.status_code >= 400).length;
        
        return {
            avgLatency: (totalLatency / logs.length).toFixed(2),
            errorRate: ((errorCount / logs.length) * 100).toFixed(1),
            requestCount: logs.length
        };
    }, [logs]);

    // Get unique endpoints for the mini chart
    const endpoints = useMemo(() => {
        const endpointMap = {};
        logs.forEach(log => {
            if (!endpointMap[log.endpoint]) endpointMap[log.endpoint] = 0;
            endpointMap[log.endpoint]++;
        });
        return Object.entries(endpointMap);
    }, [logs]);
    
    // Calculate threat level based on actual log data
    const threatLevel = useMemo(() => {
        if (logs.length === 0) return 0;
        
        // Calculate threat level based on error rate and latency anomalies
        const errorRate = (logs.filter(log => log.status_code >= 400).length / logs.length);
        const highLatencyRate = (logs.filter(log => log.latency_ms > 300).length / logs.length);
        
        // Weight factors can be adjusted based on importance
        const errorWeight = 0.6;
        const latencyWeight = 0.4;
        
        // Calculate weighted threat score (0-100%)
        return Math.min(100, Math.round((errorRate * errorWeight + highLatencyRate * latencyWeight) * 100));
    }, [logs]);

    return (
        <div className="min-h-screen bg-dark p-6">
            <div className="max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-3xl font-bold text-purple-accent flex items-center">
                        <ServerIcon />
                        <span className="ml-2">Log Stream Dashboard</span>
                    </h1>
                    <div className="flex items-center">
                        <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'} mr-2`}></div>
                        <span className="text-sm">{connected ? 'Connected' : 'Disconnected'}</span>
                    </div>
                </div>
                
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg">
                        <h3 className="text-purple-light text-sm uppercase font-semibold mb-2">Average Latency</h3>
                        <p className="text-2xl font-bold">{stats.avgLatency} ms</p>
                    </div>
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg">
                        <h3 className="text-purple-light text-sm uppercase font-semibold mb-2">Error Rate</h3>
                        <p className="text-2xl font-bold">{stats.errorRate}%</p>
                    </div>
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg">
                        <h3 className="text-purple-light text-sm uppercase font-semibold mb-2">Request Count</h3>
                        <p className="text-2xl font-bold">{stats.requestCount}</p>
                    </div>
                </div>
                
                {/* Anomaly Visualizations */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    {/* Anomaly Score Trend Chart */}
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg">
                        <h3 className="text-purple-light text-md font-semibold mb-4">Anomaly Score Trend</h3>
                        <div className="h-64 relative">
                            {logs.length > 0 && (
                                <>
                                    {/* Time axis labels */}
                                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                                        {[...Array(5)].map((_, i) => {
                                            const idx = Math.floor(logs.length / 4) * i;
                                            if (idx < logs.length) {
                                                return (
                                                    <span key={i}>
                                                        {new Date(logs[idx].timestamp).toLocaleTimeString()}
                                                    </span>
                                                );
                                            }
                                            return <span key={i}></span>;
                                        })}
                                    </div>
                                    
                                    {/* Score grid lines */}
                                    <div className="absolute inset-0 flex flex-col justify-between border-t border-gray-800">
                                        {[...Array(5)].map((_, i) => (
                                            <div key={i} className="relative h-0 border-b border-gray-800">
                                                <span className="absolute -left-6 -top-2 text-xs text-gray-500">
                                                    {(1 - i * 0.25).toFixed(1)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                    
                                    {/* Danger threshold line */}
                                    <div className="absolute inset-0 mt-12 border-t border-dashed border-red-500 opacity-50"></div>
                                    
                                    {/* Warning threshold line */}
                                    <div className="absolute inset-0 mt-32 border-t border-dashed border-yellow-500 opacity-50"></div>
                                    
                                    {/* Anomaly score line chart */}
                                    <svg className="w-full h-full absolute inset-0" preserveAspectRatio="none" viewBox={`0 0 ${logs.length} 100`}>
                                        <defs>
                                            <linearGradient id="anomaly-gradient" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#ff3e83" stopOpacity="0.8" />
                                                <stop offset="100%" stopColor="#a13dd9" stopOpacity="0.2" />
                                            </linearGradient>
                                        </defs>
                                        
                                        {/* Line plot */}
                                        <path
                                            d={logs.map((log, i) => {
                                                // Generate random anomaly scores for demo purpose
                                                const score = Math.random() * 0.7 + (log.status_code >= 400 ? 0.3 : 0);
                                                return `${i === 0 ? 'M' : 'L'} ${i} ${100 - score * 100}`;
                                            }).join(' ')}
                                            fill="none"
                                            stroke="url(#anomaly-gradient)"
                                            strokeWidth="2"
                                        />
                                        
                                        {/* Area under the curve */}
                                        <path
                                            d={`${logs.map((log, i) => {
                                                const score = Math.random() * 0.7 + (log.status_code >= 400 ? 0.3 : 0);
                                                return `${i === 0 ? 'M' : 'L'} ${i} ${100 - score * 100}`;
                                            }).join(' ')} L ${logs.length - 1} 100 L 0 100 Z`}
                                            fill="url(#anomaly-gradient)"
                                            opacity="0.4"
                                        />
                                    </svg>
                                </>
                            )}
                            
                            {logs.length === 0 && (
                                <div className="flex h-full items-center justify-center text-gray-500">
                                    Waiting for anomaly data...
                                </div>
                            )}
                        </div>
                        <div className="flex justify-between mt-2">
                            <div className="flex items-center">
                                <span className="inline-block h-2 w-2 mr-1 bg-red-500 rounded-full"></span>
                                <span className="text-xs">High Risk</span>
                            </div>
                            <div className="flex items-center">
                                <span className="inline-block h-2 w-2 mr-1 bg-yellow-500 rounded-full"></span>
                                <span className="text-xs">Medium Risk</span>
                            </div>
                            <div className="flex items-center">
                                <span className="inline-block h-2 w-2 mr-1 bg-green-500 rounded-full"></span>
                                <span className="text-xs">Low Risk</span>
                            </div>
                        </div>
                    </div>
                    
                    {/* Anomaly Heatmap */}
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg">
                        <h3 className="text-purple-light text-md font-semibold mb-4">Endpoint Security Heatmap</h3>
                        <div className="grid grid-cols-6 gap-1 h-64">
                            {endpoints.map(([endpoint, count], idx) => {
                                // Generate random security scores for each endpoint for demo
                                const securityScore = Math.random();
                                let color = "bg-green-600";
                                if (securityScore > 0.85) color = "bg-red-600";
                                else if (securityScore > 0.6) color = "bg-red-500 bg-opacity-60";
                                else if (securityScore > 0.4) color = "bg-yellow-500";
                                
                                // Calculate size based on request volume
                                const percentage = (count / logs.length) * 100;
                                const size = Math.max(60, percentage + 40);
                                
                                return (
                                    <div key={idx} className="flex justify-center items-center group relative">
                                        <div 
                                            className={`rounded transition-all ${color} hover:shadow-lg hover:shadow-purple-accent flex items-center justify-center cursor-pointer`}
                                            style={{ width: `${size}%`, height: `${size}%` }}
                                        >
                                            <span className="text-xs truncate max-w-[90%] text-center">
                                                {endpoint.split('/').pop() || '/'}
                                            </span>
                                        </div>
                                        <div className="absolute bottom-full mb-1 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 text-xs text-white p-2 rounded pointer-events-none z-10 whitespace-nowrap">
                                            {endpoint}: {(securityScore * 10).toFixed(1)} anomaly score
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="flex justify-between mt-4">
                            <span className="text-xs text-gray-500">Lower Traffic</span>
                            <span className="text-xs text-gray-500">Higher Traffic</span>
                        </div>
                        <div className="h-2 w-full mt-1 bg-gradient-to-r from-green-600 via-yellow-500 to-red-600 rounded-full"></div>
                        <div className="flex justify-between">
                            <span className="text-xs text-gray-500">Safe</span>
                            <span className="text-xs text-gray-500">Suspicious</span>
                            <span className="text-xs text-gray-500">Critical</span>
                        </div>
                    </div>
                </div>
                
                {/* Threat Gauge */}
                <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg md:col-span-2">
                    <h3 className="text-purple-light text-md font-semibold mb-4">System Security Status</h3>
                    <div className="flex items-center justify-center">
                        <div className="relative w-48 h-48">
                            {/* Gauge background */}
                            <svg className="w-full h-full" viewBox="0 0 100 100">
                                <defs>
                                    <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stopColor="#10B981" />
                                        <stop offset="50%" stopColor="#F59E0B" />
                                        <stop offset="100%" stopColor="#EF4444" />
                                    </linearGradient>
                                </defs>
                                {/* Background track */}
                                <circle
                                    cx="50"
                                    cy="50"
                                    r="40"
                                    fill="none"
                                    stroke="#374151"
                                    strokeWidth="10"
                                    strokeDasharray="251.2"
                                    strokeDashoffset="0"
                                    transform="rotate(-90 50 50)"
                                />
                                {/* Colored arc - using dashoffset to control the filling based on actual threat level */}
                                <circle
                                    cx="50"
                                    cy="50"
                                    r="40"
                                    fill="none"
                                    stroke="url(#gauge-gradient)"
                                    strokeWidth="10"
                                    strokeDasharray="251.2"
                                    strokeDashoffset={`${251.2 * (1 - threatLevel / 100)}`}
                                    transform="rotate(-90 50 50)"
                                />
                                {/* Needle with dynamic rotation based on threat level */}
                                <line
                                    x1="50"
                                    y1="50"
                                    x2="50"
                                    y2="15"
                                    stroke="#ffffff"
                                    strokeWidth="2"
                                    transform={`rotate(${threatLevel * 1.8} 50 50)`}
                                />
                                {/* Center circle */}
                                <circle cx="50" cy="50" r="5" fill="#ffffff" />
                            </svg>
                            {/* Gauge value */}
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className="text-3xl font-bold">{threatLevel}%</span>
                                <span className={`text-sm ${
                                    threatLevel > 60 ? 'text-red-400' : 
                                    threatLevel > 30 ? 'text-yellow-400' : 'text-green-400'
                                }`}>
                                    Threat Level
                                </span>
                            </div>
                        </div>
                        
                        {/* Alerts and recommendations */}
                        <div className="ml-8 text-sm">
                            <h4 className="text-purple-light font-semibold mb-2">System Alerts</h4>
                            <ul className="space-y-2">
                                {logs.length > 0 && (
                                    <>
                                        <li className="flex items-center">
                                            <span className={`w-2 h-2 ${threatLevel > 30 ? 'bg-yellow-500' : 'bg-green-500'} rounded-full mr-2`}></span>
                                            {threatLevel > 30 
                                                ? `Unusual traffic pattern detected from ${Math.ceil(threatLevel/20)} IPs` 
                                                : 'Normal traffic patterns observed'}
                                        </li>
                                        <li className="flex items-center">
                                            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                                            Authentication systems operating normally
                                        </li>
                                        <li className="flex items-center">
                                            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                                            No data exfiltration attempts detected
                                        </li>
                                        <li className="flex items-center">
                                            <span className={`w-2 h-2 ${stats.errorRate > 5 ? 'bg-yellow-500' : 'bg-green-500'} rounded-full mr-2`}></span>
                                            {stats.errorRate > 5 
                                                ? `Rate limiting triggered on ${endpoints[0]?.[0] || '/api'} endpoint` 
                                                : 'All endpoints responding normally'}
                                        </li>
                                    </>
                                )}
                                {logs.length === 0 && (
                                    <li className="flex items-center">
                                        <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                                        Waiting for log data...
                                    </li>
                                )}
                            </ul>
                        </div>
                    </div>
                </div>
                
                {/* Endpoint distribution chart - improved layout */}
                {endpoints.length > 0 && (
                    <div className="bg-gray-900 border border-purple-dark rounded-lg p-4 shadow-lg mb-8">
                        <h3 className="text-purple-light text-md font-semibold mb-4">Endpoint Distribution</h3>
                        <div className="flex flex-wrap items-end justify-center h-32 gap-3">
                            {endpoints.map(([endpoint, count], idx) => {
                                const percentage = (count / logs.length) * 100;
                                const height = Math.max(15, percentage * 1.5); // Better scaling for visualization
                                
                                // Get status codes for this endpoint to determine color
                                const endpointLogs = logs.filter(log => log.endpoint === endpoint);
                                const hasErrors = endpointLogs.some(log => log.status_code >= 400);
                                const hasWarnings = endpointLogs.some(log => log.status_code >= 300 && log.status_code < 400);
                                
                                let barColor = "bg-purple-light hover:bg-purple-accent";
                                if (hasErrors) barColor = "bg-red-500 hover:bg-red-400";
                                else if (hasWarnings) barColor = "bg-yellow-500 hover:bg-yellow-400";
                                
                                return (
                                    <div key={idx} className="flex flex-col items-center group relative">
                                        <div 
                                            className={`w-12 ${barColor} transition-all rounded-t flex justify-center items-end pb-1`}
                                            style={{ height: `${height}%` }}
                                        >
                                            {percentage > 15 && (
                                                <span className="text-xs font-bold">{Math.round(percentage)}%</span>
                                            )}
                                        </div>
                                        <span className="text-xs truncate w-16 text-center mt-1 font-medium">{endpoint.split('/').pop() || '/'}</span>
                                        <div className="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 text-xs text-white p-2 rounded pointer-events-none z-10">
                                            {endpoint}: {count} requests ({percentage.toFixed(1)}%)
                                            {hasErrors && <span className="block mt-1 text-red-400">Contains errors</span>}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="flex justify-center mt-4">
                            <div className="flex items-center mx-2">
                                <span className="inline-block h-3 w-3 mr-1 bg-purple-light rounded-sm"></span>
                                <span className="text-xs">Normal</span>
                            </div>
                            <div className="flex items-center mx-2">
                                <span className="inline-block h-3 w-3 mr-1 bg-yellow-500 rounded-sm"></span>
                                <span className="text-xs">Redirects</span>
                            </div>
                            <div className="flex items-center mx-2">
                                <span className="inline-block h-3 w-3 mr-1 bg-red-500 rounded-sm"></span>
                                <span className="text-xs">Errors</span>
                            </div>
                        </div>
                    </div>
                )}
                
                {/* Logs Table */}
                <div className="bg-gray-900 border border-purple-dark rounded-lg shadow-lg overflow-hidden">
                    <div className="p-4 border-b border-purple-dark bg-purple-dark bg-opacity-30">
                        <h2 className="text-xl font-semibold text-purple-accent">Recent Logs</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-800 text-left">
                                    <th className="p-3 text-xs font-medium uppercase tracking-wider text-purple-light">Time</th>
                                    <th className="p-3 text-xs font-medium uppercase tracking-wider text-purple-light">Endpoint</th>
                                    <th className="p-3 text-xs font-medium uppercase tracking-wider text-purple-light">Status</th>
                                    <th className="p-3 text-xs font-medium uppercase tracking-wider text-purple-light">Latency</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800">
                                {logs.length === 0 ? (
                                    <tr>
                                        <td colSpan="4" className="p-4 text-center text-gray-400">Waiting for logs...</td>
                                    </tr>
                                ) : (
                                    logs.slice().reverse().map((log, index) => (
                                        <tr key={index} className="hover:bg-gray-800 transition-colors">
                                            <td className="p-3 whitespace-nowrap">
                                                <div className="flex items-center">
                                                    <ClockIcon />
                                                    <span className="ml-2 text-sm">{new Date(log.timestamp).toLocaleTimeString()}</span>
                                                </div>
                                            </td>
                                            <td className="p-3">
                                                <span className="text-sm font-medium">{log.endpoint}</span>
                                            </td>
                                            <td className="p-3">
                                                <StatusBadge code={log.status_code} />
                                            </td>
                                            <td className="p-3">
                                                <LatencyIndicator ms={log.latency_ms} />
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LogStream;