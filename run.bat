@echo off
setlocal

cd /d "%~dp0"

if not exist ".env" (
    echo WARNING: .env file not found.
    echo Copy .env.example to .env and paste in your Firecrawl API key first.
    pause
    exit /b 1
)

echo Checking Python dependencies...
python -m pip install -r requirements.txt --quiet

if "%1"=="--with-autoreply" (
    echo.
    echo Starting WhatsApp auto-reply module in a separate window...
    if not exist "autoreply\node_modules" (
        echo Installing Node dependencies for the auto-reply module - this can take a few minutes the first time...
        pushd autoreply
        call npm install
        popd
    )
    start "Madlan Auto-Reply (unofficial WhatsApp client)" cmd /k "cd /d "%~dp0autoreply" && npm start"
)

echo.
echo Starting Madlan CRM dashboard...
python app.py

endlocal
