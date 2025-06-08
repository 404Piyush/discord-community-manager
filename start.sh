#!/bin/bash

echo "============================================"
echo "    🤖 Community Manager Bot Startup"
echo "============================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3 from https://python.org"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed"
    echo "Please install pip3"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

# Check if config.env exists
if [ ! -f "config.env" ]; then
    echo "❌ config.env file not found"
    echo "Please create config.env file with your bot token"
    echo "Example: DISCORD_TOKEN=your_bot_token_here"
    exit 1
fi

echo "✅ Installing dependencies..."
pip3 install -r requirements.txt

echo
echo "✅ Starting Community Manager Bot..."
echo "Press Ctrl+C to stop the bot"
echo
python3 main.py 