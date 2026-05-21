#!/usr/bin/env bash
# ==============================================================================
# PEMALI V2 — FULL RESET & REINSTALL
# ==============================================================================

YELLOW='\033[1;33m'
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${RED}⚠️ Peringatan: Proses ini akan menghapus semua environment (venv & node_modules).${NC}"
echo -e "${YELLOW}Membersihkan environment...${NC}"

# Hapus Backend venv
cd "$ROOT_DIR/backend"
if [ -d ".venv" ]; then
    rm -rf .venv
    echo -e "${GREEN}✔ Backend .venv dihapus.${NC}"
fi

# Hapus Frontend node_modules & build cache
cd "$ROOT_DIR/frontend"
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo -e "${GREEN}✔ Frontend node_modules dihapus.${NC}"
fi
if [ -d ".next" ]; then
    rm -rf .next
    echo -e "${GREEN}✔ Frontend .next cache dihapus.${NC}"
fi

# Panggil setup.sh
echo -e "\n${YELLOW}Mulai ulang setup...${NC}"
cd "$ROOT_DIR"
if [ -f "backend/scripts/setup.sh" ]; then
    bash backend/scripts/setup.sh
else
    echo -e "${RED}✘ backend/scripts/setup.sh tidak ditemukan!${NC}"
fi
