import os
import time
import pickle
import csv
from datetime import datetime
from module.set import create_driver, login, send_telegram_and_log, update_dashboard, find_location

# Load .env configuration file path from environment variable if provided
from dotenv import load_dotenv
dotenv_path = os.getenv("DOTENV_PATH", "/home/mmkkshim/anding_bot/.env")
load_dotenv(dotenv_path)

PAYMENT_LOG_FILE = "dashboard_log/payment_log.csv"
COOKIE_FILE = "log/last_payment_id.pkl"
BASE_URL = "https://partner.cobopay.co.kr"
PAYMENT_URL = f"{BASE_URL}/pay/payHist"

def get_today_payment_summary():
    today = datetime.now().strftime("%Y.%m.%d")
    total_amount = 0
    total_count = 0
    payments = []

    if not os.path.exists(PAYMENT_LOG_FILE):
        return total_count, total_amount, payments

    with open(PAYMENT_LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_field = row.get("date", "").strip()
            if not date_field.startswith(today):
                continue

            try:
                payment_id = row.get("payment_id", "").strip()
                name = row.get("name", "").strip()
                amount = int(row.get("amount", "0").replace(",", "").replace("원", ""))
                product = row.get("product", "").strip()
                date = row.get("date", "").strip()

                payments.append({
                    "datetime": row.get("datetime", "").strip(),
                    "payment_id": payment_id,
                    "name": name,
                    "amount": f"{amount:,}원",
                    "product": product,
                    "date": date,
                })

                total_amount += amount
                total_count += 1

            except Exception as e:
                print(f"[무시된 결제 데이터] {row} - {e}")
                continue

    return total_count, total_amount, payments

def generate_html_table(payments):
    if not payments:
        return "<p>(결제 데이터 없음)</p>"

    payments_sorted = sorted(payments, key=lambda x: int(x['payment_id']), reverse=True)

    html = "<table border='1' cellspacing='0' cellpadding='5'><tr><th>날짜시간</th><th>결제번호</th><th>이름</th><th>금액</th><th>상품</th><th>결제일</th></tr>"
    for p in payments_sorted:
        html += f"<tr><td>{p['datetime']}</td><td>{p['payment_id']}</td><td>{p['name']}</td><td>{p['amount']}</td><td>{p['product']}</td><td>{p['date']}</td></tr>"
    html += "</table>"
    return html

def main_check_payment():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")
            
    loop_min = 5
    total_loops = 1440 // loop_min
    now = datetime.now()
    minutes_since_midnight = now.hour * 60 + now.minute
    current_loop = (minutes_since_midnight // loop_min) + 1

    location_tag = find_location()

    send_telegram_and_log(f"{location_tag} 📢 [결제 - 모니터링] 시작합니다.")

    try:
        driver = create_driver()
    except Exception as e:
        send_telegram_and_log(f"[ChromeDriver 오류] 드라이버 생성 실패: {e}")
        return
    now_full_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    loop_msg = (
        f"\n\n🪑 결제 모니터링 정상 동작 중\n"
        f"Loop {current_loop}/{total_loops}\n"
        f"⏰ 날짜 + 실행 시각: {now_full_str}"
    )
    send_telegram_and_log(f"{loop_msg} \n\n")
    update_dashboard("payment", loop_msg)

    try:
        if not login(driver):
            send_telegram_and_log("[결제] 로그인 실패")
            return

        driver.get(PAYMENT_URL)
        time.sleep(2)

        rows = driver.find_elements("css selector", "table tbody tr")
        if not rows:
            update_dashboard("payment", "(결제 데이터 없음)")
            return

        existing_ids = set()
        if os.path.exists(PAYMENT_LOG_FILE):
            with open(PAYMENT_LOG_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row.get("payment_id", "").strip())

        payments_today = []
        new_payments = []
        today_str = datetime.now().strftime("%Y.%m.%d")

        for row in rows:
            cols = row.find_elements("tag name", "td")
            if len(cols) < 8:
                continue

            payment_id = cols[0].text.strip()
            name = cols[1].text.strip()
            amount = cols[6].text.strip().replace(",", "").replace("원", "")
            date = cols[7].text.strip()
            product = cols[4].text.strip()

            if today_str in date and payment_id not in existing_ids:
                payment_record = {
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'payment_id': payment_id,
                    'name': name,
                    'amount': amount,
                    'product': product,
                    'date': date
                }
                new_payments.append(payment_record)

                payment_message = f"[결제 발생] 결제번호: {payment_id} / 이름: {name} / 금액: {amount}원 / 상품: {product} / 시간: {date}"
                send_telegram_and_log(payment_message, broadcast=True)

        if new_payments:
            os.makedirs("dashboard_log", exist_ok=True)
            file_exists = os.path.exists(PAYMENT_LOG_FILE)
            with open(PAYMENT_LOG_FILE, "a", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=new_payments[0].keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerows(new_payments)

        total_count, total_amount, payments = get_today_payment_summary()
        table_html = generate_html_table(payments)

        now = datetime.now()
        today_str = now.strftime("%Y.%m.%d")
        now_time_str = now.strftime("%H:%M")

        # ✅ seat 스타일로 통일된 dashboard HTML
        summary_msg = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>앤딩스터디카페 결제 현황</title>
            <style>
                body {{
                    font-family: 'Apple SD Gothic Neo', 'Arial', sans-serif;
                    background: #f4f4f4;
                    margin: 0;
                    padding: 1rem;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .box {{
                    background: white;
                    border-radius: 1rem;
                    padding: 1.5rem;
                    max-width: 600px;
                    width: 100%;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    text-align: center;
                    font-size: 14px;
                }}
                h3 {{
                    margin-bottom: 1rem;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                    margin-top: 1rem;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 6px;
                }}
                th {{
                    background-color: #f0f0f0;
                }}
                .updated {{
                    font-size: 0.85rem;
                    color: #888;
                    margin-top: 1rem;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h3>💳 오늘 결제 현황</h3>
                <p>📅 날짜: {today_str}</p>
                <p>🧾 총 결제: <b>{total_count}건 / {total_amount:,}원</b></p>
                <p>⏰ 실행 시각: {now_time_str}</p>
                <div>{table_html}</div>
            </div>
        </body>
        </html>
        """

        update_dashboard("payment", summary_msg)
        with open("payment_dashboard.html", "w", encoding="utf-8") as f:
            f.write(summary_msg)

        if new_payments:
            plain_summary = f"[오늘 결제] 총 {total_count}건, {total_amount:,}원"
            send_telegram_and_log(plain_summary, broadcast=True)

        send_telegram_and_log(f"{location_tag} ✅ [결제 - 모니터링] 정상 종료되었습니다.")

    except Exception as e:
        send_telegram_and_log(f"[payment_check 오류] {e}")
    finally:
        driver.quit()

import requests
import socket

if __name__ == "__main__":

    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    main_check_payment()