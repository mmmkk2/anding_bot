import requests
import socket
import contextlib
import threading
from module.dashboard_studyroom import main_check_studyroom
from module.dashboard_payment import main_check_payment
from module.dashboard_seat import main_check_seat
from module.dashboard_monthly import main_monthly_payment
from module.dashboard_product import main_check_product



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

    # 먼저 seat은 단독 실행 (Selenium 안정성 확보용)
    print("▶️ 좌석 확인 시작")
    run_and_log(main_check_seat, "/home/mmkkshim/anding_bot/logs/run_s.log", label="좌석 확인")

    print("▶️ 상품 확인 시작")
    run_and_log(main_check_product, "/home/mmkkshim/anding_bot/logs/run_product.log", label="상품 확인")

    print("▶️ 결제 확인 시작")
    run_and_log(main_check_payment, "/home/mmkkshim/anding_bot/logs/run_p.log", label="결제 확인")

    print("▶️ 월별 매출 확인 시작")
    run_and_log(main_monthly_payment, "/home/mmkkshim/anding_bot/logs/run_m.log", label="월별 매출")

    print("▶️ 스터디룸 확인 시작")
    run_and_log(main_check_studyroom, "/home/mmkkshim/anding_bot/logs/run_r.log", label="스터디룸 확인")