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
        return {"once": [], "hour": [], "period": []}

    tab_products = {"once": [], "hour": [], "period": []}
    for tab_id, key in zip(["tab_1", "tab_2", "tab_3"], ["once", "hour", "period"]):
        tab = soup.select_one(f"div#{tab_id}")
        if tab:
            for tr in tab.select("tbody > tr"):
                checkboxes = tr.select('input[type="checkbox"]')
                name_input = tr.select_one('input[name="product_nm"]')
                time_input = tr.select_one('input[name="time_cnt"]')
                price_input = tr.select_one('input[name="amount"]')

                if len(checkboxes) < 2 or not (name_input and time_input and price_input):
                    continue

                name = name_input.get("value", "").strip()
                time = int(time_input.get("value", "0").strip())
                price = int(price_input.get("value", "0").strip())

                if "9시간" in name or "12시간" in name:
                    continue
                # 안내문 pass
                if time==0:
                    continue

                
                # Optionally filter out unwanted products here if needed
                use_checkbox, renew_checkbox = checkboxes[:2]
                is_active = 'checked' in use_checkbox.attrs
                is_renewable = 'checked' in renew_checkbox.attrs

                try:
                    tab_products[key].append({
                        "name": name,
                        "time": time,
                        "price": price,
                        "active": is_active,
                        "renewable": is_renewable,
                    })
                except ValueError:
                    continue
    return tab_products

def render_table(products):
    return "\n".join(
        f"""
<tr>
    <td>{p['name']}</td>
    <td>{p['time']}시간</td>
    <td>{p['price']:,}원</td>
    <td><input type="checkbox" {'checked' if p['active'] else ''} disabled></td>
    <td><input type="checkbox" {'checked' if p.get('renewable') else ''} disabled></td>
</tr>
        """.strip()
        for p in products
    )


update_mode = "M" if args.manual else "B"
now_str = f"{datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')} ({update_mode})"

def get_product_html_from_data(products_by_tab):
    return f"""

    
<!DOCTYPE html>
<html lang='ko'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>상품 현황</title>
    <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_product.css">
</head>
<body>
<div class="box">
    <div class="tab-wrapper">
        <button class="tab-btn active" data-tab="once">1회이용권</button>
        <button class="tab-btn" data-tab="hour">시간이용권</button>
        <button class="tab-btn" data-tab="period">기간이용권</button>
    </div>
    <div style="margin-bottom: 0.5rem;"></div>
    <div id="once" class="tab-content active">
        <div class="table-box">
            <table class="sortable" data-sortable><thead><tr><th>상품명</th><th>시간</th><th>금액</th><th>판매</th><th>연장</th></tr></thead><tbody>
                {render_table(products_by_tab["once"])}
            </tbody></table>
        </div>
    </div>
    <div id="hour" class="tab-content">
        <div class="table-box">
            <table class="sortable" data-sortable><thead><tr><th>상품명</th><th>시간</th><th>금액</th><th>판매</th><th>연장</th></tr></thead><tbody>
                {render_table(products_by_tab["hour"])}
            </tbody></table>
        </div>
    </div>
    <div id="period" class="tab-content">
        <div class="table-box">
            <table class="sortable" data-sortable><thead><tr><th>상품명</th><th>시간</th><th>금액</th><th>판매</th><th>연장</th></tr></thead><tbody>
                {render_table(products_by_tab["period"])}
            </tbody></table>
        </div>
    </div>
</div>
<div class="updated">Updated {now_str}</div>

<script>
document.addEventListener("DOMContentLoaded", function () {{
    var tabBtns = document.querySelectorAll('.tab-btn');
    var tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            tabBtns.forEach(function(b) {{
                b.classList.remove('active');
            }});
            tabContents.forEach(function(tc) {{
                tc.style.display = 'none';
                tc.classList.remove('active');
            }});

            btn.classList.add('active');
            var tabId = btn.getAttribute('data-tab');
            var tabElement = document.getElementById(tabId);
            if (tabElement) {{
                tabElement.style.display = 'block';
                tabElement.classList.add('active');
            }}
        }});
    }});

    // Initialize visibility
    tabContents.forEach(function(tc) {{
        if (!tc.classList.contains('active')) {{
            tc.style.display = 'none';
        }} else {{
            tc.style.display = 'block';
        }}
    }});
}});
</script>
</body>
</html>
"""


# --- Main product dashboard check ---
def run_check_product(driver):
    log("🔍 [상품] 활성 상품 현황 수집 시작")
    driver.get(PRODUCT_URL)
    time.sleep(2)
    personal_tab = driver.find_element(By.XPATH, "//a[contains(text(), '개인석')]")
    personal_tab.click()
    time.sleep(2)
    html = driver.page_source
    products_by_tab = _get_active_products(html)
    total_count = sum(len(v) for v in products_by_tab.values())
    summary = f"현재 시간권 상품 총 {total_count}종"
    log(f"✅ {summary}")

    html_rendered = get_product_html_from_data(products_by_tab)
    html_path = os.path.join(DASHBOARD_PATH, "product_dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_rendered)
    log(f"💾 HTML 저장 완료: {html_path}")
    print(summary)
    return html  # return the HTML in case caller wants it


def fetch_product_html():
    log("🌐 상품 페이지 로그인 및 HTML 가져오기 시도")
    driver = create_driver()
    html = ""
    try:
        if login(driver):
            html = run_check_product(driver)
            log("✅ 개인석 상품 HTML 가져오기 완료")
        else:
            log("❌ 상품 페이지 로그인 실패")
    except Exception as e:
        log(f"[ERROR] 상품 HTML 수집 중 오류: {e}")
    finally:
        driver.quit()
    return html





# --- 상품 판매/연장 상태 변경 함수 ---
def update_product_status(driver, product_name, sell_enable=True, renew_enable=True):
    """
    상품 판매 및 연장 상태를 변경하고 저장 버튼 클릭.
    모든 탭을 순회하여 _get_active_products와 동일한 방식으로 탐색.
    """
    try:
        driver.get(PRODUCT_URL)
        time.sleep(2)
        personal_tab = driver.find_element(By.XPATH, "//a[contains(text(), '개인석')]")
        personal_tab.click()
        time.sleep(2)

        found = False
        for tab_id in ["tab_1", "tab_2", "tab_3"]:
            try:
                tab = driver.find_element(By.ID, tab_id)
            except Exception:
                continue
            rows = tab.find_elements(By.CSS_SELECTOR, "tbody > tr")
            for row in rows:
                try:
                    name_input = row.find_element(By.NAME, "product_nm")
                except Exception:
                    continue
                if product_name in name_input.get_attribute("value").strip():
                    checkboxes = row.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    if len(checkboxes) >= 2:
                        use_checkbox = checkboxes[0]
                        renew_checkbox = checkboxes[1]
                        if use_checkbox.is_selected() != sell_enable:
                            use_checkbox.click()
                        if renew_checkbox.is_selected() != renew_enable:
                            renew_checkbox.click()
                        save_btn = driver.find_element(By.ID, "btn_save")
                        save_btn.click()
                        found = True
                        break
            if found:
                break
        if not found:
            log(f"[WARN] 상품명 '{product_name}' 을(를) 찾을 수 없음.")
    except Exception as e:
        log(f"[ERROR] 상품 상태 변경 중 오류: {e}")



def main_check_product():
    log("🌐 상품 페이지 로그인 및 현황 체크 시작")
    driver = create_driver()
    try:
        if login(driver):
            run_check_product(driver)
        else:
            log("❌ 상품 페이지 로그인 실패")
    except Exception as e:
        log(f"[ERROR] main_check_product 예외: {e}")
    finally:
        driver.quit()