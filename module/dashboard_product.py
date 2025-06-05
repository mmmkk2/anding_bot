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


# Internal function to get active products (dynamically from HTML content)
from bs4 import BeautifulSoup
def _get_active_products(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        log(f"[ERROR] 상품 HTML 파싱 실패: {e}")
        return []

    product_rows = soup.select("tbody > tr")
    products = []

    for tr in product_rows:
        checkbox = tr.select_one('input[name="use_yn"]')
        name = tr.select_one('input[name="product_nm"]').get("value", "").strip()
        is_checked = checkbox and 'checked' in checkbox.attrs
        log(f"상품 '{name}' - 체크 상태: {is_checked}")
        if is_checked:
            time_val = tr.select_one('input[name="time_cnt"]').get("value", "0").strip()
            price_val = tr.select_one('input[name="amount"]').get("value", "0").strip()
            try:
                products.append({
                    "name": name,
                    "time": int(time_val),
                    "price": int(price_val),
                    "active": True,
                })
            except ValueError:
                continue  # Skip rows with invalid numbers

    return products


# Returns a brief summary line for the active products.
def summary_line():
    html = fetch_product_html()
    products = _get_active_products(html)
    return f"현재 사용 중인 시간권 {len(products)}종"


# Returns the full HTML for the product dashboard.
def get_product_html():
    log("활성 상품 수집 시작")
    html = fetch_product_html()
    products = _get_active_products(html)
    log(f"총 상품 수: {len(products)}")
    rows = "\n".join(
        f"<tr><td>{p['name']}</td><td>{p['time']}시간</td><td>{p['price']:,}원</td></tr>"
        for p in products
    )
    return f"""
    <!DOCTYPE html>
    <html lang='ko'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>상품 현황</title>
        <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_app.css">
    </head>
    <body>
        <div class="log-container">
            <div class="log-title">🛒 활성화된 시간권 상품</div>
            <table>
                <thead><tr><th>상품명</th><th>시간</th><th>금액</th></tr></thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """


# --- Main product dashboard check ---
def fetch_product_html():
    log("🌐 상품 페이지 로그인 및 HTML 가져오기 시도")
    driver = create_driver()
    html = ""
    try:
        if login(driver):
            driver.get(PRODUCT_URL)
            time.sleep(2)
            personal_tab = driver.find_element(By.XPATH, "//a[contains(text(), '개인석')]")
            personal_tab.click()
            time.sleep(2)
            html = driver.page_source
            log("✅ 개인석 상품 HTML 가져오기 완료")
        else:
            log("❌ 상품 페이지 로그인 실패")
    except Exception as e:
        log(f"[ERROR] 상품 HTML 수집 중 오류: {e}")
    finally:
        driver.quit()
    return html


def main_check_product():
    log("🔍 [상품] 활성 상품 현황 수집 시작")
    summary = summary_line()
    log(f"✅ {summary}")
    html = get_product_html()
    html_path = os.path.join(DASHBOARD_PATH, "product_dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"💾 HTML 저장 완료: {html_path}")
    print(summary)


# If executed directly
if __name__ == "__main__":
    main_check_product()