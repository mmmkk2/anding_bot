import sys
import json
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log

import os
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from datetime import datetime
import argparse
import pytz

from datetime import timedelta


kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)
today_str = now.strftime("%Y.%m.%d")


try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# Add manual mode switch after loading .env
# Default: DEBUG is True unless --manual is passed
parser = argparse.ArgumentParser()
parser.add_argument("--manual", action="store_true", help="수동 실행 모드 (디버깅 비활성화)")
args = parser.parse_args()
DEBUG = not args.manual and os.getenv("DEBUG", "true").lower() == "true"

print(f"[DEBUG CHECK] args.manual = {args.manual}")
print(f"[DEBUG CHECK] os.getenv('DEBUG') = {os.getenv('DEBUG')}")
print(f"[DEBUG CHECK] DEBUG = {DEBUG}")
print(f"[DEBUG MODE] {'ON' if DEBUG else 'OFF'}")


FIXED_SEAT_NUMBERS = list(map(int, os.getenv("FIXED_SEAT_NUMBERS").split(",")))
LAPTOP_SEAT_NUMBERS = list(map(int, os.getenv("LAPTOP_SEAT_NUMBERS").split(",")))

# === 좌석 색상 상태 정의 (기준값 .env에서 설정)
WARNING_THRESHOLD = int(os.getenv("WARNING_THRESHOLD"))
DANGER_THRESHOLD = int(os.getenv("DANGER_THRESHOLD"))


chart_timedelta = float(os.getenv("CHART_TIME_DELTA"))

# Dashboard path for logs and HTML
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH")
DEBUG_PATH = os.getenv("DEBUG_PATH")


# KST
kst = pytz.timezone("Asia/Seoul")


# URL
BASE_URL = os.getenv("BASE_URL")
SEAT_URL = f"{BASE_URL}/use/seatUse"

# TOTAL 
TOTAL_SEATS = int(os.getenv("TOTAL_SEATS", 5))


fixed_seat_numbers = FIXED_SEAT_NUMBERS
laptop_seat_numbers = LAPTOP_SEAT_NUMBERS



# === 좌석 상태 체크 ===
def check_seat_status(driver):
    retry_count = 0
    max_retries = 2

    while retry_count <= max_retries:
        used_free_seats = 0
        used_labtop_seats = 0
        used_fixed_seats = 0
        all_seat_numbers = []

        driver.get(SEAT_URL)
        # === 날짜 필터 추가 ===
        today_date_str = datetime.now(kst).strftime("%Y.%m.%d")
        try:
            # 시작일 입력
            start_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_start_date_start']")))
            driver.execute_script(f"document.querySelector('input[name=\"s_start_date_start\"]').value = '{today_date_str}';")
            # 종료일 입력
            end_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_start_date_end']")))
            driver.execute_script(f"document.querySelector('input[name=\"s_start_date_end\"]').value = '{today_date_str}';")
            time.sleep(0.5)  # 안정화 대기
            # 검색 버튼 클릭
            search_button = driver.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-search)")
            search_button.click()
            time.sleep(1.5)  # 검색 결과 로딩 대기
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] 날짜 필터 및 검색 실패: {e}")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(1)
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        # 추가 대기: td 수가 3 미만인 행만 있는 경우
        attempts = 0
        while attempts < 3 and all(len(r.find_elements(By.TAG_NAME, "td")) < 3 for r in rows):
            time.sleep(1.5)
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            attempts += 1

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 3:
                continue

            seat_type = cols[1].text.strip()
            seat_number_text = cols[2].text.strip().replace("\uac1c", "").replace("\ubc88", "").strip()

            try:
                seat_number = int(seat_number_text)
                all_seat_numbers.append(seat_number)
            except:
                continue

            if seat_type == "개인석":
                if seat_number in fixed_seat_numbers:
                    used_fixed_seats += 1
                elif seat_number in laptop_seat_numbers:
                    used_labtop_seats += 1
                else:
                    used_free_seats += 1

        total_used = used_free_seats + used_labtop_seats + used_fixed_seats
        if total_used > 0 or retry_count == max_retries:
            break
        retry_count += 1
        time.sleep(3)

    if DEBUG and total_used == 0:
        debug_file = os.path.join(DEBUG_PATH, f"debug_seat_zero_{datetime.now(kst).strftime('%Y%m%d_%H%M%S')}.html")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"[DEBUG] 좌석이 0 → 페이지 소스 저장됨: {debug_file}")

    # Use browser's JS time for current time
    # Use JS to get browser time in ISO format
    timestamp = driver.execute_script("return new Date().toISOString();")
    current_time = datetime.fromisoformat(timestamp[:-1]).astimezone(kst)
    current_hour = current_time.hour

    # The above pagination and seat parsing logic has already processed all rows,
    # so we do not need to process again here.

    TOTAL_FREE_SEATS = TOTAL_SEATS - len(fixed_seat_numbers) - len(laptop_seat_numbers)
    remaining_seats = TOTAL_FREE_SEATS - used_free_seats
    all_free_seat_numbers = [n for n in range(1, 34) if n not in fixed_seat_numbers and n not in laptop_seat_numbers]
    available_free_seat_numbers = sorted(set(all_free_seat_numbers) - set([n for n in all_seat_numbers if n not in laptop_seat_numbers and n not in fixed_seat_numbers]))



    if remaining_seats <= DANGER_THRESHOLD:
        status_emoji = "🔴"
        line_color = 'rgba(255, 99, 132, 1)'  # red
    elif remaining_seats <= WARNING_THRESHOLD:
        status_emoji = "🟡"
        line_color = 'rgba(255, 206, 86, 1)'  # yellow
    else:
        status_emoji = "🟢"
        line_color = 'rgba(75, 192, 192, 1)'  # green

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

    # === 주의/경고/복구 (broadcast only, no flag logic)
    if remaining_seats <= DANGER_THRESHOLD:
        send_broadcast_and_update(f"[경고] 🚨 자유석 {DANGER_THRESHOLD}석 이하 - 일일권 제한 강화 필요", broadcast=True, category="seat")
    elif remaining_seats <= WARNING_THRESHOLD:
        send_broadcast_and_update(f"[주의] ⚠️ 자유석 {WARNING_THRESHOLD}석 이하 - 이용 주의 필요", broadcast=True, category="seat")

    # === 최종 CSV 로그
    return msg

# === 메인 실행 ===
def main_check_seat():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")


    location_tag = find_location()
    print(f"📢 [좌석 - 모니터링] 시작합니다.")

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

            print(f"{location_tag} ✅ [좌석 - 모니터링] 정상 종료되었습니다.")
        else:
            send_broadcast_and_update("❌ [좌석] 로그인 실패", broadcast=False, category="seat")
    except Exception as e:
        send_broadcast_and_update(f"❌ [좌석 오류] {e}", broadcast=False, category="seat")
        # Save debug HTML on failure
        if DEBUG:
            debug_file = os.path.join(DEBUG_PATH, f"debug_seat_{datetime.now(kst).strftime('%Y%m%d_%H%M%S')}.html")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"[DEBUG] 예외 발생 → 페이지 소스 저장됨: {debug_file}")
    finally:
        driver.quit()


# def start_telegram_listener():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(telegram_auth_listener.run_listener_async())


def save_seat_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, status_emoji):
    history_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")

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
            point_colors.append('rgba(75, 192, 192, 0.1)')  # Light gray transparent for normal usage

    lineColor = 'rgba(75, 192, 192, 1)'  # default green
    if remaining <= 5:
        lineColor = 'rgba(255, 99, 132, 1)'  # red
    elif remaining <= 7:
        lineColor = 'rgba(255, 206, 86, 1)'  # yellow

    data_points = [{"x": t, "y": y} for t, y in zip(timestamps, used_frees)]

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
                    data: {json.dumps(data_points)},
                    borderColor: '{lineColor}',
                    pointBackgroundColor: {json.dumps(point_colors)},
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
                min-height: 250px; /* max-height: 25vh; */
                max-height: 250px; /*   max-width: 100vw; */ 
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
        
