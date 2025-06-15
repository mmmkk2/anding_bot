import sys
from module.set import login, find_location, create_driver, send_broadcast_and_update, send_telegram_and_log

import os
import time
import pickle
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from datetime import datetime
import argparse
import pytz

kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)
today_str = now.strftime("%Y.%m.%d")


# === 설정 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

# Add manual mode switch after loading .env
# Default: DEBUG is True unless --manual is passed
parser = argparse.ArgumentParser()
parser.add_argument("--manual", action="store_true", help="수동 실행 모드 (디버깅 활성화)")
args = parser.parse_args()
DEBUG = args.manual or os.getenv("DEBUG", "true").lower() == "true"

print(args.manual)

# Dashboard path for logs and HTML
DEBUG_PATH = os.getenv("DEBUG_PATH")
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH")

PAYMENT_CACHE_FILE = os.getenv("COOKIE_FILE")


BASE_URL = os.getenv("BASE_URL")
PAYMENT_URL = f"{BASE_URL}/pay/payHist"




# === 월별 매출 캘린더 파싱 함수 ===
def fetch_monthly_sales_from_calendar(driver):
    """
    월별 매출 캘린더에서 이전달 매출을 파싱하여 반환합니다.
    Returns: [{"date": "2025.05.01", "amount": 150000}, ...]
    """
    CALENDAR_URL = "https://partner.cobopay.co.kr/pay/payHistCalendar"
    if DEBUG:
        print(f"[DEBUG] 매출 캘린더 페이지 이동: {CALENDAR_URL}")
    driver.get(CALENDAR_URL)
    time.sleep(1.5)

    # "이전달" 버튼 클릭
    try:
        prev_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fc-prev-button"))
        )
        if DEBUG:
            print("[DEBUG] '이전달' 버튼 클릭 시도")
        prev_btn.click()
        time.sleep(1.2)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] '이전달' 버튼 클릭 실패: {e}")
        raise

    # 캘린더 이벤트(매출) 로딩 대기
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fc-event-title"))
        )
        if DEBUG:
            print("[DEBUG] 캘린더 이벤트 로딩 완료")
    except TimeoutException:
        if DEBUG:
            print("[DEBUG] 캘린더 이벤트 로딩 실패 (Timeout)")
        return []

    # 각 날짜 셀(td[data-date])에서 매출 이벤트 수집
    sales = []
    day_cells = driver.find_elements(By.CSS_SELECTOR, "td.fc-daygrid-day[data-date]")
    for cell in day_cells:
        date_str = cell.get_attribute("data-date")  # e.g., "2025-05-01"
        event_titles = cell.find_elements(By.CSS_SELECTOR, "div.fc-event-title")
        for event in event_titles:
            text = event.text.strip()
            if "원" in text:
                try:
                    amount = int(text.replace(",", "").replace("원", "").strip())
                    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y.%m.%d")
                    sales.append({"date": formatted_date, "amount": amount})
                    if DEBUG:
                        print(f"[DEBUG] 캘린더 매출 파싱: {formatted_date} / {amount}")
                except Exception as e:
                    if DEBUG:
                        print(f"[DEBUG] 매출 파싱 실패: {text} ({e})")

    # === 현재달 매출 수집 ===
    try:
        next_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fc-next-button"))
        )
        if DEBUG:
            print("[DEBUG] '다음달' 버튼 클릭 시도")
        next_btn.click()
        time.sleep(1.2)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] '다음달' 버튼 클릭 실패: {e}")
        raise

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fc-event-title"))
        )
        if DEBUG:
            print("[DEBUG] 현재달 캘린더 이벤트 로딩 완료")
    except TimeoutException:
        if DEBUG:
            print("[DEBUG] 현재달 이벤트 로딩 실패 (Timeout)")
        return sales

    # 현재달 매출 수집
    current_sales = []
    day_cells = driver.find_elements(By.CSS_SELECTOR, "td.fc-daygrid-day[data-date]")
    for cell in day_cells:
        date_str = cell.get_attribute("data-date")  # e.g., "2025-06-01"
        event_titles = cell.find_elements(By.CSS_SELECTOR, "div.fc-event-title")
        for event in event_titles:
            text = event.text.strip()
            if "원" in text:
                try:
                    amount = int(text.replace(",", "").replace("원", "").strip())
                    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y.%m.%d")
                    current_sales.append({"date": formatted_date, "amount": amount})
                    if DEBUG:
                        print(f"[DEBUG] 현재달 매출 파싱: {formatted_date} / {amount}")
                except Exception as e:
                    if DEBUG:
                        print(f"[DEBUG] 현재달 매출 파싱 실패: {text} ({e})")

    # 병합
    sales += current_sales

    if sales:
        import pandas as pd
        import json
        df = pd.DataFrame(sales)
        df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d")
        # Filter only previous month
        prev_month = (now.replace(day=1) - pd.Timedelta(days=1)).month
        df["month"] = df["date"].dt.month
        df_prev = df[df["month"] == prev_month].sort_values("date").drop(columns=["month"])
        df_prev["cumsum"] = df_prev["amount"].cumsum()

        # Ensure date labels are always two digits (e.g., '01', '02d', ..., '31')
        dates = df_prev["date"].dt.strftime("%d").apply(lambda x: f"{int(x):02d}").tolist()
        cumsums = df_prev["cumsum"].tolist()
        # Insert "00" and 0 at the start of both lists
        dates.insert(0, "00")
        cumsums.insert(0, 0)

        # Prepare current month sales for comparison
        current_month = now.month
        df_current = pd.DataFrame(sales)
        df_current["date"] = pd.to_datetime(df_current["date"], format="%Y.%m.%d")
        df_current["month"] = df_current["date"].dt.month
        df_current = df_current[df_current["month"] == current_month]
        df_current = df_current.sort_values("date")
        df_current = df_current.drop(columns=["month"])
        # Inserted: handle empty df_current before calculating cumsum
        # df_current["cumsum"] = df_current["amount"].cumsum()

        df_current["cumsum"] = df_current["amount"].cumsum()

        # Inserted: calculate prev_month, curr_month, summary_amount_prev, summary_amount_curr
        prev_month = df_prev["date"].dt.month.iloc[0] if not df_prev.empty else now.month - 1
        curr_month = df_current["date"].dt.month.iloc[0] if not df_current.empty else now.month
        summary_amount_prev = df_prev["amount"].sum()
        summary_amount_curr = df_current["amount"].sum()

        print(df_current["date"])

        # === 일평균 및 예측 매출 계산 ===
        today_day_int = len(df_current["date"])
        if today_day_int > 0:
            daily_avg = summary_amount_curr // today_day_int
            days_in_month = now.replace(month=now.month % 12 + 1, day=1) - pd.Timedelta(days=1)
            days_in_month = days_in_month.day
            predicted_amount = daily_avg * days_in_month
        else:
            daily_avg = 0
            predicted_amount = 0
        if DEBUG:
            print(f"[DEBUG] 일평균 매출: {daily_avg:,}원")
            print(f"[DEBUG] 예측 매출: {predicted_amount:,}원")

        
        # Align current month cumulative sales to dates (labels) - dynamic max day for both months
        dates_current = df_current["date"].dt.strftime("%d").apply(lambda x: f"{int(x):02d}").tolist()
        cumsum_map_current = dict(zip(dates_current, df_current["cumsum"].tolist()))
        # Determine max day between previous and current month
        max_day = 31

        dates = [f"{d:02d}" for d in range(1, max_day + 1)]
        dates.insert(0, "00")

        # Rebuild cumsums_current with matching length
        cumsums_current = [0] + [cumsum_map_current.get(d, None) for d in dates[1:]]
        dates_current = dates

        update_mode = "M" if args.manual else "B"
        now_str = f"{datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')} ({update_mode})"
        if DEBUG:
            print(f"[DEBUG] now_str: {now_str}")
        print(cumsums_current)
        print(dates)

        chart_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8" />
            <title>{now.year}년 {now.month}월 매출</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_monthly.css">
        </head>
        <body>
            <div class="box">
                <canvas id="monthlyChart" style="max-width: 100%; height: auto; aspect-ratio: 16 / 9;"></canvas>
                <script>
                    // Prepare data for Chart.js: set first point to null, and pointRadius 0 for first.
                    const cumsumsPrev = [null, ...{json.dumps(cumsums[1:])}];
                    const cumsumsCur = [null, ...{json.dumps(cumsums_current[1:])}];
                    const ctx = document.getElementById('monthlyChart').getContext('2d');
                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(dates)},
                            datasets: [
                                {{
                                    label: '이번달 매출 (원)',
                                    data: cumsumsCur,
                                    borderColor: 'rgba(255, 99, 132, 1)',
                                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                    fill: true,
                                    borderWidth: 2,
                                    tension: 0.1,
                                    pointRadius: function(context) {{
                                        return context.dataIndex === 0 ? 0 : 2;
                                    }},
                                    spanGaps: false
                                }},
                                {{
                                    label: '이전달 매출 (원)',
                                    data: cumsumsPrev,
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                    fill: true,
                                    borderWidth: 2,
                                    tension: 0.1,
                                    pointRadius: function(context) {{
                                        return context.dataIndex === 0 ? 0 : 2;
                                    }},
                                    spanGaps: false
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            scales: {{
                                y: {{
                                    beginAtZero: false,
                                    ticks: {{
                                        callback: function(value) {{
                                            if (window.innerWidth <= 480) {{
                                                return (value / 1000000).toFixed(0) + '백만원';
                                            }} else {{
                                                return value.toLocaleString() + '원';
                                            }}
                                        }}
                                    }}
                                }}
                            }},
                            plugins: {{
                                tooltip: {{
                                    usePointStyle: true,
                                    displayColors: false,
                                    callbacks: {{
                                        label: function(context) {{
                                            const daily = context.raw - (context.dataset.data[context.dataIndex - 1] || 0);
                                            const now = context.raw;
                                            if (daily !== 0) {{
                                                return `일일매출: ${{daily.toLocaleString()}}원 \n 누적 매출: ${{now.toLocaleString()}}원`;
                                            }} else {{
                                                return `누적 매출: ${{now != null ? now.toLocaleString() + '원' : 'N/A'}}`;
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                </script>
               <div class="summary-box-right" style="width: 100%;">
                  <div class="summary-box">
                    <table class="summary-table">
                      <tr>
                        <td>{prev_month}월 누적 매출</td>
                        <td>:</td>
                        <td>{summary_amount_prev:,}원</td>
                      </tr>                    
                      <tr>
                        <td>{curr_month}월 누적 매출</td>
                        <td>:</td>
                        <td>{summary_amount_curr:,}원</td>
                      </tr>
                      <tr>
                        <td>{curr_month}월 일평균 매출</td>
                        <td>:</td>
                        <td>{daily_avg:,}원</td>
                      </tr>
                      <tr>
                        <td>{curr_month}월 예측 매출</td>
                        <td>:</td>
                        <td>{predicted_amount:,}원</td>
                      </tr>
                    </table>
                  </div>
                </div>
                </div>                
            </div> 
        <div class="updated">Updated {now_str}</div>
        </body>
        </html>
        """

        graph_path = os.path.join(DASHBOARD_PATH, "calendar_dashboard.html")
        # Ensure the dashboard path exists
        os.makedirs(DASHBOARD_PATH, exist_ok=True)
        with open(graph_path, "w", encoding="utf-8") as f:
            f.write(chart_html)
        if DEBUG:
            print(f"[DEBUG] 캘린더 대시보드 HTML 저장 완료: {graph_path}")

    return sales

def main_monthly_payment():

    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")

    driver = create_driver()

    try:
        if login(driver):
            fetch_monthly_sales_from_calendar(driver)
        
    except Exception as e:
        pass
    finally:
        driver.quit()
