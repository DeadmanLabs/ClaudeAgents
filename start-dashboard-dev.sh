#!/bin/bash

# Define paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_PATH="$REPO_ROOT/dashboard"
DASHBOARD_API_PATH="$REPO_ROOT/dashboard-api"

# Check if the dashboard API directory exists, if not create it
if [ ! -d "$DASHBOARD_API_PATH" ]; then
  echo "Creating dashboard API directory..."
  mkdir -p "$DASHBOARD_API_PATH/src"
fi

# Go to the API directory and set up package.json if it doesn't exist
if [ ! -f "$DASHBOARD_API_PATH/package.json" ]; then
  echo "Setting up dashboard API package.json..."
  cat > "$DASHBOARD_API_PATH/package.json" << 'EOL'
{
  "name": "claude-agents-dashboard-api",
  "version": "0.1.0",
  "description": "API server for Claude Agents Dashboard",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "socket.io": "^4.7.2"
  }
}
EOL
fi

# Create or update index.js in src directory
echo "Setting up dashboard API server code..."
cat > "$DASHBOARD_API_PATH/src/index.js" << 'EOL'
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
    origin: ["http://localhost:5173", "http://127.0.0.1:5173"],
    methods: ['GET', 'POST'],
    credentials: true
  },
  allowEIO3: true,
  transports: ['websocket', 'polling']
});

app.use(cors({
  origin: ["http://localhost:5173", "http://127.0.0.1:5173"],
  credentials: true
}));
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

// Root directory
const rootDir = path.resolve(__dirname, '../../');

// Socket.IO connection
io.on('connection', (socket) => {
  console.log('Client connected');
  
  // Send initial state
  socket.emit('state', state);
  
  // Handle language change
  socket.on('changeLanguage', (language) => {
    console.log(`Changing language to ${language}`);
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
    state.graphData = { nodes: [], links: [] }; // Reset component graph
    state.activeFile = null; // Reset active file
    io.emit('state', state);
    
    try {
      // Determine the correct path based on language
      const scriptPath = state.currentLanguage === 'python' 
        ? path.join(rootDir, 'python/src/main.py')
        : path.join(rootDir, 'javascript/src/index.js');
      
      console.log(`Running agent with ${state.currentLanguage} script: ${scriptPath}`);
      console.log(`Prompt: ${prompt}`);
      
      let agentProcess;
      if (state.currentLanguage === 'python') {
        // Pass a flag to enable dashboard output mode
        agentProcess = spawn('python', [scriptPath, prompt, '--dashboard-mode'], { cwd: rootDir });
      } else {
        agentProcess = spawn('node', [scriptPath, prompt, '--dashboard-mode'], { cwd: rootDir });
      }
      
      agentProcess.stdout.on('data', (data) => {
        const logText = data.toString();
        console.log(`[STDOUT] ${logText}`);
        
        // Check if the output contains special JSON markers for dashboard updates
        if (logText.includes('DASHBOARD_UPDATE:')) {
          try {
            // Extract the JSON part from the output
            const jsonStartIndex = logText.indexOf('DASHBOARD_UPDATE:') + 'DASHBOARD_UPDATE:'.length;
            const jsonStr = logText.substring(jsonStartIndex).trim();
            console.log(`Found dashboard update marker. JSON string: ${jsonStr.substring(0, 100)}...`);
            
            const updateData = JSON.parse(jsonStr);
            console.log(`Update type: ${updateData.type}`);
            
            // Handle different types of updates
            if (updateData.type === 'componentGraph') {
              console.log(`Received component graph update with ${updateData.data.nodes?.length || 0} nodes and ${updateData.data.links?.length || 0} links`);
              // Update the component graph from the planner
              state.graphData = updateData.data;
              io.emit('state', state);
            } else if (updateData.type === 'fileChange') {
              console.log(`Received file change update for ${updateData.filePath}`);
              // Update the active file being edited
              state.activeFile = {
                path: updateData.filePath,
                content: updateData.content,
                language: path.extname(updateData.filePath).substring(1)
              };
              io.emit('fileSelected', state.activeFile);
            }
          } catch (err) {
            console.error('Error parsing dashboard update:', err);
            console.error('JSON string that caused the error:', logText.substring(
              logText.indexOf('DASHBOARD_UPDATE:') + 'DASHBOARD_UPDATE:'.length,
              logText.indexOf('DASHBOARD_UPDATE:') + 'DASHBOARD_UPDATE:'.length + 200
            ));
          }
        }
        
        // Always add to logs
        state.logs.push({ type: 'stdout', message: logText, timestamp: new Date().toISOString() });
        io.emit('log', { type: 'stdout', message: logText });
      });
      
      agentProcess.stderr.on('data', (data) => {
        const log = data.toString();
        console.log(`[STDERR] ${log}`);
        state.logs.push({ type: 'stderr', message: log, timestamp: new Date().toISOString() });
        io.emit('log', { type: 'stderr', message: log });
      });
      
      agentProcess.on('close', (code) => {
        console.log(`Agent process exited with code ${code}`);
        state.isRunning = false;
        io.emit('agentComplete', { code });
        io.emit('state', state);
      });
    } catch (error) {
      console.error('Error running agent:', error);
      state.isRunning = false;
      state.logs.push({ type: 'error', message: error.message, timestamp: new Date().toISOString() });
      io.emit('error', error.message);
      io.emit('state', state);
    }
  });
  
  // Handle file selection
  socket.on('selectFile', (filePath) => {
    try {
      // Convert to absolute path if needed
      let fullPath = filePath;
      if (!path.isAbsolute(filePath)) {
        fullPath = path.join(rootDir, filePath);
      }
      
      console.log(`Reading file: ${fullPath}`);
      const content = fs.readFileSync(fullPath, 'utf8');
      state.activeFile = {
        path: filePath,
        content,
        language: path.extname(filePath).substring(1)
      };
      io.emit('fileSelected', state.activeFile);
    } catch (error) {
      console.error('Error reading file:', error);
      socket.emit('error', `Error reading file: ${error.message}`);
    }
  });
  
  // Handle file listing
  socket.on('getFiles', (directory) => {
    try {
      // Convert to absolute path if needed
      let fullPath = directory;
      if (!path.isAbsolute(directory) && directory !== './') {
        fullPath = path.join(rootDir, directory);
      } else if (directory === './') {
        fullPath = rootDir;
      }
      
      console.log(`Listing files in directory: ${fullPath}`);
      const files = fs.readdirSync(fullPath);
      socket.emit('fileList', { directory, files });
    } catch (error) {
      console.error('Error listing files:', error);
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
    let fullPath = directoryPath;
    if (!path.isAbsolute(directoryPath) && directoryPath !== './') {
      fullPath = path.join(rootDir, directoryPath);
    } else if (directoryPath === './') {
      fullPath = rootDir;
    }
    
    const files = fs.readdirSync(fullPath);
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
    let fullPath = filePath;
    if (!path.isAbsolute(filePath)) {
      fullPath = path.join(rootDir, filePath);
    }
    
    const content = fs.readFileSync(fullPath, 'utf8');
    res.json({
      path: filePath,
      content,
      language: path.extname(filePath).substring(1)
    });
  } catch (error) {
    res.status(500).json({ error: `Error reading file: ${error.message}` });
  }
});

// Initialize empty component graph (will be updated by planner agent)
state.graphData = { 
  nodes: [], 
  links: [] 
};

// Start server
const PORT = process.env.PORT || 3000;
const HOST = '0.0.0.0'; // Listen on all IPv4 interfaces
server.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
  console.log(`Root directory: ${rootDir}`);
});
EOL

# Install dependencies for dashboard API
echo "Installing dashboard API dependencies..."
cd "$DASHBOARD_API_PATH"
npm install

# Install Python dependencies to ensure they're available
echo "Installing Python dependencies..."
cd "$REPO_ROOT/python"
pip install -r requirements.txt

# Start the dashboard API server
echo "Starting dashboard API server..."
cd "$DASHBOARD_API_PATH"
node "$DASHBOARD_API_PATH/src/index.js" &
API_PID=$!

# Start the dashboard frontend in development mode
echo "Starting dashboard frontend..."
cd "$DASHBOARD_PATH"
npm run dev &
UI_PID=$!

# Function to handle script termination
function cleanup {
  echo "Shutting down servers..."
  kill $API_PID $UI_PID 2>/dev/null
}

# Register the cleanup function for script termination
trap cleanup EXIT

# Wait for user to terminate
echo ""
echo "Dashboard running - press Ctrl+C to stop"
echo "API Server: http://localhost:3000"
echo "Frontend: http://localhost:5173"
echo ""

# Keep the script running
wait