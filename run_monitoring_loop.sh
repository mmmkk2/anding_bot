#!/bin/bash

PROJECT_DIR="/home/mmkkshim/anding-study-bot"
MONITOR="$PROJECT_DIR/main_seat_check3.py"

echo "🔁 combined loop 시작됨: $(date)"


# 좌석 모니터링 5분마다 반복 실행
while true
do
    echo "▶ 좌석 모니터링 시작: $(date)"
    python3 "$MONITOR"
    echo "⏹ 모니터링 종료됨. 5분 대기..."
    sleep 60
done#!/bin/bash

