import requests
import socket
from module.dashboard_studyroom import main_check_studyroom
from module.dashboard_payment import main_check_payment
from module.dashboard_seat import main_check_seat



if __name__ == "__main__":
    ip = requests.get("https://api.ipify.org").text
    print(f"현재 외부 IP 주소: {ip}")
    print(f"📡 Running on hostname: {socket.gethostname()}")

    # # 인증 리스너를 백그라운드에서 실행
    # listener_thread = threading.Thread(target=start_telegram_listener, daemon=True)
    # listener_thread.start()

    
    main_check_payment()
    main_check_seat()
    main_check_studyroom()
        
    # if should_run_studyroom():
    #     main_check_studyroom()