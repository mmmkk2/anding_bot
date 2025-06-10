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



def run_and_log(func, log_path, label=None):
    with open(log_path, "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            print(f"▶️ {label} 시작", flush=True)
            try:
                func()
                print(f"✅ {label} 완료", flush=True)
            except Exception as e:
                print(f"❌ {label} 실패: {e}", flush=True)

import pytz

kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)

if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    
    # print("▶️ 좌석 확인 시작")
    # run_and_log(main_check_seat, "/home/mmkkshim/anding_bot/logs/run_s.log", label="좌석 확인")

    # print("▶️ 상품 확인 시작")
    # run_and_log(main_check_product, "/home/mmkkshim/anding_bot/logs/run_product.log", label="상품 확인")

    # run_and_log(main_check_payment, "/home/mmkkshim/anding_bot/logs/run_p.log", label="결제 확인")

    now_kst = datetime.now(kst)

    now_kst_hour = (now_kst.hour)
    now_kst_min = (now_kst.min)
    
    # print(now_kst_hour)
    print(now_kst_min)

    # if now_kst_hour < 1 and now_kst_min <=10:
    #     print("⏸ 결제 확인은 KST 00~0시 10분에는 실행되지 않습니다.")
    # else:
    #     print("▶️ 결제 확인 시작")
    #     run_and_log(main_check_payment, "/home/mmkkshim/anding_bot/logs/run_p.log", label="결제 확인")
    
    # print("▶️ 월별 매출 확인 시작")
    # run_and_log(main_monthly_payment, "/home/mmkkshim/anding_bot/logs/run_m.log", label="월별 매출")

    # print("▶️ 스터디룸 확인 시작")
    # run_and_log(main_check_studyroom, "/home/mmkkshim/anding_bot/logs/run_r.log", label="스터디룸 확인")