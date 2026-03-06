#!/bin/bash

# Support Assistant Setup Script
# Creates virtual environment and installs all dependencies

set -e

echo "🔧 Setting up Support Assistant..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "⚠️  Warning: Claude CLI not found. Please install it from https://claude.ai/code"
    echo "   The assistant requires Claude CLI to function."
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install imapclient python-dotenv

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env file from .env.example..."
        cp .env.example .env
        echo "⚠️  Please edit .env with your actual credentials before running."
    fi
fi

# Create processed_emails.txt if it doesn't exist
if [ ! -f processed_emails.txt ]; then
    echo "📄 Creating processed_emails.txt tracking file..."
    touch processed_emails.txt
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Gmail credentials"
echo "2. Enable IMAP in Gmail settings"
echo "3. Create an App Password for Gmail (if using 2FA)"
echo "4. Run ./run.sh to start the assistant"
