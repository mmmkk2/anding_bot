#!/bin/bash

# 경로 설정
PROJECT_DIR="/home/mmkkshim/anding-study-bot"
SCRIPT="$PROJECT_DIR/telegram_auth_listener.py"

while true
do
    echo "▶ 인증 리스너 실행: $(date)"
    python3 "$SCRIPT"
    echo "⏹ 리스너 종료됨. 5초 후 재시작..."
    sleep 5
done