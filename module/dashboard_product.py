

# Logging, environment, and argument setup
import os
import argparse
from datetime import datetime
import pytz
from dotenv import load_dotenv

kst = pytz.timezone("Asia/Seoul")

try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

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


# Internal function to get active products
def _get_active_products():
    all_products = [
        {"name": "1시간", "time": 1, "price": 1000, "active": True},
        {"name": "2시간", "time": 2, "price": 2000, "active": True},
        {"name": "3시간", "time": 3, "price": 3000, "active": True},
        {"name": "4시간", "time": 4, "price": 3500, "active": True},
        {"name": "6시간", "time": 6, "price": 5000, "active": True},
        {"name": "9시간", "time": 9, "price": 7000, "active": True},
        {"name": "12시간", "time": 12, "price": 9000, "active": True},
        {"name": "좌석 상황에 따라 일회이용/연장이 제한될 수 있습니다.", "time": 0, "price": 1, "active": True},
        {"name": "좌석 부족으로 일회이용/연장이 제한 상태(안내문 읽어주세요)", "time": 0, "price": 1, "active": True},
        {"name": "테스트 상품 (비활성)", "time": 99, "price": 99999, "active": False},
    ]
    return [p for p in all_products if p["active"]]


# Returns a brief summary line for the active products.
def summary_line():
    products = _get_active_products()
    return f"현재 사용 중인 시간권 {len(products)}종"


# Returns the full HTML for the product dashboard.
def get_product_html():
    log("활성 상품 수집 시작")
    products = _get_active_products()
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
            <a class="back-link" href='/admin'>⬅️ 대시보드로 돌아가기</a>
        </div>
    </body>
    </html>
    """


# --- Main product dashboard check ---
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