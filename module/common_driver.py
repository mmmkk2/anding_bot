import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# 환경변수 로드
try:
    load_dotenv(".env")
except:
    pass

# 설정값
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PWD = os.getenv("LOGIN_PWD")
BASE_URL = "https://partner.cobopay.co.kr"

import sys
HEADLESS = "--no-headless" not in sys.argv

# === 공통 텔레그램 전송 ===
def send_telegram_and_log(msg):
    print(msg)
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")

# === 드라이버 생성 ===
def create_driver():

    options = Options()
    options.binary_location = "/home/mmkkshim/bin/chrome"
    if HEADLESS:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--incognito")

    driver_path = "/home/mmkkshim/bin/chromedriver"
    return webdriver.Chrome(executable_path=driver_path, options=options)
    # return webdriver.Chrome(options=options)

# === 로그인 공통 ===
def login(driver):
    print("로그인 시도 중...")
    driver.get(BASE_URL)
    time.sleep(2)
    try:
        driver.find_element(By.ID, "account_id").send_keys(LOGIN_ID)
        driver.find_element(By.ID, "account_pwd").send_keys(LOGIN_PWD)
        driver.find_element(By.CLASS_NAME, "btn_login").click()
        time.sleep(3)
    except Exception as e:
        send_telegram_and_log(f"[로그인 실패] ID/PWD 입력 중 오류 발생: {e}")
        return False

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "swal2-html-container"))
        )
        alert_text = driver.find_element(By.CLASS_NAME, "swal2-html-container").text
        if "휴대폰 인증번호" in alert_text:
            send_telegram_and_log("🔒 인증번호 입력이 필요합니다. auth_code.txt에 입력해주세요.")
            driver.find_element(By.CLASS_NAME, "swal2-confirm").click()

            for _ in range(60):
                try:
                    with open("auth_code.txt", "r") as f:
                        auth_code = f.read().strip()
                    if auth_code and auth_code.isdigit():
                        driver.find_element(By.ID, "auth_no").send_keys(auth_code)
                        driver.find_element(By.CLASS_NAME, "btn-primary").click()
                        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
                        send_telegram_and_log("✅ 인증번호 자동 입력 완료")
                        return True
                except:
                    pass
                time.sleep(2)
            send_telegram_and_log("⏰ 인증번호 입력 시간 초과. 수동 인증이 필요합니다.")
            return False
    except:
        print("인증 없이 로그인 완료")
        return True

    if not driver.find_elements(By.ID, "auth_no"):
        send_telegram_and_log("인증번호 입력 화면이 닫히거나 종료되었습니다.")
        return False