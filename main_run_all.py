import requests
import socket
import contextlib
import threading
from module.dashboard_studyroom import main_check_studyroom
from module.dashboard_payment import main_check_payment
from module.dashboard_seat import main_check_seat
from module.dashboard_monthly import main_monthly_payment


def run_and_log(func, log_path):
    with open(log_path, "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            func()

if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    # 먼저 seat은 단독 실행 (Selenium 안정성 확보용)
    run_and_log(main_check_seat, "/home/mmkkshim/anding_bot/logs/run_s.log")

    # 나머지 3개는 병렬 실행
    threads = [
        threading.Thread(target=run_and_log, args=(main_check_payment, "/home/mmkkshim/anding_bot/logs/run_p.log")),
        threading.Thread(target=run_and_log, args=(main_monthly_payment, "/home/mmkkshim/anding_bot/logs/run_m.log")),
        threading.Thread(target=run_and_log, args=(main_check_studyroom, "/home/mmkkshim/anding_bot/logs/run_r.log")),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()