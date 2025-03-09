import { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import LanguageSelector from './components/LanguageSelector';
import GraphView from './components/GraphView';
import CodeViewer from './components/CodeViewer';
import LogViewer from './components/LogViewer';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs';

interface AgentState {
  currentLanguage: string;
  activeFile: {
    path: string;
    content: string;
    language: string;
  } | null;
  logs: {
    type: string;
    message: string;
    timestamp: string;
  }[];
  graphData: {
    nodes: {
      id: string;
      name: string;
      type: string;
    }[];
    links: {
      source: string;
      target: string;
    }[];
  };
  isRunning: boolean;
}

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [state, setState] = useState<AgentState>({
    currentLanguage: 'python',
    activeFile: null,
    logs: [],
    graphData: { nodes: [], links: [] },
    isRunning: false
  });
  const [prompt, setPrompt] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const newSocket = io(import.meta.env.VITE_API_URL || 'http://localhost:3000');
    
    newSocket.on('connect', () => {
      console.log('Connected to server');
    });
    
    newSocket.on('state', (newState: AgentState) => {
      setState(newState);
    });
    
    newSocket.on('log', (log: { type: string; message: string }) => {
      setState(prev => ({
        ...prev,
        logs: [...prev.logs, { ...log, timestamp: new Date().toISOString() }]
      }));
    });
    
    newSocket.on('fileSelected', (file) => {
      setState(prev => ({ ...prev, activeFile: file }));
    });
    
    newSocket.on('error', (errorMessage: string) => {
      setError(errorMessage);
      setTimeout(() => setError(null), 5000);
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.disconnect();
    };
  }, []);

  const handleLanguageChange = (language: string) => {
    if (socket) {
      socket.emit('changeLanguage', language);
    }
  };

  const handleRunAgent = () => {
    if (socket && prompt.trim() && !state.isRunning) {
      socket.emit('runAgent', prompt);
    } else if (!prompt.trim()) {
      setError('Please enter a prompt');
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleSelectFile = (filePath: string) => {
    if (socket) {
      socket.emit('selectFile', filePath);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Header */}
      <header className="bg-primary text-primary-foreground p-4 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold">Claude Agents Dashboard</h1>
          <LanguageSelector
            currentLanguage={state.currentLanguage}
            onChange={handleLanguageChange}
            disabled={state.isRunning}
          />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 container mx-auto p-4 flex flex-col gap-4">
        {/* Error message */}
        {error && (
          <div className="bg-destructive text-destructive-foreground p-2 rounded mb-4">
            {error}
          </div>
        )}

        {/* Prompt input */}
        <div className="grid grid-cols-6 gap-2">
          <div className="col-span-5">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter a prompt for the agents..."
              className="w-full p-2 border rounded"
              disabled={state.isRunning}
            />
          </div>
          <button
            onClick={handleRunAgent}
            disabled={state.isRunning || !prompt.trim()}
            className="col-span-1 bg-primary text-primary-foreground p-2 rounded disabled:opacity-50"
          >
            {state.isRunning ? 'Running...' : 'Run Agents'}
          </button>
        </div>

        {/* Main content split */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[calc(100vh-300px)]">
          {/* Left side - Graph */}
          <div className="border rounded p-4 bg-card text-card-foreground h-full overflow-hidden">
            <h2 className="text-lg font-medium mb-2">Agent Graph</h2>
            <GraphView graphData={state.graphData} isRunning={state.isRunning} />
          </div>

          {/* Right side - Code viewer */}
          <div className="border rounded p-4 bg-card text-card-foreground h-full overflow-hidden">
            <Tabs defaultValue="code">
              <TabsList className="mb-2">
                <TabsTrigger value="code">Current File</TabsTrigger>
                <TabsTrigger value="files">File Browser</TabsTrigger>
              </TabsList>
              <TabsContent value="code" className="h-[calc(100%-40px)] overflow-hidden">
                <CodeViewer file={state.activeFile} />
              </TabsContent>
              <TabsContent value="files" className="h-[calc(100%-40px)] overflow-auto">
                <FileBrowser onSelectFile={handleSelectFile} socket={socket} />
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Bottom - Logs */}
        <div className="border rounded p-4 bg-card text-card-foreground h-64 overflow-hidden">
          <h2 className="text-lg font-medium mb-2">Agent Logs</h2>
          <LogViewer logs={state.logs} />
        </div>
      </main>
    </div>
  );
}

interface FileBrowserProps {
  onSelectFile: (path: string) => void;
  socket: Socket | null;
}

function FileBrowser({ onSelectFile, socket }: FileBrowserProps) {
  const [currentDir, setCurrentDir] = useState('./');
  const [files, setFiles] = useState<string[]>([]);

  useEffect(() => {
    if (socket) {
      socket.emit('getFiles', currentDir);
      
      const handleFileList = ({ directory, files }: { directory: string, files: string[] }) => {
        if (directory === currentDir) {
          setFiles(files);
        }
      };
      
      socket.on('fileList', handleFileList);
      
      return () => {
        socket.off('fileList', handleFileList);
      };
    }
  }, [currentDir, socket]);

  const navigateToParent = () => {
    const parent = currentDir.split('/').slice(0, -1).join('/') || './';
    setCurrentDir(parent);
  };

  const handleClick = (item: string) => {
    const path = `${currentDir}/${item}`.replace(/\/\//g, '/');
    if (item.includes('.')) {
      onSelectFile(path);
    } else {
      setCurrentDir(path);
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="mb-2 flex items-center">
        <button 
          onClick={navigateToParent}
          className="mr-2 px-2 py-1 bg-secondary text-secondary-foreground rounded text-sm"
        >
          ..
        </button>
        <span className="text-sm truncate">{currentDir}</span>
      </div>
      <ul className="space-y-1">
        {files.map((file) => (
          <li 
            key={file} 
            className="p-2 hover:bg-accent hover:text-accent-foreground rounded cursor-pointer text-sm"
            onClick={() => handleClick(file)}
          >
            {file}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;