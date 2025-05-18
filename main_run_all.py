import requests
import socket
from dashboard_studyroom import main_check_studyroom
from dashboard_payment import main_check_payment
from dashboard_seat import main_check_seat

def should_run_studyroom():
    import os
    from datetime import datetime
    import pytz
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    today_str = now.strftime("%Y-%m-%d")
    cache_file = "/home/mmkkshim/anding_bot/log/studyroom_last_run.txt"

    if now.hour == 7:
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                last_run = f.read().strip()
                if last_run == today_str:
                    return False  # already ran today
        with open(cache_file, "w") as f:
            f.write(today_str)
        return True
    return False

if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    # # 인증 리스너를 백그라운드에서 실행
    # listener_thread = threading.Thread(target=start_telegram_listener, daemon=True)
    # listener_thread.start()

    main_check_seat()
    main_check_payment()
    main_check_studyroom()
        
    # if should_run_studyroom():
    #     main_check_studyroom()