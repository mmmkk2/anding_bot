import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/mmkkshim/anding_bot/.env")

LOGIN_ID = "anding_bot"
LOGIN_PWD = "871104tla#"

DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/")

BASE_URL = "https://mmkkshim.pythonanywhere.com"

today_str = datetime.now().strftime("%Y-%m-%d")
screenshot_dir = os.path.join(DASHBOARD_PATH, "screenshots", today_str)
os.makedirs(screenshot_dir, exist_ok=True)

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    driver = webdriver.Chrome(options=options)
    return driver

def capture_dashboard(name, path, driver):
    url = f"{BASE_URL}/{path}" if path else BASE_URL
    driver.get(url)

    if "login" in driver.current_url:
        print("[INFO] 로그인 필요 - 로그인 시도 중")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        driver.find_element(By.NAME, "username").send_keys(LOGIN_ID)
        driver.find_element(By.NAME, "password").send_keys(LOGIN_PWD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(1)
    screenshot_path = os.path.join(screenshot_dir, f"{name}.png")
    driver.save_screenshot(screenshot_path)
    print(f"[완료] 캡처됨: {screenshot_path}")

def main():
    driver = create_driver()
    try:
        capture_dashboard("seat_dashboard", "seat", driver)
        capture_dashboard("payment_dashboard", "payment", driver)
        capture_dashboard("studyroom_dashboard", "studyroom", driver)
        capture_dashboard("main_dashboard", "", driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

