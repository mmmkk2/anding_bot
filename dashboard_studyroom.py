from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os
import time
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC




BASE_URL = "https://partner.cobopay.co.kr"
ROOM_URL = f"{BASE_URL}/use/studyUse"

kst = pytz.timezone("Asia/Seoul")
today_str = datetime.now(kst).strftime("%Y.%m.%d")

from selenium.common.exceptions import TimeoutException, NoSuchElementException
# --- Set 종료일 to today, click 검색, and wait for table update ---
from selenium.webdriver.common.keys import Keys
from datetime import datetime

def check_studyroom(driver):

    print("[DEBUG] 예약룸 페이지 진입 시도 중:", ROOM_URL)
    time.sleep(2)  # 로그인 후 쿠키 세팅 대기
    driver.get(ROOM_URL)
    print("[DEBUG] 예약룸 진입 완료")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-sm-4.mb-sm-2 input"))
        )
        print("[DEBUG] 종료일 입력 필드 로딩 완료")
        print("[DEBUG] 종료일 입력 필드에 날짜 입력 시도:", datetime.now(kst).strftime("%Y.%m.%d"))
    except TimeoutException:
        raise Exception("❌ [예약룸 오류] 종료일 입력 필드를 찾을 수 없습니다.")

    # (테이블 대기 삭제됨: 검색 버튼 클릭 이후로 이동)
    today_date_str = datetime.now(kst).strftime("%Y.%m.%d")

    # Set the 종료일 input field
    end_input = driver.find_element(By.CSS_SELECTOR, "div.col-sm-4.mb-sm-2 input")
    end_input.clear()
    end_input.send_keys(today_date_str)
    end_input.send_keys(Keys.RETURN)
    print("[DEBUG] 종료일 입력 완료 및 엔터 전송")
    
    # Click the 검색 버튼 (parent of <i class="fas fa-search"></i>)
    search_button = driver.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-search)")
    search_button.click()
    print("[DEBUG] 검색 버튼 클릭 완료")

    # 검색 버튼 클릭 후, 테이블 행이 로드될 때까지 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='m_table_1']//tbody/tr[not(contains(@class, 'dataTables_empty'))]"))
        )
        print("[DEBUG] 예약룸 테이블 로딩 완료")
        time.sleep(1.5)  # JS에서 row 생성 시간 확보
    except TimeoutException:
        with open("debug_studyroom_timeout.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("❌ [예약룸 오류] 유효한 예약 데이터를 포함한 행이 나타나지 않았습니다.")

    soup = BeautifulSoup(driver.page_source, "html.parser")

    table = soup.select_one("table")
    rows = table.select("tbody tr") if table else []

    reservations = []


    for row in rows:
        cols = row.find_all("td")
        print(cols)
        if len(cols) >= 6:
            reserve_date = cols[0].text.strip()
            reserve_time = cols[1].text.strip()
            name = cols[2].text.strip()
            room_type = cols[3].text.strip()
            start_time = cols[4].text.strip()
            end_time = cols[5].text.strip()

            date_part = end_time.split(" ")[0]
            reservation_time = f"{start_time} ~ {end_time}"

            if date_part == today_str and ("2인실" in room_type or "4인실" in room_type):
                reservations.append({
                    "date": date_part,
                    "time": reservation_time,
                    "name": name,
                    "room": room_type
                })

    count_2 = sum(1 for r in reservations if "2인실" in r["room"])
    count_4 = sum(1 for r in reservations if "4인실" in r["room"])

    html_rows = "\n".join(
        f"<tr><td>{r['time']}</td><td>{r['name']}</td><td>{r['room']}</td></tr>"
        for r in reservations
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
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
                background: #f1f3f5;
                padding: 0.5rem;
                margin: 0;
                display: flex;
                align-items: flex-start;
                min-height: 100vh;
                box-sizing: border-box;
                justify-content: center;
                text-align: center;
                max-width: 100vw;
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1rem;
                max-width: 650px;
                width: 100%;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
                margin: 0 auto;
            }}
            h1 {{
                font-size: 1.1rem;
                margin-bottom: 1rem;
                color: #333;
            }}
            .summary {{
                font-size: 1rem;
                margin-bottom: 1rem;
                color: #555;
            }}
            .updated {{
                font-size: 0.8rem;
                color: #888;
                margin-top: 1rem;
                text-align: center;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.8rem;
                margin-top: 1rem;
            }}
            th, td {{
                border: 1px solid #dee2e6;
                padding: 0.2rem;
            }}
            th {{
                background-color: #6c757d;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>📋 스터디룸 예약 현황</h1>
            <div class="summary">
                🧑‍🤝‍🧑 2인실 예약: {count_2}건<br>
                👨‍👨‍👧‍👦 4인실 예약: {count_4}건
            </div>
            <div class="updated">업데이트 시각: {now_str}</div>
            <table>
                <thead>
                    <tr><th>시간</th><th>이름</th><th>룸</th></tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    with open("/home/mmkkshim/anding_bot/studyroom_dashboard.html", "w", encoding="utf-8") as f:
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
            send_broadcast_and_update("❌ [예약룸] 로그인 실패", broadcast=False, category="payment")
    except Exception as e:
        # send_broadcast_and_update(f"❌ [예약룸 오류] {e}", broadcast=False, category="payment")  # Disabled broadcast in except
        pass
    finally:
        driver.quit()
