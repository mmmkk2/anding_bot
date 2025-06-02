import requests
import socket
import contextlib
from module.dashboard_studyroom import main_check_studyroom
from module.dashboard_payment import main_check_payment
from module.dashboard_seat import main_check_seat
from module.dashboard_monthly import main_monthly_payment


if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    with open("logs/run_s.log", "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            main_check_seat()

    with open("logs/run_p.log", "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            main_check_payment()

    with open("logs/run_m.log", "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            main_monthly_payment()

    with open("logs/run_r.log", "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            main_check_studyroom()