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
    log_path = "/home/mmkkshim/anding_bot/log/seat_history.csv"
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
now = datetime.now(kst)


import asyncio


def start_telegram_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_auth_listener.run_listener_async())


import requests
import socket

def save_seat_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, status_emoji):
    history_path = "/home/mmkkshim/anding_bot/log/seat_history.csv"
    history_rows = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            history_rows = lines[-10:]
    timestamps = []
    used_frees = []
    for line in history_rows:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            timestamps.append(parts[0])
            used_frees.append(int(parts[1]))
    # Determine line color based on status_emoji
    if status_emoji == "🔴":
        line_color = 'rgba(255, 99, 132, 1)'  # red
    elif status_emoji == "🟡":
        line_color = 'rgba(255, 206, 86, 1)'  # yellow
    else:
        line_color = 'rgba(75, 192, 192, 1)'  # green
    chart_script = f"""
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <script>
        const ctx = document.getElementById('seatChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {timestamps},
                datasets: [{{
                    label: '자유석 사용 수',
                    data: {used_frees},
                    borderColor: '{line_color}',
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
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
        <title>앤딩스터디카페 좌석 현황</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', 'Arial', sans-serif;
                background: #f4f4f4;
                margin: 0;
                padding: 1rem;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                min-height: 100vh;
                box-sizing: border-box;
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h1 {{
                font-size: 1.4rem;
                margin-bottom: 1rem;
                color: #333;
            }}
            .emoji {{
                font-size: 2.5rem;
                margin-bottom: 1rem;
            }}
            .stat {{
                font-size: 1.1rem;
                margin: 0.3rem 0;
            }}
            .updated {{
                font-size: 0.8rem;
                color: #888;
                margin-top: 1rem;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🪑 앤딩스터디카페 좌석 현황</h1>
            <div class="emoji">{status_emoji}</div>
            <div class="stat">자유석: {used_free}/{total_free}</div>
            <div class="stat">노트북석: {used_laptop}/{total_laptop}</div>
            <div class="stat">남은 자유석: {remaining}석</div>
            <div class="updated">업데이트 시각: {now_str}</div>
            <div style="margin-top:2rem;">
                <h2 style="font-size:1rem; color:#444;">📈 최근 자유석 이용 추이</h2>
                <canvas id="seatChart" height="200"></canvas>
                {chart_script}
            </div>
        </div>
    </body>
    </html>
    """
    with open("/home/mmkkshim/anding_bot/seat_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
        


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
            seat_type = cols[8].text.strip()       # 결제상품 (예: 스터디룸(2인) 등)
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

    # 텔레그램 메시지 등 전송 메시지 구성
    msg_lines = [
        f"결제 ID: {p['id']}, 사용자: {p['user']}, 좌석: {p['seat_type']}, 금액: {p['amount']}, 상태: {p['status']}"
        for p in new_payments
    ]
    msg = "[결제 알림]\n" + "\n".join(msg_lines) if msg_lines else "새로운 결제 내역이 없습니다."

    # 대시보드 HTML 저장 함수 호출 (기존 구현)
    save_payment_dashboard_html(payments)

    return msg


    today = datetime.now(kst).strftime("%Y.%m.%d")
    summary_time = datetime.now(kst).strftime("%H:%M")
    summary_count = len(payments)
    summary_amount = sum(int(p['amount'].replace(',', '').replace('원', '')) for p in payments if p['amount'])

    html_rows = ""
    for row in payments:
        html_rows += f"""
            <tr>
                <td>{row['id']}</td>
                <td>{row['user']}</td>
                <td>{row['amount']}</td>
                <td>{row['seat_type']}</td>
                <td>{row['date']}</td>
            </tr>
        """
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>오늘 결제 현황</title>
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
                background: #f1f3f5;
                padding: 2rem;
                margin: 0;
                display: flex;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 1rem;
                box-shadow: 0 5px 20px rgba(0,0,0,0.08);
                padding: 2rem;
                width: 100%;
                max-width: 900px;
            }}
            .updated {{
                font-size: 0.8rem;
                color: #888;
                margin-top: 1rem;
            }}            
            h2 {{
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: #343a40;
                text-align: center;
            }}
            .summary {{
                font-size: 0.95rem;
                margin-bottom: 1rem;
                color: #555;
                text-align: center;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                background: white;
                border-radius: 0.5rem;
                overflow: hidden;
            }}
            th, td {{
                border: 1px solid #dee2e6;
                padding: 0.75rem;
                text-align: center;
                font-size: 0.90rem;
                color: #343a40;
            }}
            th {{
                background-color: #6c757d;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>오늘 결제 현황</h2>
            <div class="summary">
                날짜: {today}<br>
                총 결제: {summary_count}건 / {summary_amount}원<br>
            </div>
            <div class="updated">업데이트 시각: {now_str}</div>            
            <table>
                <thead>
                    <tr>
                        <th>결제번호</th>
                        <th>이름</th>
                        <th>금액</th>
                        <th>상품</th>
                        <th>결제일</th>
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




    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")

    
    location_tag = find_location()
    send_telegram_and_log(f"📢 [결제 - 모니터링] 시작합니다.")

    driver = create_driver()

    try:
        if login(driver):
            payment_status_msg = check_payment_status(driver)
            now_full_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            loop_msg = (
                f"\n\n🧾 결제 모니터링 정상 동작 중\n"
                f"⏰ 날짜 + 실행 시각: {now_full_str}"
            )
            full_msg = loop_msg + "\n\n" + payment_status_msg
            send_broadcast_and_update(full_msg, broadcast=False, category="payment")

            send_telegram_and_log(f"{location_tag} ✅ [결제 - 모니터링] 정상 종료되었습니다.")
        else:
            send_broadcast_and_update("❌ [결제] 로그인 실패", broadcast=False, category="payment")
    except Exception as e:
        send_broadcast_and_update(f"❌ [결제 오류] {e}", broadcast=False, category="payment")
    finally:
        driver.quit()