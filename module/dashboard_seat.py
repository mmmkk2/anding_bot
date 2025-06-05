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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from datetime import timedelta
import argparse


kst = pytz.timezone("Asia/Seoul")
today_str = datetime.now(kst).strftime("%Y.%m.%d")


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
WARNING_CUM_THRESHOLD = int(os.getenv("WARNING_CUM_THRESHOLD", "50"))


# Dashboard path for logs and HTML
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH")
DEBUG_PATH = os.getenv("DEBUG_PATH")


# KST
kst = pytz.timezone("Asia/Seoul")


# URL
BASE_URL = os.getenv("BASE_URL")
SEAT_URL = f"{BASE_URL}/use/seatUse"
FIXED_URL =  f"{BASE_URL}/use/seatAccess"


# TOTAL 
TOTAL_SEATS = int(os.getenv("TOTAL_SEATS", 5))


# === 좌석 상태 체크 ===

def extract_seat_data(driver, SEAT_URL, seat_type_filter=None):
    """
    Extracts all seat data from the seat table with pagination and returns a list of tuples:
    (seat_type, seat_number_text, identifier, product, start_time)
    """
    retry_count = 0
    max_retries = 2
    all_rows_data = []
    while retry_count <= max_retries:
        # Cast to sets for faster lookup and deduplication
        fixed_set = set(FIXED_SEAT_NUMBERS)
        laptop_set = set(LAPTOP_SEAT_NUMBERS)
        excluded_seats = fixed_set.union(laptop_set)

        driver.get(SEAT_URL)
        today_date_str = datetime.now(kst).strftime("%Y.%m.%d")
        yesterday_date_str = (datetime.now(kst) - timedelta(days=1)).strftime("%Y.%m.%d")
        try:
            # 날짜 필터 설정
            # start_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_start_date_start']")))
            # start_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_enter_date_start']")))
            # driver.execute_script(f"document.querySelector('input[name=\"s_start_date_start\"]').value = '{today_date_str}';")
            start_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name$='_date_start']")))
            driver.execute_script(f"document.querySelector('input[name$=\"_date_start\"]').value = '{yesterday_date_str}';")
            end_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name$='_date_end']")))
            driver.execute_script(f"document.querySelector('input[name$=\"_date_end\"]').value = '{today_date_str}';")
            # driver.execute_script(f"document.querySelector('input[name=\"s_start_date_end\"]').value = '{today_date_str}';")
            time.sleep(0.5)
            # 검색 버튼 클릭
            search_button = driver.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-search)")
            search_button.click()
            time.sleep(1.5)  # 검색 결과 로딩 대기

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] 날짜 필터 및 검색 실패: {e}")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(1)

        all_rows_data = []
        while True:
            page_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            for row in page_rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 7:
                        continue
                    # Determine offset based on whether cols[0].text is a boolean string (like 'True'/'False')
                    offset = 1 if cols[0].text.strip()=="" else 0
                    try:
                        seat_type = cols[offset].text.strip()
                        seat_number_text = cols[offset + 1].text.strip().replace("번", "").strip()
                        identifier = cols[offset + 3].text.strip()
                        product = cols[offset + 4].text.strip()
                        start_time = cols[offset + 5].text.strip()
                        end_time = cols[offset + 6].text.strip()
                    except IndexError:
                        continue
                    if not identifier:
                        continue
                    
                    if (seat_type_filter is None) or (seat_type in seat_type_filter):
                        all_rows_data.append((seat_type, seat_number_text, identifier, product, start_time, end_time))
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
                time.sleep(1.5)
            except NoSuchElementException:
                if DEBUG:
                    print("[DEBUG] 페이지네이션 요소 없음 → 루프 종료")
                break

        if all_rows_data or retry_count == max_retries:
            break
        retry_count += 1
        time.sleep(3)

    return all_rows_data


def check_seat_status(driver):
    fixed_set = set(FIXED_SEAT_NUMBERS)
    laptop_set = set(LAPTOP_SEAT_NUMBERS)
    excluded_seats = fixed_set.union(laptop_set)

    free_rows_data = extract_seat_data(driver, SEAT_URL, seat_type_filter=["개인석"])
    fixed_rows_data = extract_seat_data(driver, FIXED_URL, seat_type_filter=["고정석"])

    all_rows_data = free_rows_data + fixed_rows_data

    # Insert the grouped and styled seat table before closing .box
    if all_rows_data:
        laptop_rows = []
        free_rows = []
        fixed_rows = []

        for seat_type, seat_number, name, product, start_time, end_time in all_rows_data:
            try:
                seat_number_int = int(seat_number)
            except ValueError:
                continue

            # Priority: 노트북석 > 고정석 > 자유석
            if seat_number_int in LAPTOP_SEAT_NUMBERS:
                seat_type = "노트북석"
                laptop_rows.append((seat_type, seat_number, name, product, start_time, end_time))
            elif seat_number_int in FIXED_SEAT_NUMBERS:
                seat_type = "고정석"
                fixed_rows.append((seat_type, seat_number, name, product, start_time, end_time))
            else:
                seat_type = "자유석"
                free_rows.append((seat_type, seat_number, name, product, start_time, end_time))


    # --- Sort rows by 입실시간 (start_time) ---
    def sort_by_start_time(row):
        try:
            return datetime.strptime(row[4], '%Y.%m.%d %H:%M')
        except:
            return datetime.min
    free_rows.sort(key=sort_by_start_time, reverse=True)
    laptop_rows.sort(key=sort_by_start_time, reverse=True)
    fixed_rows.sort(key=sort_by_start_time, reverse=True)


    used_labtop_seats = len(laptop_rows)
    used_free_seats = len(free_rows)
    used_fixed_seats = len(fixed_rows)        

    total_used = used_free_seats + used_labtop_seats + used_fixed_seats

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

    total_assigned_free_seats = TOTAL_SEATS - len(fixed_set.union(laptop_set))
    
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
    elif remaining_seats <= WARNING_THRESHOLD:
        status_emoji = "🟡"
    else:
        status_emoji = "🟢"


    # === 메시지 작성
    msg = (
        f"[좌석 알림] {status_emoji}\n"
        f"자유석 현재 입실: {used_free_seats}/{TOTAL_FREE_SEATS}\n"
        f"노트북석 현재 입실: {used_labtop_seats}/{len(LAPTOP_SEAT_NUMBERS)}\n"
        f"남은 자유석: {remaining_seats}석"
    )

    # === 좌석 기록 저장
    history_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{now_str},{used_free_seats}\n")


    rows_dict = {"자유석": free_rows, "노트북석": laptop_rows, "고정석" : fixed_rows}

    save_seat_dashboard_html(
        used_free=used_free_seats,
        total_free=TOTAL_FREE_SEATS,
        used_laptop=used_labtop_seats,
        total_laptop=len(LAPTOP_SEAT_NUMBERS),
        remaining=remaining_seats,
        rows_dict=rows_dict
    )


    # === 주의/경고/복구 (broadcast only, no flag logic)
    if remaining_seats <= DANGER_THRESHOLD:
        send_broadcast_and_update(f"[경고] 🚨 잔여 자유석 {remaining_seats}석 - 일일권 제한 강화 필요", broadcast=True, category="seat")
    elif remaining_seats <= WARNING_THRESHOLD:
        send_broadcast_and_update(f"[주의] ⚠️ 잔여 자유석 {remaining_seats}석 - 이용 주의 필요", broadcast=True, category="seat")

    # === 최종 CSV 로그
    return free_rows, laptop_rows, msg


def render_table(title, rows):
    html_table = f"""
    <div class="table-box">
        <h2>{title}</h2>
        <table class="sortable" data-sortable>
            <thead>
                <tr><th>#</th><th>Seat#</th><th>이름</th><th>상품</th><th>입실시간</th></tr>
            </thead>
            <tbody>
    """
    for idx, (seat_type, seat_number, name, product, start_time, end_time) in enumerate(rows, 1):
        html_table += f"<tr><td>{len(rows) - idx + 1}</td><td>{seat_number}</td><td>{name}</td><td>{product}</td><td class='time'>{start_time.replace('.', '-')}</td></tr>"
    html_table += """
            </tbody>
        </table>
    </div>
    """
    return html_table

def render_table_expire(title, rows):
    html_table = f"""
    <div class="table-box">
        <h2>{title}</h2>
        <table class="sortable" data-sortable>
            <thead>
                <tr><th>#</th><th>Seat#</th><th>이름</th><th>상품</th><th>종료시간</th></tr>
            </thead>
            <tbody>
    """
    for idx, (seat_type, seat_number, name, product, start_time, end_time) in enumerate(rows, 1):
        html_table += f"<tr><td>{idx}</td><td>{seat_number}</td><td>{name}</td><td>{product}</td><td class='time'>{end_time.replace('.', '-')}</td></tr>"
    html_table += """
            </tbody>
        </table>
    </div>
    """
    return html_table



# === 메인 실행 ===
def main_check_seat():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")


    location_tag = find_location()
    print(f"📢 [좌석 - 모니터링] 시작합니다.")

    driver = create_driver()

    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    try:
        if login(driver):
    
            today_user_count = get_today_user_count(driver)
            print(f"[DEBUG] 추출된 누적 사용자 수 텍스트: '{today_user_count}'")

            # ✅ 누적 이용자 수 저장
            if today_user_count is not None:
                cum_users_path = os.path.join(DASHBOARD_PATH, "cum_users_history.csv")
                os.makedirs(os.path.dirname(cum_users_path), exist_ok=True)
                with open(cum_users_path, "a", encoding="utf-8") as f:
                    f.write(f"{now_str},{today_user_count}\n")

                # ✅ 일일 누적 이용자 수 저장 (05시대에만, 하루 1회만 저장)
                now_kst = datetime.now(kst)
                if 5 <= now_kst.hour < 6:
                    daily_count_path = os.path.join(DASHBOARD_PATH, "daily_count_history.csv")
                    os.makedirs(os.path.dirname(daily_count_path), exist_ok=True)
                    # 날짜가 오전 0시~5시 사이 실행 시 전날 날짜로 기록
                    today_date = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d") if now_kst.hour < 5 else now_kst.strftime("%Y-%m-%d")
                    already_written = False
                    if os.path.exists(daily_count_path):
                        with open(daily_count_path, "r", encoding="utf-8") as f:
                            for line in f:
                                if line.startswith(today_date):
                                    already_written = True
                                    break
                    if not already_written:
                        with open(daily_count_path, "a", encoding="utf-8") as f:
                            f.write(f"{today_date},{today_user_count}\n")

                # === 누적 이용자수 경고 임계치 초과 1회 알림 ===
                CUM_ALERT_FLAG_PATH = os.path.join(DASHBOARD_PATH, "cum_alert_flag.txt")
                if today_user_count >= WARNING_CUM_THRESHOLD:
                    already_alerted = False
                    if os.path.exists(CUM_ALERT_FLAG_PATH):
                        with open(CUM_ALERT_FLAG_PATH, "r") as f:
                            if f.read().strip() == today_str:
                                already_alerted = True
                    if not already_alerted:
                        send_broadcast_and_update(f"[안내] 👥 금일 누적 이용자 수 {today_user_count}명 초과", broadcast=True, category="seat")
                        with open(CUM_ALERT_FLAG_PATH, "w") as f:
                            f.write(today_str)

            free_rows, laptop_rows, seat_status_msg  = check_seat_status(driver)
            # Use the same now_str for the monitoring message
            loop_msg = (
                f"\n\n🪑 좌석 모니터링 정상 동작 중\n"
                f"⏰ 날짜 + 실행 시각: {now_str}"
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


def save_seat_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, rows_dict):
    history_path = os.path.join(DASHBOARD_PATH, "seat_history.csv")
    cum_users_path = os.path.join(DASHBOARD_PATH, "cum_users_history.csv")

    # --- Daytime window calculation (KST 5:00 to next 5:00) ---
    now_kst = datetime.now(kst)
    if now_kst.hour < 5:
        start_time = (now_kst - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    else:
        start_time = now_kst.replace(hour=5, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    # ISO strings for Chart.js min/max x axis
    min_ts = start_time.isoformat()
    max_ts = end_time.isoformat()

    # --- 자유석 이력 ---
    history_rows = []
    with open(history_path, "r", encoding="utf-8") as f:
        for line in reversed(f.readlines()):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                timestamp_obj = kst.localize(datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S"))
                if start_time <= timestamp_obj < end_time:
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
        if total_free - y <= DANGER_THRESHOLD:
            point_colors.append('rgba(255, 99, 132, 1)')  # Red
        elif total_free - y <= WARNING_THRESHOLD:
            point_colors.append('rgba(255, 206, 86, 1)')  # Yellow
        else:
            point_colors.append('rgba(75, 192, 192, 0.1)')  # Light gray transparent for normal usage

    
    data_points = [{"x": t, "y": y} for t, y in zip(timestamps, used_frees)]

    # --- 누적 이용자 수 이력 ---
    cum_users_rows = []
    cum_user_counts = []
    try:
        with open(cum_users_path, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    timestamp_obj = kst.localize(datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S"))
                    if start_time <= timestamp_obj < end_time:
                        cum_users_rows.insert(0, line)
                    else:
                        break
        for line in cum_users_rows:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                cum_user_counts.append(int(parts[1]))
    except Exception:
        cum_user_counts = []
    

    # --- 차트 스크립트 (dashboard_monthly.py 스타일) ---
    chart_script = f"""
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <script src='https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns'></script>
    <script>
        const ctx = document.getElementById('seatChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [{{
                    label: '자유석 이용자 수',
                    data: {json.dumps(used_frees)},
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    fill: true,
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: function(context) {{
                        const color = context.dataset.pointBackgroundColor[context.dataIndex];
                        return (color === 'rgba(75, 192, 192, 0.1)') ? 0 : 3;
                    }},
                    pointBackgroundColor: {json.dumps(point_colors)},
                    spanGaps: false
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 30,
                        title: {{
                            display: true,
                            text: '자유석 이용자 수'
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return value + '명';
                            }}
                        }}
                    }},
                    x: {{
                        type: 'time',
                        time: {{
                            unit: 'minute',
                            displayFormats: {{
                                minute: 'HH:mm'
                            }},
                            stepSize: 30
                        }},
                        ticks: {{
                            autoSkip: false,
                            stepSize: 30,
                            source: 'auto'
                        }},
                        min: '{min_ts}',
                        max: '{max_ts}',
                        title: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
    </script>
    """
    update_mode = "M" if args.manual else "B"
    now_str = f"{datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')} ({update_mode})"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <title>좌석 현황</title>
        <meta http-equiv="refresh" content="60">
        <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_seat.css">
        <script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/sorttable/2.1.2/sorttable.min.js"></script>
    </head>
    <body>
        <div class="box">
        
            <div class="stat">🪑 {used_free}/{total_free} · 💻 {used_laptop}/{total_laptop} · 🟩 {remaining}석 · 👥 {cum_user_counts[-1] if cum_user_counts else "정보 없음"}명</div>                        
            <canvas id="seatChart" style="max-width: 100%; height: auto; aspect-ratio: 16 / 12;"></canvas>
            {chart_script}
        
"""

    html += """
    <div class="tables" style="margin-top: 1rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
    """
    # Add separate table for 자유석 종료시간 6시간 이내
    near_expire_rows = []
    now_kst = datetime.now(kst)
    threshold_time = now_kst + timedelta(hours=6)
    for row in rows_dict.get("자유석", []):
        try:
            end_time_str = row[5]
            end_time = datetime.strptime(end_time_str, "%Y.%m.%d %H:%M")
            end_time = kst.localize(end_time)
            if now_kst <= end_time <= threshold_time:
                near_expire_rows.append(row)
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] 종료시간 파싱 실패: {e} | 값: {row[5]}")
            continue

    # Sort near_expire_rows in ascending order of 종료시간
    near_expire_rows.sort(key=lambda x: datetime.strptime(x[5], "%Y.%m.%d %H:%M"))

    if near_expire_rows:
        html += render_table_expire("종료 예정 자유석", near_expire_rows)

    for title, rows in rows_dict.items():
        html += render_table(title, rows)
    
    html += f"""
    </div>        
    </div>
    <div class="updated">Updated {now_str}</div>
    
    """
    # Move the updated line outside the .box, after the entire box
    # (already included inside summary-box, so omit here)
    html += """
    <script>
      document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('table.sortable').forEach(function(table) {
          table.classList.add('sortable');
        });
      });
    </script>
    </body>
    </html>
    """
    with open(os.path.join(DASHBOARD_PATH, "seat_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)
        


# 금일 누적 이용자 수 가져오기 함수
def get_today_user_count(driver):
    try:
        driver.get(f"{BASE_URL}/dashboard")
        if DEBUG:
            print(f"[DEBUG] 현재 대시보드 URL: {driver.current_url}")

        # 텍스트가 숫자일 때까지 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, "today_use_cnt").text.strip().isdigit()
        )
        user_count_text = driver.find_element(By.ID, "today_use_cnt").text.strip()
        today_count = int(user_count_text)

        if DEBUG:
            print(f"[DEBUG] 추출된 사용자 수 텍스트 (오늘): '{today_count}'")

        now_kst = datetime.now(kst)
        if now_kst.hour < 5:
            # 어제 날짜로 대시보드 조회
            yesterday = (now_kst - timedelta(days=1)).strftime("%Y.%m.%d")
            driver.get(f"{BASE_URL}/dashboard?date={yesterday}")
            time.sleep(1)
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.ID, "today_use_cnt").text.strip().isdigit()
            )
            y_text = driver.find_element(By.ID, "today_use_cnt").text.strip()
            yesterday_count = int(y_text)
            if DEBUG:
                print(f"[DEBUG] 어제 사용자 수 텍스트: '{yesterday_count}'")
            return today_count + yesterday_count

        return today_count

    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] 금일 누적 이용자 수 가져오기 실패 (Selenium): {e}")
        return None