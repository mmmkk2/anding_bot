import sys
import json
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log
from flask import request

import os
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
parser.add_argument("--manual", action="store_true", help="수동 실행 모드 (로그인 계정 변경)")
parser.add_argument("--hide", action="store_true", help="디버그 메시지 숨김")
args = parser.parse_args()
DEBUG_ENV = os.getenv("DEBUG", "true").lower() == "true"
DEBUG = not args.hide and DEBUG_ENV

print(f"[DEBUG CHECK] args.manual = {args.manual}")
print(f"[DEBUG CHECK] args.hide = {args.hide}")
print(f"[DEBUG CHECK] os.getenv('DEBUG') = {os.getenv('DEBUG')}")
print(f"[DEBUG CHECK] DEBUG_ENV = {DEBUG_ENV}")
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

        # Cast to sets for faster lookup and deduplication
        fixed_set = set(fixed_seat_numbers)
        laptop_set = set(laptop_seat_numbers)
        excluded_seats = fixed_set.union(laptop_set)

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
        # --- Pagination logic (safe seat data extraction) ---
        all_rows_data = []
        while True:
            page_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            for row in page_rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 3:
                        continue
                    seat_type = cols[1].text.strip()
                    seat_number_text = cols[2].text.strip().replace("\uac1c", "").replace("\ubc88", "").strip()
                    all_rows_data.append((seat_type, seat_number_text))
                except Exception:
                    continue
            try:
                next_li = driver.find_element(By.CSS_SELECTOR, '.paginate_button.next')
                next_class = next_li.get_attribute("class")
                if DEBUG:
                    print(f"[DEBUG] 다음 버튼 class 속성: {next_class}")
                if "disabled" in next_class:
                    if DEBUG:
                        print("[DEBUG] 다음 페이지 없음 → 루프 종료")
                    break
                next_btn = next_li.find_element(By.TAG_NAME, "a")
                next_btn.click()
                if DEBUG:
                    print("[DEBUG] 다음 페이지 클릭")
                time.sleep(1.5)  # 다음 페이지 로딩 시간 확보
            except NoSuchElementException:
                if DEBUG:
                    print("[DEBUG] 페이지네이션 요소 없음 → 루프 종료")
                break

        # 추가 대기: td 수가 3 미만인 행만 있는 경우 (not strictly needed with all_rows_data, but can reload if needed)
        attempts = 0
        while attempts < 3 and all(len(row) < 2 or not row[1] for row in all_rows_data):
            time.sleep(1.5)
            # reload all_rows_data (repeat first page)
            all_rows_data = []
            page_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            for row in page_rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 3:
                        continue
                    seat_type = cols[1].text.strip()
                    seat_number_text = cols[2].text.strip().replace("\uac1c", "").replace("\ubc88", "").strip()
                    all_rows_data.append((seat_type, seat_number_text))
                except Exception:
                    continue
            attempts += 1

        seat_debug_log = []
        for seat_type, seat_number_text in all_rows_data:
            try:
                seat_number = int(seat_number_text)
            except Exception:
                continue

            if DEBUG:
                print(f"[DEBUG] 좌석 유형 원본: '{seat_type}'")

            # Only log 자유석 (non-fixed, non-laptop) for all_seat_numbers
            if "개인석" in seat_type:
                if seat_number in fixed_set:
                    used_fixed_seats += 1
                    if DEBUG:
                        print(f"[DEBUG] 고정석 사용됨: {seat_number}")
                elif seat_number in laptop_set:
                    used_labtop_seats += 1
                    if DEBUG:
                        print(f"[DEBUG] 노트북석 사용됨: {seat_number}")
                else:
                    used_free_seats += 1
                    if DEBUG:
                        print(f"[DEBUG] 자유석 사용됨: {seat_number}")
                    all_seat_numbers.append(seat_number)  # Only 자유석 tracked here

        if DEBUG:
            print(f"[DEBUG] 전체 좌석번호(자유석): {all_seat_numbers}")
            print(f"[DEBUG] 고정석 번호(set): {sorted(fixed_set)}")
            print(f"[DEBUG] 노트북석 번호(set): {sorted(laptop_set)}")
            print(f"[DEBUG] 제외된 좌석(set): {sorted(excluded_seats)}")

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

    total_assigned_free_seats = TOTAL_SEATS - len(fixed_set) - len(laptop_set)
    used_total_seats = used_free_seats + used_labtop_seats + used_fixed_seats
    # remaining_seats is simply the difference between total seats and used seats
    TOTAL_FREE_SEATS = total_assigned_free_seats
    remaining_seats = TOTAL_FREE_SEATS - used_free_seats
    
    # Use the earlier excluded_seats set directly (already deduplicated)
    all_seats = set(range(1, TOTAL_SEATS + 1))
    free_seat_numbers = sorted(all_seats - excluded_seats)

    print(f"[DEBUG] 전체 좌석: {all_seats}")
    print(f"[DEBUG] 제외된 좌석: {excluded_seats}")
    print(f"[DEBUG] 자유석 (used): {used_free_seats}석")

    if remaining_seats <= DANGER_THRESHOLD:
        status_emoji = "🔴"
        line_color = 'rgba(255, 99, 132, 1)'  # red
    elif remaining_seats <= WARNING_THRESHOLD:
        status_emoji = "🟡"
        line_color = 'rgba(255, 206, 86, 1)'  # yellow
    else:
        status_emoji = "🟢"
        line_color = 'rgba(75, 192, 192, 1)'  # green


    # === 메시지 작성
    msg = (
        f"[좌석 알림] {status_emoji}\n"
        f"자유석 현재 입실: {used_free_seats}/{TOTAL_FREE_SEATS}\n"
        f"노트북석 현재 입실: {used_labtop_seats}/{len(laptop_seat_numbers)}\n"
        f"남은 자유석: {remaining_seats}석"
    )

    # === 좌석 기록 저장
    history_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
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
            now_full_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
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



def save_seat_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, status_emoji):
    output_path = os.path.join(DASHBOARD_PATH, "seat_dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>좌석 현황</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
            <style>
                body {{
                    font-family: 'Apple SD Gothic Neo', 'Arial', sans-serif;
                    background: #f1f3f5;
                    padding: 1rem;
                    text-align: center;
                }}
                .chart-container {{
                    max-width: 700px;
                    margin: auto;
                    background: white;
                    padding: 1rem;
                    border-radius: 1rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                button {{
                    margin: 0.5rem;
                }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <h3>📅 좌석 현황</h3>
                <div id="summary"></div>
                <canvas id="seatChart" height="200"></canvas>
                <div>
                    <button onclick="navigateDay(-1)">← 전일</button>
                    <button onclick="navigateDay(1)">익일 →</button>
                </div>
            </div>

            <script>
            const kstOffset = 9 * 60 * 60 * 1000;
            const now = new Date();
            let dateParam = new URLSearchParams(window.location.search).get("date");
            let baseDate = dateParam ? new Date(dateParam) : new Date(Date.now() + kstOffset);
            baseDate.setUTCHours(0, 0, 0, 0);

            function formatDate(date) {{
                return date.toISOString().split('T')[0];
            }}

            function navigateDay(offset) {{
                baseDate.setDate(baseDate.getDate() + offset);
                const newDateStr = formatDate(baseDate);
                const url = new URL(window.location.href);
                url.searchParams.set("date", newDateStr);
                window.location.href = url.toString();
            }}

            fetch('/dashboard_log/seat_history.csv')
                .then(resp => resp.text())
                .then(text => {
                    const rows = text.trim().split('\n').map(line => line.split(','));
                    const filtered = rows.map(([ts, used]) => {{
                        const d = new Date(ts + " KST");
                        return {{ x: d, y: parseInt(used) }};
                    }}).filter(pt => {{
                        const start = new Date(baseDate.getTime() + 5 * 3600 * 1000);
                        const end = new Date(start.getTime() + 24 * 3600 * 1000);
                        return pt.x >= start && pt.x < end;
                    }});

                    const ctx = document.getElementById('seatChart').getContext('2d');
                    const chartConfig = {{
                        type: 'line',
                        data: {{
                            datasets: [{{
                                label: '자유석 사용 수',
                                data: filtered,
                                borderColor: 'rgba(75,192,192,1)',
                                pointBackgroundColor: 'rgba(75,192,192,1)',
                                tension: 0.2
                            }}]
                        }},
                        options: {{
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
                                    ticks: {{
                                        source: 'auto',
                                        autoSkip: false
                                    }},
                                    min: new Date(baseDate.getTime() + 5 * 3600 * 1000),
                                    max: new Date(baseDate.getTime() + 29 * 3600 * 1000)
                                }},
                                y: {{
                                    beginAtZero: true,
                                    suggestedMax: 28
                                }}
                            }}
                        }}
                    }};
                    new Chart(ctx, chartConfig);

                    document.getElementById("summary").innerHTML =
                        "기준일: <b>" + formatDate(baseDate) + "</b> / 총 기록: " + filtered.length + "건";
                });
            </script>
        </body>
        </html>
        """)
