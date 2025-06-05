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
        checkboxes = tr.select('input[type="checkbox"]')
        name_input = tr.select_one('input[name="product_nm"]')
        time_input = tr.select_one('input[name="time_cnt"]')
        price_input = tr.select_one('input[name="amount"]')

        if len(checkboxes) < 2 or not (name_input and time_input and price_input):
            continue

        use_checkbox, renew_checkbox = checkboxes[:2]
        name = name_input.get("value", "").strip()
        is_active = 'checked' in use_checkbox.attrs
        is_renewable = 'checked' in renew_checkbox.attrs

        log(f"상품 '{name}' - 판매: {is_active}, 연장: {is_renewable}")

        try:
            products.append({
                "name": name,
                "time": int(time_input.get("value", "0").strip()),
                "price": int(price_input.get("value", "0").strip()),
                "active": is_active,
                "renewable": is_renewable,
            })
        except ValueError:
            continue  # Skip rows with invalid numbers

    return products

def get_product_html_from_data(products):
    rows = "\n".join(
        f"<tr><td>{p['name']}</td><td>{p['time']}시간</td><td>{p['price']:,}원</td><td>{'✅' if p['active'] else '❌'}</td><td>{'🔁' if p.get('renewable') else '―'}</td></tr>"
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
                <thead><tr><th>상품명</th><th>시간</th><th>금액</th><th>판매</th><th>연장</th></tr></thead>
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
    html = fetch_product_html()
    products = _get_active_products(html)
    summary = f"현재 사용 중인 시간권 {len(products)}종"
    log(f"✅ {summary}")

    html_rendered = get_product_html_from_data(products)
    html_path = os.path.join(DASHBOARD_PATH, "product_dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_rendered)
    log(f"💾 HTML 저장 완료: {html_path}")
    print(summary)


# If executed directly
if __name__ == "__main__":
    main_check_product()