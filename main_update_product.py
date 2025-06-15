import os
import argparse
from datetime import datetime
import pytz
from dotenv import load_dotenv
# --- Selenium login utility imports ---
from module.set import login, create_driver
from selenium.webdriver.common.by import By
import time

kst = pytz.timezone("Asia/Seoul")

try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# --- URL variables ---
BASE_URL = os.getenv("BASE_URL")
PRODUCT_URL = f"{BASE_URL}/product/seatArea"

parser = argparse.ArgumentParser()
parser.add_argument("--manual", action="store_true", help="수동 실행 모드")
parser.add_argument("--hide", action="store_true", help="디버그 메시지 숨김")
args = parser.parse_args()

DEBUG_ENV = os.getenv("DEBUG", "true").lower() == "true"
DEBUG = not args.hide and DEBUG_ENV
print(f"[DEBUG MODE] {'ON' if DEBUG else 'OFF'}")

DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard")

now_kst = datetime.now(kst)
timestamp_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
log_dir = os.path.join(DASHBOARD_PATH, "logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "run_product.log")

def log(msg):
    full_msg = f"{timestamp_str} | {msg}"
    print(full_msg)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")


from module.dashboard_product import update_product_status, run_check_product


def main_check_product():
    log("🌐 상품 페이지 로그인 및 현황 체크 시작")
    driver = create_driver()
    try:
        if login(driver):
            # ✅ 테스트: 판매 ON, 연장 OFF로 변경해봄
            update_product_status(driver, product_name="9시간", sell_enable=True, renew_enable=False)
            # ✅ 상태 확인용 대시보드 갱신
            # run_check_product(driver)
        else:
            log("❌ 상품 페이지 로그인 실패")
    except Exception as e:
        log(f"[ERROR] main_check_product 예외: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main_check_product()