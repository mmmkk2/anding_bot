import os
import time
import requests
import socket
import platform
import tempfile
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# === 환경변수 로드 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except Exception as e:
    print(f"[.env 로드 실패] {e}")

# === 필수 환경변수 ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PWD = os.getenv("LOGIN_PWD")
EMERGENCY_CHAT_ID = os.getenv("EMERGENCY_CHAT_ID")


import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def send_telegram_and_log(msg, broadcast=False):
    print(msg)

    chat_id = os.getenv("CHAT_ID")

    # If broadcast is requested, also send to EMERGENCY_CHAT_ID
    if broadcast:
        chat_id = os.getenv("EMERGENCY_CHAT_ID")

    if not chat_id:
        print("[텔레그램 오류] CHAT_ID 설정이 없습니다.")
        return

    try:
        # Always send to the main chat
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg}
        )

    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")


auth_code = None  # Event-driven 인증번호 저장 변수

auth_path="/home/mmkkshim/anding_bot/auth_code.txt"

# === 로그인 함수 ===
def login(driver):

    BASE_URL = "https://partner.cobopay.co.kr"

    if not LOGIN_ID or not LOGIN_PWD:
        send_telegram_and_log("[로그인 실패] ID/PWD 누락")
        return False

    print("로그인 시도 중...")
    driver.get(BASE_URL)

    print("현재 페이지 타이틀:", driver.title)
    print("현재 URL:", driver.current_url)

    # 로그인 페이지가 로드될 때까지 대기
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "account_id"))
    )


    try:
        driver.find_element(By.ID, "account_id").send_keys(LOGIN_ID)
        driver.find_element(By.ID, "account_pwd").send_keys(LOGIN_PWD)
        driver.find_element(By.CLASS_NAME, "btn_login").click()
        time.sleep(3)
    except Exception as e:
        send_telegram_and_log(f"[로그인 실패] ID/PWD 입력 오류: {e}")
        return False

    try:
        # 인증 요청 알림 대기
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "swal2-html-container"))
        )
        alert_text = driver.find_element(By.CLASS_NAME, "swal2-html-container").text


        if "휴대폰 인증번호" in alert_text:
            print("인증번호 입력 대기 중...")
            send_telegram_and_log(f"📲 인증번호 요청됨. \n👤 로그인 ID: {LOGIN_ID}\n텔레그램으로 인증번호 입력 시 자동 처리됩니다.", broadcast=True)

            try:
                driver.find_element(By.CLASS_NAME, "swal2-confirm").click()
            except Exception as e:
                send_telegram_and_log(f"❌ 확인 버튼 클릭 실패: {e}")
                print(f"❌ swal2-confirm 클릭 실패: {e}")
                return False

            print("📲 인증번호 입력 대기 중... (auth_code.txt가 생길 때까지 무한 대기)")

            # 인증번호 수신 대기
            # ✅ 인증번호 수신까지 무한 대기
            while True:
                if os.path.exists(auth_path):
                    with open(auth_path, "r") as f:
                        code = f.read().strip()
                    if code.isdigit() and len(code) == 4:
                        print(f"📥 인증번호 수신됨: {code}")
                        try:
                            driver.find_element(By.ID, "auth_no").clear()
                            driver.find_element(By.ID, "auth_no").send_keys(code)
                            driver.find_element(By.CSS_SELECTOR, "button.btn.btn_login").click()

                            # driver.find_element(By.CLASS_NAME, "btn-primary").click()
                            # driver.find_element(By.CSS_SELECTOR, 'button[type=\"submit\"]').click()


                        except Exception as e:
                            send_telegram_and_log(f"❌ 인증번호 입력 실패: {e}", broadcast=True)
                            return False
                        os.remove(auth_path)

                        # 실패 메시지 감지 여부
                        try:
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "swal2-html-container"))
                            )
                            error_text = driver.find_element(By.CLASS_NAME, "swal2-html-container").text
                            if "잘못" in error_text or "인증번호" in error_text:
                                send_telegram_and_log(f"❌ 인증 실패: {error_text}")
                                return False
                        except:
                            pass

                        # 로그인 성공 판별
                        if driver.find_elements(By.ID, "auth_no"):
                            send_telegram_and_log("❌ 인증번호 입력 후 여전히 입력창이 남아 있음", broadcast=True)
                            return False

                        send_telegram_and_log("✅ 인증번호 자동 입력 완료 및 로그인 성공")
                        return True
                time.sleep(2)

    except Exception:
        try:
            # Dashboard URL로 직접 이동
            driver.get("https://partner.cobopay.co.kr/dashboard")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            current_url = driver.current_url
            if "/dashboard" in current_url:
                send_telegram_and_log("✅ 인증 없이 로그인 성공 (Dashboard 접근 확인)")
                return True
            else:
                send_telegram_and_log(f"❌ 로그인 실패 - 이동한 URL 확인 필요: {current_url}", broadcast=True)
                return False
        except Exception as e:
            send_telegram_and_log(f"❌ 로그인 실패 - Dashboard 접근 불가: {e}", broadcast=True)
            return False

    if not driver.find_elements(By.ID, "auth_no"):
        send_telegram_and_log("인증 입력 화면이 닫혔습니다. 수동 확인 필요", broadcast=True)
        return False


# === 드라이버 생성 ===
from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.ChromeOptions import Options
from selenium import webdriver



import os
import uuid
import tempfile


# from selenium import webdriver

# chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--window-size=1920,1080")

# driver = webdriver.Chrome(options=chrome_options)

# try:
#     driver.get("https://www.google.com")
#     print("Page title was '{}'".format(driver.title))
# finally:
#     driver.quit()


def create_driver():
    chrome_options = webdriver.ChromeOptions()

    # 1. Chromium 실행 파일 위치 지정 (권한 있는 사용자 디렉토리로 복사한 바이너리)
    # chrome_options.binary_location = "/home/mmkkshim/bin/chromium_custom"

    # 2. Headless 모드 설정
    chrome_options.add_argument("--headless")  # 안정적인 headless 모드

    # 3. 필수 안정성 옵션
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # 4. 사용자 데이터 디렉토리를 임시로 생성
    # user_data_dir = tempfile.mkdtemp()
    # chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    # 5. 명시적으로 chromedriver 위치 지정
    service = Service("/usr/bin/chromedriver")

    # 6. 드라이버 생성
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# === 실행 위치 판별 ===
def find_location():
    try:
        hostname = socket.gethostname()
        if hostname == 'Mikyungs-MacBook-Air.local':
            _location = "(Mac)"
        else:
            _location = "(Server)"
    except Exception:
        _location = "(unknown)"

    return _location



def send_broadcast_message(msg):
    """진짜 중요한 알림만 텔레그램으로 보내기"""
    print(f"[Broadcast] {msg}")
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")

from datetime import datetime

def update_dashboard(category, msg, append=False):
    os.makedirs("dashboard_log", exist_ok=True)
    file_path = f"dashboard_log/{category}_dashboard.txt"
    mode = "a" if append else "w"
    with open(file_path, mode, encoding="utf-8") as f:
        f.write(msg + "\n\n")

def send_broadcast_and_update(msg, broadcast=True, category="seat"):
    send_telegram_and_log(msg, broadcast=broadcast)
    update_dashboard(category, msg)


import os
import pickle

FLAGS_FILE = "log/broadcast_flags.pkl"

def load_flags():
    if os.path.exists(FLAGS_FILE):
        with open(FLAGS_FILE, "rb") as f:
            data = pickle.load(f)
    else:
        data = {"date": "", "warn_6": False, "warn_4": False, "recovery": False, "fixed_missing": False}
    return data

def save_flags(flags):
    os.makedirs("log", exist_ok=True)
    with open(FLAGS_FILE, "wb") as f:
        pickle.dump(flags, f)


