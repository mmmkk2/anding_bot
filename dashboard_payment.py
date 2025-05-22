import sys
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log

import os
import time
import pickle
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from datetime import datetime
import argparse
import pytz

kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)
today_str = now.strftime("%Y.%m.%d")


# === 설정 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# Dashboard path for logs and HTML
DEBUG_PATH = os.getenv("DEBUG_PATH")
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH")


# Add manual mode switch after loading .env
# Default: DEBUG is True unless --manual is passed
parser = argparse.ArgumentParser()
parser.add_argument("--manual", action="store_true", help="수동 실행 모드 (디버깅 비활성화)")
args = parser.parse_args()
DEBUG = not args.manual and os.getenv("DEBUG", "true").lower() == "true"

PAYMENT_CACHE_FILE = os.getenv("COOKIE_FILE")


BASE_URL = os.getenv("BASE_URL")
PAYMENT_URL = f"{BASE_URL}/pay/payHist"



# === Payment logic merged from main_payment.py ===


def check_payment_status(driver):
    if DEBUG:
        print("[DEBUG] 결제 페이지 진입 시도 중:", PAYMENT_URL)
    time.sleep(2)  # 로그인 후 쿠키 세팅 대기
    driver.get(PAYMENT_URL)
    if DEBUG:
        print("[DEBUG] 페이지 진입 완료")

    # === 초기 테이블 존재 여부 확인 ===
    table_rows = driver.find_elements(By.CSS_SELECTOR, "table#m_table_1 tbody tr")
    if not table_rows:
        if DEBUG:
            print("[DEBUG] 결제 테이블이 비어 있음 → HTML 생성 시도")
        save_payment_dashboard_html([])
        return

    # === 날짜 필터: 결제일자 시작~종료일을 오늘로 설정 ===
    today_date_str = datetime.now(kst).strftime("%Y.%m.%d")
    if DEBUG:
        print(f"[DEBUG] 오늘 날짜 기준 결제 필터: {today_date_str}")
    try:
        start_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_pay_date_start']")))
        driver.execute_script(f"document.querySelector('input[name=\"s_pay_date_start\"]').value = '{today_date_str}';")
        end_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='s_pay_date_end']")))
        driver.execute_script(f"document.querySelector('input[name=\"s_pay_date_end\"]').value = '{today_date_str}';")
        time.sleep(0.5)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] 결제일자 필터 및 검색 실패: {e}")

    # 검색 버튼 클릭 (아이콘을 포함하는 부모 버튼 클릭)
    try:
        search_button = driver.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-search)")
        if DEBUG:
            print("[DEBUG] 검색 버튼 태그 구조:", search_button.get_attribute("outerHTML"))
        search_button.click()
        if DEBUG:
            print("[DEBUG] 검색 버튼 클릭 완료")
        time.sleep(1.5)
    except Exception as e:
        if DEBUG:
            print("[DEBUG] 검색 버튼 클릭 실패:", e)

    try:
        # 데이터가 실제로 존재하는 경우를 감지 (이전 table row 확인은 사전 처리됨)
        # 실제 데이터가 채워진 row가 나타날 때까지 대기 (빈 값이 아닌 이름 칸)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='m_table_1']//tbody//tr/td[2][normalize-space(text()) != '']"))
        )
        if DEBUG:
            print("[DEBUG] 결제 테이블 로딩 완료")
        time.sleep(1.5)  # JS에서 row 생성 시간 확보
    except TimeoutException:
        with open(os.path.join(DEBUG_PATH, "debug_payment_timeout.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("❌ [결제 오류] 결제 테이블의 유효한 데이터를 찾을 수 없습니다.")

    payments = []
    while True:
        # 여기서는 id를 기준으로 테이블 내 tbody의 row들을 모두 가져옵니다.
        rows = driver.find_elements(By.CSS_SELECTOR, "table#m_table_1 tbody tr")
        if DEBUG:
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
        if DEBUG:
            for payment in payments:
                pay_date = payment["date"].split()[0].replace("-", ".")
                print(f"[DEBUG] 결제일자 원본: {payment['date']}, 변환 후: {pay_date}, 오늘 기준: {today_str}")

        # 페이지네이션: '다음' 버튼이 활성화되어 있으면 클릭, 아니면 종료
        try:
            next_li = driver.find_element(By.CSS_SELECTOR, 'ul.pagination li.next')
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
        except Exception as e:
            with open(os.path.join(DEBUG_PATH, "debug_payment_error.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise Exception(f"❌ [결제 파싱 오류] {e}")

    # 날짜 기준 필터링 (오늘 날짜만 유지)
    today_only = []
    for payment in payments:
        pay_date = payment["date"].split()[0].replace("-", ".")
        if pay_date == today_str:
            today_only.append(payment)
    if DEBUG:
        print(f"[DEBUG] 오늘 결제 내역 개수: {len(today_only)}")
        print(f"[DEBUG] 오늘 결제 내역 개수: {len(today_only)} (HTML 생성 여부 무관)")

    # 마지막으로 읽은 결제 ID와 새 결제 내역 비교
    last_payment_id = None
    if os.path.exists(PAYMENT_CACHE_FILE):
        with open(PAYMENT_CACHE_FILE, "rb") as f:
            last_payment_id = pickle.load(f)

    new_payments = []
    for payment in today_only:
        if last_payment_id is None or payment["id"] > last_payment_id:
            new_payments.append(payment)

    # 가장 최신의 결제 ID 저장
    if today_only:
        with open(PAYMENT_CACHE_FILE, "wb") as f:
            pickle.dump(today_only[0]["id"], f)

    # 대시보드 HTML 저장 함수 호출 (항상 호출, today_only가 비어도)
    save_payment_dashboard_html(today_only)
    if DEBUG:
        print("[DEBUG] 대시보드 HTML 저장 완료 요청됨.")


def save_payment_dashboard_html(payments):
    today = now.strftime("%Y.%m.%d")
    summary_time = now.strftime("%H:%M")
    summary_count = len(payments)
    # summary_amount = sum(int(p['amount'].replace(',', '').replace('원', '')) for p in payments if p['amount'])
    summary_amount = sum(
        int(p['amount'].replace(',', '').replace('원', ''))
        for p in payments
        if p['amount'] and '승인' in p['status']
    )
    if DEBUG:
        print(f"[DEBUG] save_payment_dashboard_html: 전달된 결제 내역 개수: {len(payments)}")
        if not payments:
            print("[DEBUG] save_payment_dashboard_html: 결제 내역이 비어 있음. HTML은 그래도 생성됨.")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    if not payments:
        html_rows = "<tr><td colspan='5'>오늘 결제 내역이 없습니다.</td></tr>"
    else:
        html_rows = ""
        for row in payments:
            html_rows += f"""
                <tr>
                    <td class="number">{row['id']}</td>
                    <td class="user">{row['user']}</td>
                    <td class="amount">{row['amount']}</td>
                    <td class="seat">{row['seat_type']}</td>
                    <td class="time">{row['date'][:10]} {row['date'][11:19]}</td>
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
                padding: 0.5rem;
                margin: 0;
                display: flex;
                align-items: flex-start;
                justify-content: center;
                text-align: center;
                max-width: 100vw;
                height: auto;
                min-height: 0;
                box-sizing: border-box;
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1rem;
                max-width: 650px;         /* 데스크탑 기준 최대 폭 */
                width: 100%;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
                margin: 0 auto;
            }}
            @media (max-width: 480px) {{
                .box {{
                max-width: 95vw;
                /* padding: 1.2rem; */
                min-height: 90vh;  /* 화면 높이의 90%까지 확장 */
                }}
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
            .number {{
                font-size: 0.7rem;
                min-width: 20px;
                padding: 0.4rem;
            }}            
            .user {{
                min-width: 40px;
            }}
            .amount {{            
                font-size: 0.7rem;
                min-width: 50px;
            }}
            .seat {{
                font-size: 0.7rem;
                padding: 0.1rem;  
                word-break: break-word;
                white-space: normal; 
                min-width: 58px;
                max-width: 90px; /*
            }}            
            .time {{
                font-size: 0.7rem;
                padding: 0.4rem;
                word-break: break-word;
                white-space: normal; 
                min-width: 50px;               
                max-width: 90px; /*
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <div class="updated">📅 기준 날짜: <b>{today_str}</b></div>
            <div class="summary">
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

    output_path = os.path.join(DASHBOARD_PATH, "payment_dashboard.html")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        if DEBUG:
            print(f"[완료] 결제 대시보드 HTML 저장됨: {output_path}")
    except Exception as e:
        print(f"[오류] 결제 대시보드 HTML 저장 실패: {e}")

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