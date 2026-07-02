#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "WARNING: .env file not found."
  echo "Copy .env.example to .env and paste in your Firecrawl API key first."
  exit 1
fi

echo "Checking Python dependencies..."
python3 -m pip install -r requirements.txt --quiet

if [ "$1" = "--with-autoreply" ]; then
  echo ""
  echo "Starting WhatsApp auto-reply module in the background..."
  if [ ! -d "autoreply/node_modules" ]; then
    echo "Installing Node dependencies for the auto-reply module - this can take a few minutes the first time..."
    (cd autoreply && npm install)
  fi
  (cd autoreply && npm start) &
fi

echo ""
echo "Starting Madlan CRM dashboard..."
python3 app.py
