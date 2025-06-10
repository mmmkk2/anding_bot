import requests
import socket
import contextlib
import threading
from datetime import datetime
from module.dashboard_studyroom import main_check_studyroom
from module.dashboard_payment import main_check_payment
from module.dashboard_seat import main_check_seat
from module.dashboard_monthly import main_monthly_payment
from module.dashboard_product import main_check_product
import os



def run_and_log(func, log_path, label=None):
    with open(log_path, "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            print(f"▶️ {label} 시작", flush=True)
            try:
                func()
                print(f"✅ {label} 완료", flush=True)
            except Exception as e:
                print(f"❌ {label} 실패: {e}", flush=True)

if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    # === DANGER_THRESHOLD 이하일 때만 좌석 + 상품 실행 ===
    seat_csv_path = "/home/mmkkshim/anding_bot/dashboard_log/seat_history.csv"
    try:
        with open(seat_csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_line = lines[-1] if lines else None
            last_count = int(last_line.strip().split(",")[1]) if last_line else 99
    except Exception as e:
        print(f"[경고] 좌석 이력 CSV 로딩 실패: {e}")
        last_count = 99

    try:
        from dotenv import load_dotenv
        load_dotenv("/home/mmkkshim/anding_bot/.env")
        # threshold = int(os.getenv("DANGER_THRESHOLD", "5"))
        threshold = int(os.getenv("WARNING_THRESHOLD", "8"))
    except Exception as e:
        print(f"[경고] DANGER_THRESHOLD 로딩 실패: {e}")
        threshold = 5

    # for test
    # danger_threshold = 8
    total_free = 28
    last_remaining_free = total_free - last_count

    if last_remaining_free <= threshold:
        # 먼저 seat은 단독 실행 (Selenium 안정성 확보용)
        print("▶️ 좌석 확인 시작")
        run_and_log(main_check_seat, "/home/mmkkshim/anding_bot/logs/run_s.log", label="좌석 확인")

        print("▶️ 상품 확인 시작")
        run_and_log(main_check_product, "/home/mmkkshim/anding_bot/logs/run_product.log", label="상품 확인")

        print("▶️ 결제 확인 시작")
        run_and_log(main_check_payment, "/home/mmkkshim/anding_bot/logs/run_p.log", label="결제 확인")
    else:
        print(f"[스킵] 좌석 수 {last_remaining_free} > THRESHOLD {threshold} → 좌석 및 상품 확인 생략")
