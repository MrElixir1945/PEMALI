#!/bin/bash

# PEMALI Setup Script
# This script automates the environment setup for PEMALI.

set -e

# Colors for better visibility
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting PEMALI Setup...${NC}"

# 1. Check Prerequisites
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"
command -v python3 >/dev/null 2>&1 || { echo -e >&2 "${RED}❌ Python 3 is required but not installed. Aborting.${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e >&2 "${RED}❌ Node.js is required but not installed. Aborting.${NC}"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e >&2 "${RED}❌ npm is required but not installed. Aborting.${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e >&2 "${YELLOW}⚠️  Docker is not installed. You will need it to run the database.${NC}"; }

# 2. Environment Configuration
echo -e "${YELLOW}[2/4] Configuring environment...${NC}"
if [ ! -f .env ]; then
    echo -e "📄 Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys (e.g., OPENROUTER_KEY).${NC}"
else
    echo -e "${GREEN}✅ .env already exists.${NC}"
fi

# 3. Python Virtual Environment
echo -e "${YELLOW}[3/4] Setting up Python Virtual Environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created.${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists.${NC}"
fi

echo -e "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Frontend Dependencies
echo -e "${YELLOW}[4/4] Installing Frontend dependencies...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✅ Frontend dependencies installed.${NC}"
else
    echo -e "${RED}❌ Frontend directory not found.${NC}"
fi

echo -e "\n${GREEN}✅ Setup Complete!${NC}"
echo -e "---------------------------------------------------"
echo -e "${BLUE}To run PEMALI, open 3 terminals and run:${NC}"
echo -e "${YELLOW}1. Backend:  ${NC}source venv/bin/activate && uvicorn main:app --reload"
echo -e "${YELLOW}2. Worker:   ${NC}source venv/bin/activate && python worker.py"
echo -e "${YELLOW}3. Frontend: ${NC}cd frontend && npm run dev"
echo -e "---------------------------------------------------"
echo -e "${BLUE}Don't forget to start the database:${NC} docker compose up -d"
echo -e "---------------------------------------------------"
