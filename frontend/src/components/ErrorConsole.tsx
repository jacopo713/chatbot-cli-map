"use client";

import React, { useState, useEffect, useRef } from 'react';

interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'error' | 'api' | 'info' | 'warning';
  message: string;
  source: string;
  details?: any;
  duration?: number;
}

interface ErrorConsoleProps {
  isVisible: boolean;
  onClose: () => void;
}

const ErrorConsole: React.FC<ErrorConsoleProps> = ({ isVisible, onClose }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'error' | 'api' | 'info' | 'warning'>('all');
  const logCounter = useRef(0);

  useEffect(() => {
    const originalFetch = window.fetch;
    
    window.fetch = async function(input: RequestInfo | URL, init?: RequestInit) {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      const method = init?.method || 'GET';
      const startTime = Date.now();
      const logId = `api-${Date.now()}-${++logCounter.current}`;
      
      const startLog: LogEntry = {
        id: logId,
        timestamp: new Date(),
        type: 'api',
        message: `${method} ${url}`,
        source: 'API',
        details: {
          url,
          method,
          headers: init?.headers,
          body: init?.body
        }
      };
      
      setLogs(prev => [startLog, ...prev]);
      
      try {
        const response = await originalFetch(input, init);
        const duration = Date.now() - startTime;
        const status = response.status;
        
        const responseLog: LogEntry = {
          id: `${logId}-response-${++logCounter.current}`,
          timestamp: new Date(),
          type: status >= 400 ? 'error' : 'api',
          message: `${method} ${url} - ${status} (${duration}ms)`,
          source: 'API',
          details: {
            url,
            method,
            status,
            duration,
            headers: Object.fromEntries(response.headers.entries()),
          },
          duration
        };
        
        setLogs(prev => [responseLog, ...prev]);
        return response;
      } catch (error) {
        const duration = Date.now() - startTime;
        
        const errorLog: LogEntry = {
          id: `${logId}-error-${++logCounter.current}`,
          timestamp: new Date(),
          type: 'error',
          message: `${method} ${url} - Error (${duration}ms)`,
          source: 'API',
          details: {
            url,
            method,
            error: error instanceof Error ? error.message : String(error),
            duration
          },
          duration
        };
        
        setLogs(prev => [errorLog, ...prev]);
        throw error;
      }
    };
    
    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      const newLog: LogEntry = {
        id: `error-${Date.now()}-${++logCounter.current}`,
        timestamp: new Date(),
        type: 'error',
        message: event.message,
        source: `${event.filename}:${event.lineno}:${event.colno}`,
        details: {
          stack: event.error?.stack,
          error: event.error
        }
      };
      
      setLogs(prev => [newLog, ...prev]);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const newLog: LogEntry = {
        id: `promise-${Date.now()}-${++logCounter.current}`,
        timestamp: new Date(),
        type: 'error',
        message: `Unhandled Promise Rejection: ${event.reason}`,
        source: 'Promise',
        details: {
          reason: event.reason
        }
      };
      
      setLogs(prev => [newLog, ...prev]);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  useEffect(() => {
    (window as any).addDevLog = (message: string, type: LogEntry['type'] = 'info', source = 'App', details?: any) => {
      const newLog: LogEntry = {
        id: `manual-${Date.now()}-${++logCounter.current}`,
        timestamp: new Date(),
        type,
        message,
        source,
        details
      };
      
      setLogs(prev => [newLog, ...prev]);
    };
    
    return () => {
      delete (window as any).addDevLog;
    };
  }, []);

  const clearLogs = () => {
    setLogs([]);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString();
  };

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.type === filter);

  if (!isVisible) return null;

  const getIcon = (type: LogEntry['type']) => {
    switch (type) {
      case 'error':
        return (
          <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      case 'api':
        return (
          <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'info':
      default:
        return (
          <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const getBgColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'error': return 'bg-red-50';
      case 'api': return 'bg-blue-50';
      case 'warning': return 'bg-yellow-50';
      case 'info': return 'bg-green-50';
      default: return 'bg-gray-50';
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose}></div>
        
        <section className="absolute inset-y-0 right-0 max-w-full flex">
          <div className="relative w-screen max-w-md">
            <div className="h-full flex flex-col bg-white shadow-xl">
              <div className="flex-1 overflow-y-auto py-6">
                <div className="px-4 sm:px-6">
                  <div className="flex items-start justify-between">
                    <h2 className="text-lg font-medium text-gray-900">Console di Sviluppo</h2>
                    <div className="ml-3 h-7 flex items-center">
                      <button
                        type="button"
                        className="bg-white rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onClick={onClose}
                      >
                        <span className="sr-only">Chiudi pannello</span>
                        <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 relative flex-1 px-4 sm:px-6">
                  <div className="absolute inset-0 px-4 sm:px-6">
                    <div className="h-full border-2 border-dashed border-gray-200" aria-hidden="true"></div>
                  </div>
                  
                  <div className="relative">
                    <div className="flex justify-between items-center mb-4">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setFilter('all')}
                          className={`px-3 py-1 text-xs rounded ${filter === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                        >
                          Tutti
                        </button>
                        <button
                          onClick={() => setFilter('error')}
                          className={`px-3 py-1 text-xs rounded ${filter === 'error' ? 'bg-red-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                        >
                          Errori
                        </button>
                        <button
                          onClick={() => setFilter('api')}
                          className={`px-3 py-1 text-xs rounded ${filter === 'api' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                        >
                          API
                        </button>
                        <button
                          onClick={() => setFilter('warning')}
                          className={`px-3 py-1 text-xs rounded ${filter === 'warning' ? 'bg-yellow-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                        >
                          Warning
                        </button>
                        <button
                          onClick={() => setFilter('info')}
                          className={`px-3 py-1 text-xs rounded ${filter === 'info' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                        >
                          Info
                        </button>
                      </div>
                      
                      <button
                        onClick={clearLogs}
                        className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        Cancella
                      </button>
                    </div>
                    
                    <div className="bg-white border border-gray-200 rounded-lg shadow overflow-hidden">
                      <ul className="-mb-4">
                        {filteredLogs.map((log) => (
                          <li key={log.id} className="py-4">
                            <div className="px-4">
                              <div className="flex items-start">
                                <div className="flex-shrink-0">
                                  {getIcon(log.type)}
                                </div>
                                <div className="ml-3 flex-1">
                                  <div className="flex justify-between">
                                    <p className={`text-sm font-medium ${getBgColor(log.type)} px-2 py-1 rounded`}>
                                      {log.message}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                      {formatTime(log.timestamp)}
                                    </p>
                                  </div>
                                  <div className="mt-1 text-xs text-gray-500 flex justify-between">
                                    <span>{log.source}</span>
                                    {log.duration !== undefined && (
                                      <span>{log.duration}ms</span>
                                    )}
                                  </div>
                                  
                                  {log.details && (
                                    <div className="mt-2">
                                      <button
                                        onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                                        className="text-xs text-blue-600 hover:text-blue-800"
                                      >
                                        {expandedLog === log.id ? 'Nascondi dettagli' : 'Mostra dettagli'}
                                      </button>
                                      
                                      {expandedLog === log.id && (
                                        <div className="mt-2 p-2 bg-gray-100 rounded text-xs font-mono overflow-x-auto">
                                          <pre>{JSON.stringify(log.details, null, 2)}</pre>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                      
                      {filteredLogs.length === 0 && (
                        <div className="py-8 text-center">
                          <p className="text-gray-500">Nessun log da visualizzare</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default ErrorConsole;
