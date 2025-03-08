#!/bin/bash

# Run script for ClaudeAgents (Linux/macOS)

# Set script to exit on error
set -e

# Detect OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
else
    echo "Unsupported OS. This script is designed for Linux and macOS."
    exit 1
fi

echo "ClaudeAgents Run Script for $OS_TYPE"
echo "===================================="

# Check for help flag
if [[ "$1" == "--help" ]]; then
    echo "Usage: ./run.sh [options] \"prompt\""
    echo
    echo "Options:"
    echo "  -l, --language LANG     Language implementation to use (python, javascript)"
    echo "  -v, --verbose           Enable verbose logging"
    echo "  -p, --persist-memory    Persist agent memory between runs" 
    echo "  -f, --file FILE         Read prompt from file"
    echo
    echo "Example:"
    echo "  ./run.sh \"Design a simple todo app\""
    echo "  ./run.sh -l javascript -v -p -f prompt.txt"
    exit 0
fi

# Default configuration
LANGUAGE="python"  # Options: python, javascript
VERBOSE=false
PERSIST_MEMORY=false
PROMPT_FILE=""
PROMPT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -l|--language)
      LANGUAGE="$2"
      shift # past argument
      shift # past value
      ;;
    -v|--verbose)
      VERBOSE=true
      shift # past argument
      ;;
    -p|--persist-memory)
      PERSIST_MEMORY=true
      shift # past argument
      ;;
    -f|--file)
      PROMPT_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    *)    # unknown option or prompt
      PROMPT="$1"
      shift # past argument
      ;;
  esac
done

# Validate language choice
if [[ "$LANGUAGE" != "python" && "$LANGUAGE" != "javascript" ]]; then
    echo "ERROR: Invalid language selection. Choose 'python' or 'javascript'."
    exit 1
fi

# Check environmental variables
if [[ -z "${ANTHROPIC_API_KEY}" && -z "${OPENAI_API_KEY}" ]]; then
    echo "WARNING: Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY environment variables are set."
    echo "The agents will not be able to make API calls to AI services."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for Python environment and dependencies for Python implementation
if [[ "$LANGUAGE" == "python" ]]; then
    echo "Checking Python environment..."
    
    if ! command -v python3 &> /dev/null; then
        echo "ERROR: Python 3 is not installed or not in PATH."
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "python/venv" ]; then
        echo "Creating Python virtual environment..."
        cd python
        python3 -m venv venv
        cd ..
    fi
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source python/venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    cd python
    pip install -e . --upgrade
    pip install -r requirements.txt --upgrade
    cd ..
    
    # Prepare command
    CMD="python python/src/main.py"
    
    if [ "$VERBOSE" = true ]; then
        CMD="$CMD --log-level DEBUG --log-to-file"
    fi
    
    if [ "$PERSIST_MEMORY" = true ]; then
        CMD="$CMD --persist-memory"
    fi
    
    if [ ! -z "$PROMPT_FILE" ]; then
        CMD="$CMD --prompt-file \"$PROMPT_FILE\""
    elif [ ! -z "$PROMPT" ]; then
        CMD="$CMD \"$PROMPT\""
    else
        echo "ERROR: No prompt provided. Use the -f option for a file or provide a prompt as an argument."
        exit 1
    fi
    
    # Run Python implementation
    echo "Running Python implementation..."
    echo "Command: $CMD"
    eval $CMD
    
    # Deactivate virtual environment
    deactivate
fi

# Check for Node.js and dependencies for JavaScript implementation
if [[ "$LANGUAGE" == "javascript" ]]; then
    echo "Checking Node.js environment..."
    
    if ! command -v node &> /dev/null; then
        echo "ERROR: Node.js is not installed or not in PATH."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        echo "ERROR: npm is not installed or not in PATH."
        exit 1
    fi
    
    # Install dependencies
    echo "Installing dependencies..."
    cd javascript
    npm install
    
    # Build the project
    echo "Building project..."
    npm run build
    
    # Prepare command
    CMD="node dist/index.js"
    
    if [ "$VERBOSE" = true ]; then
        CMD="$CMD --log-level debug --log-to-file"
    fi
    
    if [ "$PERSIST_MEMORY" = true ]; then
        CMD="$CMD --persist-memory"
    fi
    
    if [ ! -z "$PROMPT_FILE" ]; then
        CMD="$CMD --prompt-file \"$PROMPT_FILE\""
    elif [ ! -z "$PROMPT" ]; then
        CMD="$CMD \"$PROMPT\""
    else
        echo "ERROR: No prompt provided. Use the -f option for a file or provide a prompt as an argument."
        exit 1
    fi
    
    # Run JavaScript implementation
    echo "Running JavaScript implementation..."
    echo "Command: $CMD"
    eval $CMD
    
    cd ..
fi

echo "ClaudeAgents run completed."