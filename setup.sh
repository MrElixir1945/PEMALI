#!/bin/bash
# PEMALI Quick Setup Script
# Setup semua dependencies dalam 1 command

set -e

echo "🔧 PEMALI Quick Setup"
echo "===================="

# Backend Setup
echo "📦 Setting up Backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Edit backend/.env and fill in OPENROUTER_KEY"
fi
cd ..

# Frontend Setup
echo "🎨 Setting up Frontend..."
cd frontend
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi
pnpm install
cd ..

echo ""
echo "✅ Setup complete!"
echo "================="
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and fill in your OPENROUTER_KEY"
echo "2. Run: ./start.sh"
echo ""
