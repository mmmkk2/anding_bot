import sys
from bs4 import BeautifulSoup
from datetime import datetime
import os
import time
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import TimeoutException, NoSuchElementException
# --- Set 종료일 to today, click 검색, and wait for table update ---
from selenium.webdriver.common.keys import Keys
from datetime import datetime

from datetime import datetime
import argparse
import pytz
from dotenv import load_dotenv

# === 설정 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# Dashboard path for logs and HTML
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH")
DEBUG_PATH = os.getenv("DEBUG_PATH")

# Add DEBUG switch after loading .env
parser = argparse.ArgumentParser()
parser.add_argument("--manual", action="store_true", help="수동 실행 모드 (디버깅 비활성화)")
parser.add_argument("--hide", action="store_true", help="디버그 메시지 숨김")
parser.add_argument("--date", nargs="?", type=str, default=None, help="조회 기준 날짜 (예: '2025.05.21')")

args = parser.parse_args()
print(args)

DEBUG_ENV = os.getenv("DEBUG", "true").lower() == "true"
DEBUG = not args.hide and DEBUG_ENV

print(f"[DEBUG CHECK] args.manual = {args.manual}")
print(f"[DEBUG CHECK] args.hide = {args.hide}")
print(f"[DEBUG CHECK] os.getenv('DEBUG') = {os.getenv('DEBUG')}")
print(f"[DEBUG CHECK] DEBUG_ENV = {DEBUG_ENV}")
print(f"[DEBUG CHECK] DEBUG = {DEBUG}")
print(f"[DEBUG MODE] {'ON' if DEBUG else 'OFF'}")

# KST
kst = pytz.timezone("Asia/Seoul")
today_str = datetime.now(kst).strftime("%Y.%m.%d")

target_date = args.date if args.date else today_str

BASE_URL = os.getenv("BASE_URL")
ROOM_URL = f"{BASE_URL}/use/studyUse"


def check_studyroom(driver):

    if DEBUG: print("[DEBUG] 예약룸 페이지 진입 시도 중:", ROOM_URL)
    time.sleep(2)  # 로그인 후 쿠키 세팅 대기
    driver.get(ROOM_URL)
    if DEBUG: print("[DEBUG] 현재 페이지 URL:", driver.current_url)
    if DEBUG: print("[DEBUG] 현재 페이지 TITLE:", driver.title)
    if DEBUG: print("[DEBUG] 예약룸 진입 완료")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-sm-4.mb-sm-2 input"))
        )
        if DEBUG: print("[DEBUG] 종료일 입력 필드 로딩 완료")
        if DEBUG: print("[DEBUG] 종료일 입력 필드에 날짜 입력 시도:", datetime.now(kst).strftime("%Y.%m.%d"))
    except TimeoutException:
        raise Exception("❌ [예약룸 오류] 종료일 입력 필드를 찾을 수 없습니다.")

    # (테이블 대기 삭제됨: 검색 버튼 클릭 이후로 이동)
    today_date_str = datetime.now(kst).strftime("%Y.%m.%d")

    # Set the 종료일 input field using JavaScript
    end_input = driver.find_element(By.CSS_SELECTOR, "input[name='s_end_date']")
    if DEBUG: print("[DEBUG] 종료일 input 태그 구조 (name='s_end_date'):", end_input.get_attribute("outerHTML"))
    script = f"document.querySelector('input[name=\"s_end_date\"]').value = '{today_date_str}';"
    driver.execute_script(script)
    time.sleep(0.5)
    value_after = driver.execute_script("return document.querySelector('input[name=\"s_end_date\"]').value;")
    if DEBUG: print("[DEBUG] JS로 설정된 종료일 값:", value_after)
    
    # Click the 검색 버튼 (parent of <i class="fas fa-search"></i>)
    search_button = driver.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-search)")
    if DEBUG: print("[DEBUG] 검색 버튼 태그 구조:", search_button.get_attribute("outerHTML"))
    search_button.click()
    if DEBUG: print("[DEBUG] 검색 버튼 클릭 완료")
    time.sleep(1.5)  # Ensure search results load fully before parsing

    # 검색 버튼 클릭 후, 테이블 행이 로드될 때까지 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='m_table_1']//tbody/tr[not(contains(@class, 'dataTables_empty'))]"))
        )
        if DEBUG: print("[DEBUG] 예약룸 테이블 로딩 완료")
        time.sleep(1.5)  # JS에서 row 생성 시간 확보
    except TimeoutException:
        with open(os.path.join(DEBUG_PATH, "debug_studyroom_timeout.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("❌ [예약룸 오류] 유효한 예약 데이터를 포함한 행이 나타나지 않았습니다.")

    rows = driver.find_elements(By.CSS_SELECTOR, "table#m_table_1 tbody tr")
    if DEBUG: print(f"[DEBUG] 검색 결과 행 수: {len(rows)}")

    reservations_2 = []
    reservations_4 = []


    for row in rows:
        if "dataTables_empty" in row.get_attribute("class"):
            continue

        cols = row.find_elements(By.TAG_NAME, "td")
        if DEBUG: print("[DEBUG] row HTML:", row.get_attribute("outerHTML"))
        if DEBUG: print("[DEBUG] col count:", len(cols))
        for i, col in enumerate(cols):
            if DEBUG: print(f"[DEBUG] col[{i}] text: {col.text.strip()}")
        if len(cols) >= 6:
            room_type = cols[1].text.strip()
            name = cols[2].text.strip()
            start_time = cols[4].text.strip()
            end_time = cols[5].text.strip()

            if DEBUG: print("[DEBUG] 추출된 값:", {
                "room_type": room_type,
                "name": name,
                "start_time": start_time,
                "end_time": end_time
            })

            date_part = end_time.split(" ")[0]
            reservation_time = f"{start_time} ~ {end_time}"

            if DEBUG:
                print("[DEBUG] 예약행:", {
                    "room_type": room_type, "name": name,
                    "end_time": end_time, "date_part": date_part, "today": today_str
                })

            if date_part == today_str:
                if "2인" in room_type:
                    room_label = "2인실"
                    reservations_2.append({
                        "date": date_part,
                        "time": reservation_time,
                        "name": name,
                        "room": room_label
                    })
                elif "4인" in room_type:
                    room_label = "4인실"
                    reservations_4.append({
                        "date": date_part,
                        "time": reservation_time,
                        "name": name,
                        "room": room_label
                    })
            else:
                if DEBUG:
                    print("[DEBUG] 필터 제외됨:", {
                        "room_type": room_type,
                        "name": name,
                        "end_time": end_time,
                        "date_part": date_part,
                        "today_str": today_str
                    })

    count_2 = len(reservations_2)
    count_4 = len(reservations_4)

    reservations_2.sort(key=lambda x: x['time'].split('~')[0].strip())
    reservations_4.sort(key=lambda x: x['time'].split('~')[0].strip())

    # --- Removed is_currently_in_use function and usage calculation ---

    html_rows_2 = "\n".join(
        f"<tr><td>{r['time']}</td><td>{r['name']}</td></tr>"
        for r in reservations_2
    )
    html_rows_4 = "\n".join(
        f"<tr><td>{r['time']}</td><td>{r['name']}</td></tr>"
        for r in reservations_4
    )

    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>스터디룸 예약 현황</title>
        <meta http-equiv="refresh" content="60">
        <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_studyroom.css">
    </head>
    <body>
        <div class="box">
            <div class="tables">
                <div class="table-box">
                    <h2>2인실</h2>
                    <table>
                        <thead>
                            <tr><th>시간</th><th>이름</th></tr>
                        </thead>
                        <tbody>
                            {html_rows_2}
                        </tbody>
                    </table>
                </div>
                <div class="table-box">
                    <h2>4인실</h2>
                    <table>
                        <thead>
                            <tr><th>시간</th><th>이름</th></tr>
                        </thead>
                        <tbody>
                            {html_rows_4}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="summary">
                2인실 : 예약: {count_2}건<br>
                4인실 : 예약: {count_4}건
            </div>
            <div class="updated">Updated {now_str}</div>            
        </div>
    </body>
    </html>
    """

    # Always print a summary, even if DEBUG is False
    total_reservations = count_2 + count_4
    if total_reservations == 0 and not DEBUG:
        print("[INFO] 완료: 예약 건수가 없어 출력하지 않았습니다.")
    elif not DEBUG:
        print(f"[INFO] 완료: {total_reservations}건의 예약 정보를 HTML로 저장했습니다.")

    with open(os.path.join(os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/"), "studyroom_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)



def main_check_studyroom():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")

    location_tag = find_location()
    # send_telegram_and_log(f"📢 [결제 - 모니터링] 시작합니다.")  # Disabled Telegram notification

    driver = create_driver()

    try:
        if login(driver):
            check_studyroom(driver)
            # send_telegram_and_log(f"{location_tag} ✅ [결제 - 모니터링] 정상 종료되었습니다.")  # Disabled Telegram notification
        else:
            send_broadcast_and_update("❌ [예약룸] 로그인 실패", broadcast=True, category="studyroom")
    except Exception as e:
        # send_broadcast_and_update(f"❌ [예약룸 오류] {e}", broadcast=False, category="studyroom")  # Disabled broadcast in except
        pass
    finally:
        driver.quit()
