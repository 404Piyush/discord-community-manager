@echo off
title Community Manager Bot
echo.
echo ============================================
echo    🤖 Community Manager Bot Startup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if requirements.txt exists
if not exist requirements.txt (
    echo ❌ requirements.txt not found
    pause
    exit /b 1
)

REM Check if config.env exists
if not exist config.env (
    echo ❌ config.env file not found
    echo Please create config.env file with your bot token
    echo Example: DISCORD_TOKEN=your_bot_token_here
    pause
    exit /b 1
)

echo ✅ Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Starting Community Manager Bot...
echo Press Ctrl+C to stop the bot
echo.
python main.py

pause 