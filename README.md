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

### Python Implementation

```bash
# Navigate to the Python implementation
cd python

# Install dependencies
pip install -e .

# Run with prompt
python src/main.py "Your prompt here"

# Run with prompt from file
python src/main.py --prompt-file your_prompt.txt

# Enable verbose logging
python src/main.py --log-level DEBUG --log-to-file "Your prompt here"
```

### JavaScript Implementation

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

## Project Structure

```
ClaudeAgents/
├── python/                      # Python implementation
│   ├── src/
│   │   ├── agents/              # Agent implementations
│   │   ├── utils/               # Utility functions
│   │   └── main.py              # Entry point
│   ├── tests/                   # Test suite
│   └── pyproject.toml           # Project configuration
├── javascript/                  # JavaScript implementation
│   ├── src/
│   │   ├── agents/              # Agent implementations
│   │   ├── utils/               # Utility functions
│   │   └── index.ts             # Entry point
│   ├── tests/                   # Test suite
│   └── package.json             # Project configuration
└── README.md                    # This file
```

## License

MIT