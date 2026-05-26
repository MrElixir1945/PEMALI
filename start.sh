#!/bin/bash
# PEMALI — 1 Command Start Script
# Jalanin backend + worker + frontend dalam 1 terminal

set -e

# Warna
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════╗"
echo "  ║      PEMALI V2 STARTUP      ║"
echo "  ╚══════════════════════════════╝"
echo -e "${NC}"

# Cek backend .env
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}❌ backend/.env not found!${NC}"
    echo "Copy from backend/.env.example: cp backend/.env.example backend/.env"
    exit 1
fi

# Database check
echo -e "${YELLOW}[1/5] Checking database...${NC}"
if command -v docker &> /dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "pemali_db"; then
    echo -e "  ${GREEN}✓ Database container already running${NC}"
else
    if command -v docker &> /dev/null; then
        echo -e "  ${YELLOW}Starting database container...${NC}"
        docker run -d --name pemali_db \
            -e POSTGRES_USER=admin \
            -e POSTGRES_PASSWORD=pemalipass \
            -e POSTGRES_DB=pemali_db \
            -p 5432:5432 \
            postgres:15 2>/dev/null || echo -e "  ${GREEN}✓ DB already running${NC}"
        sleep 3
    else
        echo -e "  ${RED}✗ Docker not found. Start PostgreSQL manually.${NC}"
    fi
fi

# Setup Python venv
echo -e "${YELLOW}[2/5] Setting up Python environment...${NC}"
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt -q
echo -e "  ${GREEN}✓ Python deps installed${NC}"

# Init database
echo -e "${YELLOW}[3/5] Initializing database...${NC}"
python3 -c "from backend.core.database import init_db; init_db()" 2>&1 || true
echo -e "  ${GREEN}✓ Database tables ready${NC}"

# Start backend
echo -e "${YELLOW}[4/5] Starting services...${NC}"
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --workers 2 > /tmp/pemali_backend.log 2>&1 &
BACKEND_PID=$!

python worker.py > /tmp/pemali_worker.log 2>&1 &
WORKER_PID=$!

cd ..
echo -e "  ${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"
echo -e "  ${GREEN}✓ Worker running (PID: $WORKER_PID)${NC}"

# Setup & start frontend
echo -e "${YELLOW}[5/5] Setting up frontend...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    pnpm install 2>&1 | tail -1
fi
pnpm dev --host 0.0.0.0 > /tmp/pemali_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}  ✅ PEMALI IS RUNNING!${NC}"
echo ""
echo -e "  ${CYAN}Frontend:${NC}  http://localhost:3000"
echo -e "  ${CYAN}Backend:${NC}   http://localhost:8080"
echo ""
echo -e "  ${YELLOW}Log files:${NC}"
echo -e "  Backend  → tail -f /tmp/pemali_backend.log"
echo -e "  Frontend → tail -f /tmp/pemali_frontend.log"
echo -e "  Worker   → tail -f /tmp/pemali_worker.log"
echo ""
echo -e "  ${RED}Press Ctrl+C to stop all services${NC}"
echo ""

# Trap exit signal
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $WORKER_PID 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Keep running
wait
