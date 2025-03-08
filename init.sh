#!/bin/bash

# Initialization script for ClaudeAgents (Linux/macOS)

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

echo "ClaudeAgents Initialization Script for $OS_TYPE"
echo "==============================================="

# Check Python environment
echo "Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH."
    echo "Please install Python 3.9+ and ensure it's in your PATH."
    exit 1
fi

# Check Node.js environment
echo "Checking Node.js environment..."
if ! command -v node &> /dev/null; then
    echo "WARNING: Node.js is not installed or not in PATH."
    echo "The JavaScript implementation will not be available."
    echo "Please install Node.js 18+ if you want to use the JavaScript implementation."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    if ! command -v npm &> /dev/null; then
        echo "WARNING: npm is not installed or not in PATH."
        echo "The JavaScript implementation will not be available."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Make sure the script is executable
chmod +x run.sh

# Set up Python virtual environment
echo "Setting up Python environment..."
if [ ! -d "python/venv" ]; then
    echo "Creating Python virtual environment..."
    cd python
    python3 -m venv venv
    cd ..
fi

# Set up Python dependencies
echo "Installing Python dependencies..."
source python/venv/bin/activate
cd python
python -m pip install --upgrade pip
pip install wheel setuptools --upgrade
pip install -e . --upgrade
pip install -r requirements.txt --upgrade
cd ..
deactivate

# Set up JavaScript dependencies (if Node.js is available)
if command -v node &> /dev/null; then
    echo "Setting up JavaScript environment..."
    cd javascript
    npm install
    npm run build
    cd ..
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit the .env file to add your API keys."
fi

# Create example prompt
if [ ! -f "example_prompt.txt" ]; then
    echo "Creating example prompt..."
    echo "Design a simple command-line calculator app with basic arithmetic operations." > example_prompt.txt
fi

echo
echo "ClaudeAgents initialized successfully!"
echo
echo "You can now run the system using:"
echo "  ./run.sh \"Your prompt here\""
echo "or"
echo "  ./run.sh -f example_prompt.txt"
echo
echo "For more options, run:"
echo "  ./run.sh --help"