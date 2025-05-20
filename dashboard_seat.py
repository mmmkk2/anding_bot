import sys
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log

import os
import time
import pickle
import csv
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import threading
import telegram_auth_listener



# === 설정 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# Dashboard path for logs and HTML
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/")

DEBUG_PATH = os.getenv("DEBUG_PATH", "/home/mmkkshim/anding_bot/log/")

# Add DEBUG switch after loading .env
DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")

COOKIE_FILE = os.getenv("COOKIE_FILE") or "/home/mmkkshim/anding_bot/log/last_payment_id.pkl"
SEAT_CACHE_FILE = os.getenv("SEAT_CACHE_FILE") or "/home/mmkkshim/anding_bot/log/last_seat_state.pkl"

FIX_SEATS = int(os.getenv("FIX_SEATS", 5))
LAPTOP_SEATS = int(os.getenv("LAPTOP_SEATS", 6))

BASE_URL = "https://partner.cobopay.co.kr"
SEAT_URL = f"{BASE_URL}/use/seatUse"
TOTAL_FREE_SEATS = 39 - FIX_SEATS - LAPTOP_SEATS

kst = pytz.timezone("Asia/Seoul")



# === 좌석 상태 체크 ===
def check_seat_status(driver):
    used_free_seats = 0
    used_labtop_seats = 0
    used_fixed_seats = 0
    all_seat_numbers = []

    fixed_seat_numbers = [19, 20, 21, 22, 23, 39]
    laptop_seat_numbers = [34, 35, 36, 37, 38]

    driver.get(SEAT_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))


    # Use browser's JS time for current time
    # Use JS to get browser time in ISO format
    timestamp = driver.execute_script("return new Date().toISOString();")
    current_time = datetime.fromisoformat(timestamp[:-1]).astimezone(kst)
    current_hour = current_time.hour

    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if DEBUG: print("[DEBUG] columns parsed:", [c.text for c in cols])
            if len(cols) < 3:
                continue

            seat_type = cols[1].text.strip()
            seat_number_text = cols[2].text.strip().replace("\uac1c", "").replace("\ubc88", "").strip()

            try:
                seat_number = int(seat_number_text)
                all_seat_numbers.append(seat_number)
            except:
                continue

            if DEBUG: print(f"[DEBUG] Parsed seat_type: {seat_type}, seat_number: {seat_number}")

            if seat_type == "개인석":
                if seat_number in fixed_seat_numbers:
                    used_fixed_seats += 1
                elif seat_number in laptop_seat_numbers:
                    used_labtop_seats += 1
                else:
                    used_free_seats += 1

            # End of for row in rows: loop, before pagination try:
        if DEBUG: print(f"[DEBUG] used_free_seats: {used_free_seats}, used_fixed_seats: {used_fixed_seats}, used_labtop_seats: {used_labtop_seats}")

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'ul.pagination li.active + li a')
            if "javascript:;" in next_btn.get_attribute("href"):
                break
            next_btn.click()
            time.sleep(1)
        except:
            break

    TOTAL_FREE_SEATS = 39 - len(fixed_seat_numbers) - len(laptop_seat_numbers)
    remaining_seats = TOTAL_FREE_SEATS - used_free_seats
    all_free_seat_numbers = [n for n in range(1, 34) if n not in fixed_seat_numbers and n not in laptop_seat_numbers]
    available_free_seat_numbers = sorted(set(all_free_seat_numbers) - set([n for n in all_seat_numbers if n not in laptop_seat_numbers and n not in fixed_seat_numbers]))

    # === 좌석 색상 상태 정의
    if remaining_seats <= 5:
        status_emoji = "🔴"
    elif remaining_seats <= 7:
        status_emoji = "🟡"
    else:
        status_emoji = "🟢"

    # === 좌석 기록 저장
    log_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{now_str},{used_free_seats}\n")

    save_seat_dashboard_html(
        used_free=used_free_seats,
        total_free=TOTAL_FREE_SEATS,
        used_laptop=used_labtop_seats,
        total_laptop=len(laptop_seat_numbers),
        remaining=remaining_seats,
        status_emoji=status_emoji
    )

    # === 메시지 작성
    msg = (
        f"[좌석 알림] {status_emoji}\n"
        f"자유석 현재 입실: {used_free_seats}/{TOTAL_FREE_SEATS}\n"
        f"노트북석 현재 입실: {used_labtop_seats}/{len(laptop_seat_numbers)}\n"
        f"남은 자유석: {remaining_seats}석"
    )

    # === 변경 체크해서 broadcast
    changed = True

    if changed:
        send_broadcast_and_update(msg, broadcast=False,  category="seat")

    # === 주의/경고/복구 (broadcast only, no flag logic)
    if remaining_seats <= 5:
        send_broadcast_and_update("[경고] 🚨 자유석 5석 이하 - 일일권 제한 강화 필요", broadcast=True, category="seat")
    elif remaining_seats <= 7:
        send_broadcast_and_update("[주의] ⚠️ 자유석 7석 이하 - 이용 주의 필요", broadcast=True, category="seat")
    elif current_hour >= 20 and remaining_seats >= 10:
        send_broadcast_and_update("[안내] ✅ 자유석 여유 확보 (10석 이상) - 일일권 이용 제한 해제", broadcast=False, category="seat")

    # === 최종 CSV 로그
    return msg

# === 메인 실행 ===
def main_check_seat():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")


    location_tag = find_location()
    send_telegram_and_log(f"📢 [좌석 - 모니터링] 시작합니다.")

    driver = create_driver()

    try:
        if login(driver):
            seat_status_msg = check_seat_status(driver)
            now_full_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            loop_msg = (
                f"\n\n🪑 좌석 모니터링 정상 동작 중\n"
                f"⏰ 날짜 + 실행 시각: {now_full_str}"
            )
            full_msg = loop_msg + "\n\n" + seat_status_msg
            send_broadcast_and_update(full_msg, broadcast=False, category="seat")

            send_telegram_and_log(f"{location_tag} ✅ [좌석 - 모니터링] 정상 종료되었습니다.")
        else:
            send_broadcast_and_update("❌ [좌석] 로그인 실패", broadcast=False, category="seat")
    except Exception as e:
        send_broadcast_and_update(f"❌ [좌석 오류] {e}", broadcast=False, category="seat")
    finally:
        driver.quit()


from datetime import datetime
import pytz

kst = pytz.timezone("Asia/Seoul")

today_str = datetime.now(kst).strftime("%Y.%m.%d")
now = datetime.now(kst)


import asyncio


def start_telegram_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_auth_listener.run_listener_async())


import requests
import socket

chart_timedelta = float(os.getenv("CHART_TIME_DELTA", "12"))

def save_seat_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, status_emoji):
    history_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")

    from datetime import timedelta

    history_rows = []
    cutoff_time = datetime.now(kst) - timedelta(hours=chart_timedelta)

    with open(history_path, "r", encoding="utf-8") as f:
        for line in reversed(f.readlines()):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                timestamp_obj = kst.localize(datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S"))
                if timestamp_obj >= cutoff_time:
                    history_rows.insert(0, line)
                else:
                    break
                
    timestamps = []
    used_frees = []
    for line in history_rows:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            timestamp_obj = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
            timestamps.append(timestamp_obj.strftime("%Y-%m-%dT%H:%M:%S"))
            used_frees.append(int(parts[1]))
    point_colors = []
    for y in used_frees:
        if total_free - y <= 5:
            point_colors.append('rgba(255, 99, 132, 1)')  # Red
        elif total_free - y <= 7:
            point_colors.append('rgba(255, 206, 86, 1)')  # Yellow
        else:
            point_colors.append('rgba(200, 200, 200, 1)')  # Light gray transparent for normal usage

    chart_script = f"""
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <script src='https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns'></script>
    <script>
        const ctx = document.getElementById('seatChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                datasets: [{{
                    label: '자유석 사용 수',
                    data: [
                        {''.join([f"{{ x: '{t}', y: {y} }}," for t, y in zip(timestamps, used_frees)])}
                    ],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    pointBackgroundColor: {point_colors},
                    pointRadius: window.innerWidth > 768 ? 2 : 4,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{
                            unit: 'minute',
                            stepSize: 30,
                            displayFormats: {{
                                minute: 'HH:mm'
                            }}
                        }},
                        title: {{
                            display: false
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        max: {total_free}
                    }}
                }}
            }}
        }});
    </script>
    """

    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <title>좌석 현황</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', 'Arial', sans-serif;
                background: #f1f3f5;
                padding: 0.5rem;
                margin: 0;
                display: flex;
                align-items: flex-start;
                min-height: 300px; /* max-height: 25vh; */
                max-height: 300px; /*   max-width: 100vw; */ 
                box-sizing: border-box;
                justify-content: center;
                text-align: center;  /* 텍스트 정렬 보정 */               
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1rem;
                max-width: 650px;         /* max-width: 600px */
                width: 100%;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
                overflow-y: auto;
                margin: 0 auto;
            }}       
            h1 {{
                font-size: 1.1rem;
                margin-bottom: 1rem;
                color: #333;
            }}
            .emoji {{
                font-size: 1.0rem;
                margin-bottom: 1rem;
            }}
            .stat {{
                font-size: 0.9rem;
                margin: 0.3rem 0;
            }}
            .updated {{
                font-size: 0.8rem;
                color: #888;
                margin-top: 1rem;
            }}          
            @media (max-width: 480px) {{
                body {{
                    max-height: 50vh;
                }}            
                .box {{
                    max-height: 100vh;  /* 화면 높이의 90%까지 확장 */
                }}
            }}                
        </style>
    </head>
    <body>
        <div class="box">
            <div class="updated">📅 기준 날짜: <b>{today_str}</b></div>
            <div class="stat">자유석: {used_free}/{total_free}</div>
            <div class="stat">노트북석: {used_laptop}/{total_laptop}</div>
            <div class="stat">남은 자유석: {remaining}석</div>            
            <div class="updated">업데이트 시각: {now_str}</div>
            <div style="margin-top:0.5rem;">            
                 <canvas id="seatChart"  height="210"></canvas>
                {chart_script}
            </div>
        </div>
    </body>
    </html>
    """
    with open(os.path.join(DASHBOARD_PATH, "seat_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)
        
