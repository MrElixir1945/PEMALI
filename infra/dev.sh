#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   PEMALI AGENTIC SYSTEM - DEV MODE    ${NC}"
echo -e "${BLUE}=======================================${NC}"

VENV="backend/.venv"
if [ ! -d "$VENV" ]; then
    echo -e "${RED}Error: Virtual environment ($VENV) tidak ditemukan!${NC}"
    echo "Jalankan: python3 -m venv backend/.venv && backend/.venv/bin/pip install -r config/requirements.txt"
    exit 1
fi

if [ ! -f "config/.env" ]; then
    echo -e "${RED}Warning: config/.env tidak ditemukan!${NC}"
fi

cleanup() {
    echo -e "\n${RED}Stopping all PEMALI services...${NC}"
    kill $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup SIGINT

echo -e "${GREEN}[1/2] Starting Backend Services (API + Worker)...${NC}"
$VENV/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!

$VENV/bin/python backend/worker.py > logs/worker.log 2>&1 &
WORKER_PID=$!

echo -e "${GREEN}[2/2] Starting Frontend (Next.js)...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
else
    echo -e "${RED}Warning: Folder frontend tidak ditemukan!${NC}"
fi

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}Sistem PEMALI berhasil dijalankan!${NC}"
echo -e "API Log: tail -f logs/api.log"
echo -e "Worker Log: tail -f logs/worker.log"
echo -e "Frontend Log: tail -f logs/frontend.log"
echo -e "Tekan Ctrl+C untuk mematikan seluruh server."
echo -e "${BLUE}=======================================${NC}"

wait
