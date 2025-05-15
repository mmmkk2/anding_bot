#!/bin/bash

PROJECT_DIR="/home/mmkkshim/anding-study-bot"
LISTENER="$PROJECT_DIR/telegram_auth_listener.py"
MONITOR="$PROJECT_DIR/main_seat_check3.py"

echo "🔁 combined loop 시작됨: $(date)"

# listener를 백그라운드로 실행하고 PID 저장
start_listener() {
    nohup python3 "$LISTENER" > listener.log 2>&1 &
    LISTENER_PID=$!
    echo "✅ 리스너 시작됨 (PID: $LISTENER_PID)"
}

start_listener

while true
do
    # === 리스너 생존 여부 확인 ===
    if ! ps -p $LISTENER_PID > /dev/null; then
        echo "⚠️ 리스너 프로세스 중단 감지. 재시작 중... ($(date))"
        start_listener
    fi

    # === 좌석 모니터링 실행 ===
    echo "▶ 좌석 모니터링 시작: $(date)"
    python3 "$MONITOR"
    echo "⏹ 모니터링 종료됨. 5분 대기..."

    sleep 60
done