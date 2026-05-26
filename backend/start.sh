#!/usr/bin/env bash
cd /home/bdw/Documents/PEMALI/backend
mkdir -p logs
CHROMA_PATH=/tmp/pemali_chroma PYTHONUNBUFFERED=1 nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level info > logs/api.log 2>&1 &
echo $!
