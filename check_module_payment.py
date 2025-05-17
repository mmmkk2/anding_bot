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

COOKIE_FILE = os.getenv("COOKIE_FILE") or "/home/mmkkshim/anding_bot/log/last_payment_id.pkl"
BASE_URL = "https://partner.cobopay.co.kr"


from datetime import datetime
import pytz

kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)

import requests

# === Payment logic merged from main_payment.py ===

PAYMENT_URL = f"{BASE_URL}/pay/payHist"
PAYMENT_CACHE_FILE = COOKIE_FILE


from selenium.common.exceptions import TimeoutException, NoSuchElementException


def check_payment_status(driver):
    print("[DEBUG] 결제 페이지 진입 시도 중:", PAYMENT_URL)
    time.sleep(2)  # 로그인 후 쿠키 세팅 대기
    driver.get(PAYMENT_URL)
    print("[DEBUG] 페이지 진입 완료")

    try:
        # '이름' 컬럼이 있는 테이블이 로드될 때까지 대기 (페이지의 결제 테이블에는 id="m_table_1"가 있음)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='m_table_1']//th[contains(text(), '이름')]"))
        )
        print("[DEBUG] '이름' 컬럼 있는 테이블 로딩 완료")
        time.sleep(1.5)  # JS에서 row 생성 시간 확보
    except TimeoutException:
        with open("debug_payment_timeout.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("❌ [결제 오류] '이름' 컬럼이 포함된 테이블을 찾을 수 없습니다.")

    payments = []
    while True:
        # 여기서는 id를 기준으로 테이블 내 tbody의 row들을 모두 가져옵니다.
        rows = driver.find_elements(By.CSS_SELECTOR, "table#m_table_1 tbody tr")
        print(f"[DEBUG] 로드된 row 수: {len(rows)}")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            # 스크린샷으로 파악한 결제 내역 테이블은 12개의 열이 있어야 함
            if len(cols) < 12:
                continue

            # 스크린샷 기반 열 인덱스
            payment_id = cols[0].text.strip()    # No (결제 ID)
            user_name = cols[1].text.strip()       # 이름
            # cols[2]는 전화번호, cols[3]는 결제방법, cols[4]는 결제수단
            status = cols[5].text.strip()          # 결제상태 (예: 승인완료)
            amount = cols[6].text.strip()          # 결제금액
            payment_date = cols[7].text.strip()    # 결제일시
            seat_type = cols[8].text.strip().split("/")[0] + " / " + cols[9].text.strip()      # 결제상품 (예: 스터디룸(2인) 등)
            

            # cols[9]는 시작시간, cols[10]는 종료시간, cols[11]는 가입일

            payments.append({
                "id": payment_id,
                "date": payment_date,
                "user": user_name,
                "seat_type": seat_type,
                "amount": amount,
                "status": status
            })

        # 페이지네이션: '다음' 버튼이 활성화되어 있으면 클릭, 아니면 종료
        try:
            next_li = driver.find_element(By.CSS_SELECTOR, 'ul.pagination li.next')
            if "disabled" in next_li.get_attribute("class"):
                print("[DEBUG] 다음 페이지 없음 → 루프 종료")
                break
            next_btn = next_li.find_element(By.TAG_NAME, "a")
            next_btn.click()
            print("[DEBUG] 다음 페이지 클릭")
            time.sleep(1.5)  # 다음 페이지 로딩 시간 확보
        except NoSuchElementException:
            print("[DEBUG] 페이지네이션 요소 없음 → 루프 종료")
            break
        except Exception as e:
            with open("debug_payment_error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise Exception(f"❌ [결제 파싱 오류] {e}")

    # 마지막으로 읽은 결제 ID와 새 결제 내역 비교
    last_payment_id = None
    if os.path.exists(PAYMENT_CACHE_FILE):
        with open(PAYMENT_CACHE_FILE, "rb") as f:
            last_payment_id = pickle.load(f)

    new_payments = []
    for payment in payments:
        if last_payment_id is None or payment["id"] > last_payment_id:
            new_payments.append(payment)

    # 가장 최신의 결제 ID 저장
    if payments:
        with open(PAYMENT_CACHE_FILE, "wb") as f:
            pickle.dump(payments[0]["id"], f)

    # 대시보드 HTML 저장 함수 호출 (기존 구현)
    save_payment_dashboard_html(payments)


def save_payment_dashboard_html(payments):
    today = datetime.now(kst).strftime("%Y.%m.%d")
    summary_time = datetime.now(kst).strftime("%H:%M")
    summary_count = len(payments)
    summary_amount = sum(int(p['amount'].replace(',', '').replace('원', '')) for p in payments if p['amount'])
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    html_rows = ""
    for row in payments:
        html_rows += f"""
            <tr>
                <td>{row['id']}</td>
                <td>{row['user']}</td>
                <td>{row['amount']}</td>
                <td class="breakable">{row['seat_type']}</td>
                <td class="breakable">{row['date'][:10]} {row['date'][11:19]}</td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>오늘 결제 현황</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
                background: #f1f3f5;
                padding: 1rem;
                margin: 0;
                display: flex;
                align-items: flex-start;
                min-height: 100vh;
                box-sizing: border-box;
                justify-content: center;
                text-align: center;  /* 텍스트 정렬 보정 */
                max-width: 100vw;
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1rem;
                max-width: 600px;         /* 데스크탑 기준 최대 폭 */
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
                padding: 0.1rem;
            }}
            th {{
                background-color: #6c757d;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            .breakable {{
                padding: 0.4rem;
                word-break: break-word;
                white-space: normal;
                max-width: 50px;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>오늘 결제 현황</h1>
            <div class="summary">
                날짜: {today}<br>
                총 결제: {summary_count}건 / {summary_amount:,}원<br>
            </div>
            <div class="updated">업데이트 시각: {now_str}</div>
            <table>
                <thead>
                    <tr>
                        <th>번호</th>
                        <th>이름</th>
                        <th>금액</th>
                        <th>상품</th>
                        <th>결제일시</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    with open("/home/mmkkshim/anding_bot/payment_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)


def main_check_payment():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")

    location_tag = find_location()
    # send_telegram_and_log(f"📢 [결제 - 모니터링] 시작합니다.")  # Disabled Telegram notification

    driver = create_driver()

    try:
        if login(driver):
            check_payment_status(driver)
            # send_telegram_and_log(f"{location_tag} ✅ [결제 - 모니터링] 정상 종료되었습니다.")  # Disabled Telegram notification
        else:
            send_broadcast_and_update("❌ [결제] 로그인 실패", broadcast=False, category="payment")
    except Exception as e:
        # send_broadcast_and_update(f"❌ [결제 오류] {e}", broadcast=False, category="payment")  # Disabled broadcast in except
        pass
    finally:
        driver.quit()