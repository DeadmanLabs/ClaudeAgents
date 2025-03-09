import { useRef, useEffect } from 'react';

interface Log {
  type: string;
  message: string;
  timestamp: string;
}

interface LogViewerProps {
  logs: Log[];
}

export default function LogViewer({ logs }: LogViewerProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Format the timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  // Get style class based on log type
  const getLogClass = (type: string) => {
    switch (type) {
      case 'stderr':
        return 'text-red-500';
      case 'error':
        return 'text-red-500 font-bold';
      default:
        return 'text-foreground';
    }
  };

  return (
    <div
      ref={logContainerRef}
      className="h-full overflow-auto font-mono text-xs p-2 bg-muted rounded"
    >
      {logs.length === 0 ? (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          No logs available. Start the agents to see logs.
        </div>
      ) : (
        logs.map((log, index) => (
          <div key={index} className={`mb-1 ${getLogClass(log.type)}`}>
            <span className="text-muted-foreground mr-2">[{formatTime(log.timestamp)}]</span>
            {log.message}
          </div>
        ))
      )}
    </div>
  );
}