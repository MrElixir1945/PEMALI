#!/usr/bin/env bash
# ==============================================================================
# PEMALI V2 — SETUP SYSTEM
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${YELLOW}Memulai setup PEMALI V2...${NC}"

# 1. Konfigurasi Environment Variables
echo -e "\n${YELLOW}[1/3] Menyiapkan Konfigurasi (.env)...${NC}"
if [ -f "$ROOT_DIR/backend/.env" ]; then
    echo -e "${GREEN}✔ backend/.env ditemukan.${NC}"
else
    echo -e "${RED}✘ backend/.env tidak ditemukan! Silakan buat dari .env.example${NC}"
fi

# 2. Setup Backend (Python Virtual Environment)
echo -e "\n${YELLOW}[2/3] Setup Backend (Python venv)...${NC}"
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi
deactivate
echo -e "${GREEN}✔ Backend dependencies berhasil diinstall.${NC}"

# 3. Setup Frontend (Node.js)
echo -e "\n${YELLOW}[3/3] Setup Frontend (Node modules)...${NC}"
cd "$ROOT_DIR/frontend"
if command -v pnpm &> /dev/null; then
    pnpm install
else
    npm install
fi
echo -e "${GREEN}✔ Frontend dependencies berhasil diinstall.${NC}"

echo -e "\n${GREEN}=== Setup Selesai! Kamu sekarang bisa menjalankan backend/scripts/run.sh ===${NC}"
