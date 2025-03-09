const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

app.use(cors());
app.use(express.json());

// Current state storage
const state = {
  currentLanguage: 'python',
  activeFile: null,
  logs: [],
  graphData: {
    nodes: [],
    links: []
  },
  isRunning: false
};

// Socket.IO connection
io.on('connection', (socket) => {
  console.log('Client connected');
  
  // Send initial state
  socket.emit('state', state);
  
  // Handle language change
  socket.on('changeLanguage', (language) => {
    state.currentLanguage = language;
    io.emit('state', state);
  });
  
  // Handle run agent request
  socket.on('runAgent', async (prompt) => {
    if (state.isRunning) {
      socket.emit('error', 'Agent is already running');
      return;
    }
    
    state.isRunning = true;
    state.logs = [];
    io.emit('state', state);
    
    try {
      const scriptPath = state.currentLanguage === 'python' 
        ? 'python/src/main.py' 
        : 'javascript/src/index.js';
      
      let agentProcess;
      if (state.currentLanguage === 'python') {
        agentProcess = spawn('python', [scriptPath, prompt]);
      } else {
        agentProcess = spawn('node', [scriptPath, prompt]);
      }
      
      agentProcess.stdout.on('data', (data) => {
        const log = data.toString();
        state.logs.push({ type: 'stdout', message: log, timestamp: new Date().toISOString() });
        io.emit('log', { type: 'stdout', message: log });
      });
      
      agentProcess.stderr.on('data', (data) => {
        const log = data.toString();
        state.logs.push({ type: 'stderr', message: log, timestamp: new Date().toISOString() });
        io.emit('log', { type: 'stderr', message: log });
      });
      
      agentProcess.on('close', (code) => {
        state.isRunning = false;
        io.emit('agentComplete', { code });
        io.emit('state', state);
      });
    } catch (error) {
      state.isRunning = false;
      state.logs.push({ type: 'error', message: error.message, timestamp: new Date().toISOString() });
      io.emit('error', error.message);
      io.emit('state', state);
    }
  });
  
  // Handle file selection
  socket.on('selectFile', (filePath) => {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      state.activeFile = {
        path: filePath,
        content,
        language: path.extname(filePath).substring(1)
      };
      io.emit('fileSelected', state.activeFile);
    } catch (error) {
      socket.emit('error', `Error reading file: ${error.message}`);
    }
  });
  
  // Handle file listing
  socket.on('getFiles', (directory) => {
    try {
      const files = fs.readdirSync(directory);
      socket.emit('fileList', { directory, files });
    } catch (error) {
      socket.emit('error', `Error listing files: ${error.message}`);
    }
  });
  
  // Disconnect
  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});

// API Routes
app.get('/api/status', (req, res) => {
  res.json({ status: 'ok', currentLanguage: state.currentLanguage, isRunning: state.isRunning });
});

app.get('/api/files', (req, res) => {
  const directoryPath = req.query.path || './';
  try {
    const files = fs.readdirSync(directoryPath);
    res.json({ directory: directoryPath, files });
  } catch (error) {
    res.status(500).json({ error: `Error listing files: ${error.message}` });
  }
});

app.get('/api/file', (req, res) => {
  const filePath = req.query.path;
  if (!filePath) {
    return res.status(400).json({ error: 'File path is required' });
  }
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    res.json({
      path: filePath,
      content,
      language: path.extname(filePath).substring(1)
    });
  } catch (error) {
    res.status(500).json({ error: `Error reading file: ${error.message}` });
  }
});

// Build agent graph data
function buildAgentGraph() {
  const agents = [
    { id: 'manager', name: 'Manager Agent', type: 'manager' },
    { id: 'architecture', name: 'Architecture Designer Agent', type: 'design' },
    { id: 'stack', name: 'Stack Builder Agent', type: 'build' },
    { id: 'library', name: 'Library Researcher Agent', type: 'research' },
    { id: 'planner', name: 'Software Planner Agent', type: 'plan' },
    { id: 'programmer', name: 'Software Programmer Agent', type: 'code' },
    { id: 'debugger', name: 'Exception Debugger Agent', type: 'debug' },
    { id: 'dependency', name: 'Dependency Analyzer Agent', type: 'analyze' }
  ];
  
  const links = [
    { source: 'manager', target: 'architecture' },
    { source: 'manager', target: 'stack' },
    { source: 'manager', target: 'library' },
    { source: 'manager', target: 'planner' },
    { source: 'manager', target: 'programmer' },
    { source: 'manager', target: 'debugger' },
    { source: 'manager', target: 'dependency' },
    { source: 'architecture', target: 'stack' },
    { source: 'library', target: 'planner' },
    { source: 'planner', target: 'programmer' },
    { source: 'programmer', target: 'debugger' },
    { source: 'debugger', target: 'dependency' }
  ];
  
  state.graphData = { nodes: agents, links };
}

// Initialize graph data
buildAgentGraph();

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});