# ClaudeAgents

A multi-agent system with Python and JavaScript implementations for collaborative software development.

## Overview

ClaudeAgents is a dual-implementation framework (Python and JavaScript) that enables multiple specialized AI agents to work together on software development tasks. Each agent focuses on a specific aspect of the development process, from architecture design to debugging, with a central Manager Agent coordinating the workflow.

## Key Features

- **Dual Implementation**: Complete Python and TypeScript versions of the system
- **Multi-Agent Architecture**: Specialized agents for different development tasks
- **Robust Memory Management**: Persistent context management for agents
- **Comprehensive Logging**: Detailed logging of agent activities
- **Real-Time Streaming**: Support for streaming outputs
- **Extensible Design**: Easily add new agent types or capabilities
- **Web Search Capability**: Search and retrieve information from the web
- **File Operations**: Comprehensive file handling utilities

## Agent Types

1. **Manager Agent**: Central coordinator that orchestrates the workflow
2. **Architecture Designer Agent**: Creates infrastructure stack designs
3. **Stack Builder Agent**: Translates designs into installation scripts
4. **Library Researcher Agent**: Researches suitable libraries and dependencies
5. **Software Planner Agent**: Architects code structure and module boundaries
6. **Software Programmer Agent**: Generates code based on the software plan
7. **Exception Debugger Agent**: Tests and fixes issues in the generated code
8. **Dependency Analyzer Agent**: Analyzes and optimizes project dependencies

## Getting Started

### Prerequisites

- Python 3.9+ or Node.js 18+
- API keys for OpenAI or Anthropic (set as environment variables)

### Quick Start

#### First Time Setup

Before running the system for the first time, use the initialization script to set up the environment:

#### On Linux/macOS

```bash
# Make the initialization script executable
chmod +x init.sh

# Run the initialization script
./init.sh
```

#### On Windows

```batch
:: Run the initialization script
init.bat
```

The initialization script will:
1. Check for dependencies (Python, Node.js)
2. Set up virtual environments
3. Install all required packages
4. Create a template .env file for your API keys
5. Create an example prompt file

#### Running the System

After initialization, you can use the provided run scripts:

#### On Linux/macOS

```bash
# Make the script executable
chmod +x run.sh

# Run with Python implementation (default)
./run.sh "Your prompt here"

# Run with JavaScript implementation
./run.sh -l javascript "Your prompt here"

# Run with a prompt from a file
./run.sh -f your_prompt.txt

# Enable verbose logging and persist memory
./run.sh -v -p "Your prompt here"
```

#### On Windows

```batch
:: Run with Python implementation (default)
run.bat "Your prompt here"

:: Run with JavaScript implementation
run.bat -l javascript "Your prompt here"

:: Run with a prompt from a file
run.bat -f your_prompt.txt

:: Enable verbose logging and persist memory
run.bat -v -p "Your prompt here"
```

### Manual Setup and Running

#### Python Implementation

```bash
# Navigate to the Python implementation
cd python

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run with prompt
python src/main.py "Your prompt here"

# Run with prompt from file
python src/main.py --prompt-file your_prompt.txt

# Enable verbose logging
python src/main.py --log-level DEBUG --log-to-file "Your prompt here"
```

#### JavaScript Implementation

```bash
# Navigate to the JavaScript implementation
cd javascript

# Install dependencies
npm install

# Build the project
npm run build

# Run with prompt
npm start "Your prompt here"

# Run with prompt from file
npm start --prompt-file your_prompt.txt

# Enable verbose logging
npm start --log-level debug --log-to-file "Your prompt here"
```

## Environment Variables

Create a `.env` file in the project root or set these environment variables:

```
# Required for AI capabilities - at least one of these must be set
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Project Structure

```
ClaudeAgents/
├── python/                      # Python implementation
│   ├── src/
│   │   ├── agents/              # Agent implementations
│   │   ├── utils/               # Utility functions
│   │   └── main.py              # Entry point
│   ├── tests/                   # Test suite
│   ├── pyproject.toml           # Project configuration
│   └── requirements.txt         # Dependencies list
├── javascript/                  # JavaScript implementation
│   ├── src/
│   │   ├── agents/              # Agent implementations
│   │   ├── utils/               # Utility functions
│   │   └── index.ts             # Entry point
│   ├── tests/                   # Test suite
│   └── package.json             # Project configuration
├── run.sh                       # Run script for Linux/macOS
├── run.bat                      # Run script for Windows
└── README.md                    # This file
```

## License

MIT