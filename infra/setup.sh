#!/bin/bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Starting PEMALI Setup...${NC}"

echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"
command -v python3 >/dev/null 2>&1 || { echo -e >&2 "${RED}Python 3 is required.${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e >&2 "${RED}Node.js is required.${NC}"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e >&2 "${RED}npm is required.${NC}"; exit 1; }

echo -e "${YELLOW}[2/4] Configuring environment...${NC}"
if [ ! -f config/.env ]; then
    cp config/.env.example config/.env
    echo -e "${YELLOW}Edit config/.env and add your API keys.${NC}"
else
    echo -e "${GREEN}config/.env exists.${NC}"
fi

echo -e "${YELLOW}[3/4] Setting up Python Virtual Environment...${NC}"
VENV_DIR="backend/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
$VENV_DIR/bin/pip install --upgrade pip -q
$VENV_DIR/bin/pip install -r config/requirements.txt -q
echo -e "${GREEN}Python dependencies installed.${NC}"

echo -e "${YELLOW}[4/4] Installing Frontend dependencies...${NC}"
if [ -d "frontend" ]; then
    cd frontend && npm install && cd ..
    echo -e "${GREEN}Frontend dependencies installed.${NC}"
else
    echo -e "${RED}Frontend directory not found.${NC}"
fi

echo -e "\n${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}Run:${NC}"
echo -e "  ${YELLOW}Backend:${NC}  $VENV_DIR/bin/uvicorn backend.main:app --reload --port 8000"
echo -e "  ${YELLOW}Worker:${NC}   $VENV_DIR/bin/python backend/worker.py"
echo -e "  ${YELLOW}Frontend:${NC} cd frontend && npm run dev"
echo -e "  ${YELLOW}TUI:${NC}      $VENV_DIR/bin/python tools/tui_monitor.py"
echo -e "  ${YELLOW}TUI Chat:${NC} $VENV_DIR/bin/python tools/tui_chat.py"
echo -e "${BLUE}Database:${NC} docker compose -f infra/docker-compose.yml up -d"
