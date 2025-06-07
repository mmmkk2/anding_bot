from flask import Flask, send_file, render_template
import os
import subprocess


import re
from bs4 import BeautifulSoup
from datetime import datetime
import pytz  # 추가

from dotenv import load_dotenv


try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass


DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/")

LOGIN_ID = os.getenv("LOGIN_ID", "anding_bot")
LOGIN_PWD = os.getenv("LOGIN_PWD", "871104tla#")

VIEWER_ID = os.getenv("VIEWER_ID", "viewer")
VIEWER_PWD = os.getenv("VIEWER_PWD", "viewerpass")


DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/")


app = Flask(__name__)

# Set permanent session lifetime to 7 days
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=7)

# --- Form-based login logic ---
from flask import request, redirect, url_for, session, render_template_string

app.secret_key = "your_secret_key"  # change this to a secure value



@app.route("/login", methods=["GET", "POST"])
def login():
    # The login page should always be accessible regardless of session state
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == LOGIN_ID and password == LOGIN_PWD:
            session["logged_in"] = True
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        if os.getenv("VIEWER_BLOCK", "false").lower() == "true":
            return "뷰어 로그인은 현재 차단되어 있습니다.", 403
        elif username == VIEWER_ID and password == VIEWER_PWD:
            session["logged_in"] = True
            session["is_admin"] = False
            return redirect(url_for("viewer_dashboard"))
        return "로그인 실패", 401

    # Always render login page for GET requests (do not redirect based on session here)
    return render_template_string('''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>로그인</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f8f9fa;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            padding: 2rem;
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            max-width: 360px;
            width: 100%;
        }
        h3 {
            margin-bottom: 1rem;
            font-size: 1.2rem;
            color: #333;
        }
        input, button {
            box-sizing: border-box;
        }
        input {
            width: 100%;
            padding: 0.7rem;
            margin-bottom: 1rem;
            border: 1px solid #ccc;
            border-radius: 0.5rem;
            font-size: 1rem;
        }
        button {
            width: 100%;
            padding: 0.7rem;
            background: #495057;
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-size: 1rem;
            cursor: pointer;
        }
        button:hover {
            background: #343a40;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <form method="post">
            <h3>로그인</h3>
            <input type="text" name="username" placeholder="아이디" required>
            <input type="password" name="password" placeholder="비밀번호" required>
            <button type="submit">로그인</button>
        </form>
    </div>
</body>
</html>
''')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.before_request
def require_login():
    session.permanent = True
    # Always allow access to login and static routes
    if request.endpoint in ("login", "static"):
        return
    if not session.get("logged_in"):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return "세션이 만료되었습니다", 401
        return redirect(url_for("login"))


@app.route("/admin")
def admin_dashboard():
    # Only allow access if is_admin is True, else redirect to login
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_dashboard(is_admin=True, is_viewer=False)

@app.route("/viewer")
def viewer_dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_dashboard(is_admin=session.get("is_admin", False), is_viewer=True)

# --- Direct mode switch routes ---
@app.route("/set_viewer", methods=["POST"])
def set_viewer():
    session["logged_in"] = True
    session["is_admin"] = False
    return redirect(url_for("viewer_dashboard"))

@app.route("/set_admin", methods=["POST"])
def set_admin():
    # Allow promotion to admin if session already valid (either admin or viewer)
    if session.get("logged_in"):
        session["logged_in"] = True
        session["is_admin"] = True
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))

@app.route("/")
def index_redirect():
    return redirect(url_for("login"))

def render_dashboard(is_admin=True, is_viewer=False):
    # --- 상품 현황: 1회이용권 판매중 상품 요약 추출 ---
    product_summary = ""
    product_path = os.path.join(DASHBOARD_PATH, "product_dashboard.html")
    if os.path.exists(product_path):
        with open(product_path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")

        # "1회이용권" 탭에서만 추출
        once_tab = soup.find("div", {"id": "once"})
        rows = once_tab.select("table tbody tr") if once_tab else []
        matching = []
        extendable = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                name = cols[0].get_text(strip=True)
                check_input = cols[3].find("input")
                extension_input = cols[4].find("input")
                is_checked = check_input and check_input.has_attr("checked")
                is_extendable = extension_input and extension_input.has_attr("checked")
                if "제한" not in name and name and "시간" in name:
                    if is_checked:
                        matching.append(name)
                    if is_extendable:
                        extendable.append(name)

        product_summary = ", ".join(matching) if matching else "없음"
        extendable_summary = ", ".join(extendable) if extendable else "없음"
    # Dynamically read thresholds at runtime
    WARNING_THRESHOLD = int(os.getenv("WARNING_THRESHOLD", "8"))
    DANGER_THRESHOLD = int(os.getenv("DANGER_THRESHOLD", "5"))
    kst = pytz.timezone("Asia/Seoul")  # KST 시간대
    today_str = datetime.now(kst).strftime("%Y-%m-%d")  # ✅ 여기에 KST 적용
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    # (Redundant check removed as per request)

    def is_currently_in_use(reservations, now_str):
        kst = pytz.timezone("Asia/Seoul")
        now_naive = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
        now = kst.localize(now_naive)

        for r in reservations:
            try:
                start_str, end_str = r['time'].split("~")
                start_dt_naive = datetime.strptime(start_str.strip(), "%Y.%m.%d %H:%M")
                end_dt_naive = datetime.strptime(end_str.strip(), "%Y.%m.%d %H:%M")
                start_dt = kst.localize(start_dt_naive)
                end_dt = kst.localize(end_dt_naive)

                if start_dt <= now <= end_dt:
                    return True
            except:
                continue
        return False

    def extract_summary(filepath, type="seat"):
        if not os.path.exists(filepath):
            return "정보 없음", "--:--:--"
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
        updated = re.search(r"Updated ([\d\-: ]+)", html)
        if type == "seat":
            update_mode_match = re.search(r"업데이트 시각: [\d\-: ]+ \((.)\)", html)
            update_mode = update_mode_match.group(1) if update_mode_match else "?"
            updated_time_raw = updated.group(1) if updated else "--:--:--"
            updated_time = f"{updated_time_raw} ({update_mode})"
            stat = re.search(r"자유석: (\d+)/(\d+).*?노트북석: (\d+)/(\d+)", html, re.DOTALL)
            if stat:
                f_used, f_total, l_used, l_total = stat.groups()
                remaining = int(f_total) - int(f_used)
                summary = f"남은 자유석  {remaining}석"
                threshold_warning = int(os.getenv("WARNING_THRESHOLD", "8"))
                threshold_danger = int(os.getenv("DANGER_THRESHOLD", "5"))
                emoji = "🔴" if remaining <= threshold_danger else ("🟡" if remaining <= threshold_warning else "🟢")
                return f"<b>좌석 현황</b> {emoji} · {summary} · ⏱️ {updated_time}", updated_time
            return "정보 없음", updated_time
        elif type == "payment":
            updated_time_raw = updated.group(1) if updated else "--:--:--"
            mode_match = re.search(r"\((B|M)\)", html)
            update_mode = mode_match.group(1) if mode_match else "?"
            updated_time = f"{updated_time_raw} ({update_mode})"
            match = re.search(r"총 결제: (\d+)건 / ([\d,]+원)", html)
            if match:
                summary = f"총 매출 {match.group(1)}건 / {match.group(2)}"
                return summary, updated_time, int(match.group(2).replace(",", "").replace("원", ""))
        elif type == "monthly":
            updated_time_raw = updated.group(1) if updated else "--:--:--"
            mode_match = re.search(r"\((B|M)\)", html)
            update_mode = mode_match.group(1) if mode_match else "?"
            updated_time = f"{updated_time_raw} ({update_mode})"
            curr_month = datetime.now(pytz.timezone("Asia/Seoul")).month
            matches = re.findall(r"([\d,]+)원", html)
            if len(matches) >= 2:
                return "", updated_time, int(matches[1].replace(",", ""))
            return "", updated_time, 0
        elif type == "studyroom":
            studyroom_updated_match = re.search(r"Updated ([\d\-:\. ]+)", html)
            if studyroom_updated_match:
                studyroom_updated = studyroom_updated_match.group(1)
                mode_match = re.search(r"\((B|M)\)", html)
                update_mode = mode_match.group(1) if mode_match else "?"
                studyroom_updated = f"{studyroom_updated} ({update_mode})"
                return "정보 없음", studyroom_updated

        elif type == "product":
            updated_time_raw = updated.group(1) if updated else "--:--:--"
            mode_match = re.search(r"\((B|M)\)", html)
            update_mode = mode_match.group(1) if mode_match else "?"
            updated_time = f"{updated_time_raw} ({update_mode})"
            return "정보 없음", updated_time

        return "정보 없음", updated_time

    seat_path = os.path.join(DASHBOARD_PATH, "seat_dashboard.html")
    payment_path = os.path.join(DASHBOARD_PATH, "payment_dashboard.html")
    if os.path.exists(seat_path):
        with open(seat_path, "r", encoding="utf-8") as f:
            seat_html = f.read()
        stat_line_match = re.search(r"&lt;div class=&quot;stat&quot;&gt;(.*?)&lt;/div&gt;", seat_html)
        if not stat_line_match:
            stat_line_match = re.search(r'<div class="stat">(.*?)</div>', seat_html)
        seat_stat_line = stat_line_match.group(1) if stat_line_match else "정보 없음"
        updated_match = re.search(r"Updated ([\d\-: ]+)", seat_html)
        mode_match = re.search(r"\((B|M)\)", seat_html)
        update_mode = mode_match.group(1) if mode_match else "?"
        seat_updated_time = updated_match.group(1) if updated_match else "--:--:--"
        seat_updated = f"{seat_updated_time} ({update_mode})"
        remain_match = re.search(r"🟩\s*(\d+)", seat_stat_line)
        if remain_match:
            remain_count = int(remain_match.group(1))
            if remain_count <= DANGER_THRESHOLD:
                seat_emoji = "🔴"
            elif remain_count <= WARNING_THRESHOLD:
                seat_emoji = "🟡"
            else:
                seat_emoji = "🟢"
            seat_summary_line = f"{seat_emoji} 남은 자유석 {remain_count}석"
        else:
            seat_summary_line = "정보 없음"

    else:
        seat_summary_line = "정보 없음"
        seat_updated = "--:--:--"

    payment_summary, payment_updated, payment_amount_curr = extract_summary(payment_path, "payment")
    monthly_path = os.path.join(DASHBOARD_PATH, "calendar_dashboard.html")
    monthly_summary, monthly_updated, monthly_amount_curr = extract_summary(monthly_path, "monthly")
    curr_month = datetime.now(kst).month
    monthly_summary_line = f"{curr_month}월 {monthly_amount_curr:,}원"
    studyroom_path = os.path.join(DASHBOARD_PATH, "studyroom_dashboard.html")
    _, studyroom_updated = extract_summary(studyroom_path, "studyroom")

    _, product_updated = extract_summary(product_path, "product")
    count_2, count_4, first_time = "-", "-", "-"
    reservations_2 = []
    reservations_4 = []
    using_2 = False
    using_4 = False
    html = ""
    if os.path.exists(studyroom_path):
        with open(studyroom_path, "r", encoding="utf-8") as f:
            html = f.read()
        count_2_match = re.search(r"2인실.*?예약\s*(\d+)건", html)
        count_4_match = re.search(r"4인실.*?예약\s*(\d+)건", html)
        if count_2_match:
            count_2 = count_2_match.group(1)
        if count_4_match:
            count_4 = count_4_match.group(1)
        def parse_reservations(block):
            pattern = r"<td>(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) ~ (\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})</td>"
            return [{"time": f"{m[0]} ~ {m[1]}"} for m in re.findall(pattern, block)]
        two_block = re.search(r"<h2>2인실</h2>.*?<tbody>(.*?)</tbody>", html, re.DOTALL)
        four_block = re.search(r"<h2>4인실</h2>.*?<tbody>(.*?)</tbody>", html, re.DOTALL)
        reservations_2 = parse_reservations(two_block.group(1)) if two_block else []
        reservations_4 = parse_reservations(four_block.group(1)) if four_block else []
        using_2 = is_currently_in_use(reservations_2, now_str)
        using_4 = is_currently_in_use(reservations_4, now_str)
    # Mask names in studyroom reservation table if not admin and not viewer
    if not (is_admin and not is_viewer) and html:
        # 두 글자 이름: 앞글자만 보이고 뒤는 'x'로 마스킹 (권범 → 권x)
        html = re.sub(r'\b([가-힣])([가-힣])\b', r'\1x', html)  # 두 글자 이름
        # 세 글자 이상인 경우: 앞글자만 보이고 나머지는 'xx'로 마스킹 (홍길동 → 홍xx)
        html = re.sub(r'\b([가-힣])[가-힣]{2,}\b', r'\1xx', html)  # 세 글자 이상

    # Compose HTML blocks for payment and monthly (admin only)
    payment_monthly_blocks = ""
    if is_admin and not is_viewer:
        payment_monthly_blocks = f"""
            <div class="toggle-section">
                <div class="summary-header-row">
                    <div class="summary-header">
                        💳 <b>결제 현황</b><br>
                        {payment_summary}<br>
                        <div class="updated">Updated {payment_updated}</div>
                    </div>
                    <div class="summary-buttons">
                      <form method="post" action="/run_p_output">
                        <button class="pill small" type="submit"> 📜 </button>
                      </form>
                    </div>
                </div>
                <button class="toggle-button" onclick="toggle('payment')">자세히 보기</button>
                <div id="payment" class="content">
                    <iframe id="toggle-iframe-payment" src="/payment" style="width: 100%; height: 500px;" frameborder="0"></iframe>
                </div>
            </div>
            <div class="toggle-section">
                <div class="summary-header-row">
                    <div class="summary-header">
                        📊 <b>월별 누적 매출</b><br>{monthly_summary_line}<br>
                        <div class="updated">Updated {monthly_updated}</div>
                    </div>
                    <div class="summary-buttons">
                      <form method="post" action="/run_m_output">
                        <button class="pill small" type="submit">📜 </button>
                      </form>
                    </div>
                </div>
                <button class="toggle-button" onclick="toggle('monthly')">자세히 보기</button>
                <div id="monthly" class="content">
                    <iframe id="toggle-iframe-monthly" src="/monthly" style="width: 100%; height: 500px;" frameborder="0"></iframe>

                </div>
            </div>
        """

    # Floating menu: three-dot menu for admin or viewer only
    floating_menu_html = ""
    if is_admin or is_viewer:
        floating_menu_html = """
        <div class="floating-menu-wrapper" style="position: fixed; bottom: 20px; left: 20px; z-index: 999;">
            <button class="floating-menu-toggle floating-menu-button" style="background: #eee; border: none; border-radius: 50%; width: 48px; height: 48px; font-size: 20px; cursor: pointer;">⋯</button>
            <div class="floating-menu" style="display: none;">
                <a href="/admin" class="menu-option">관리자</a>
                <a href="/viewer" class="menu-option">뷰어</a>
                <form method="get" action="/env_config" style="margin: 0; padding: 0;">
                  <button class="menu-option" type="submit">.env 설정</button>
                </form>
                <form method="get" action="/admin" style="margin: 0; padding: 0;">
                  <button class="menu-option" type="submit">🔄 새로고침</button>
                </form>
                <a href="/logout" class="menu-option" style="color: #c00;">로그아웃</a>
            </div>
        </div>
        <script>
        (function() {
            var btn = document.querySelector('.floating-menu-toggle');
            var menu = document.querySelector('.floating-menu');
            if (btn && menu) {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    menu.style.display = (menu.style.display === "block") ? "none" : "block";
                });
                document.addEventListener('click', function(e) {
                    menu.style.display = "none";
                });
            }
        })();
        </script>
        """
    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta http-equiv="refresh" content="60" />
        <title>앤딩스터디카페 대시보드</title>
        <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_app.css">
        <style>
            .pill.small {{
                font-size: 0.75rem;
                padding: 0.3rem 0.8rem;
            }}
            .pill.right {{
                margin-left: auto;
            }}
            .summary-header-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .box-right {{
                display: flex;
                justify-content: flex-end;
            }}
        </style>
    </head>
    <body>
        {floating_menu_html}
        <div class="box">
            <div class="toggle-section">
                <div class="summary-header-row">
                    <div class="summary-header">
                        🪑 <b>좌석 현황</b><br>
                        {seat_summary_line}<br>
                        <div class="updated">Updated {seat_updated}</div>
                    </div>
                    <div class="summary-buttons">
                    {"".join([
                      '<form method="post" action="/run_s_output"><button class="pill small" type="submit">📜 </button></form>'
                    ]) if is_admin and not is_viewer else ""}
                    </div>
                </div>
                <button class="toggle-button" onclick="toggle('seat')">자세히 보기</button>
                <div id="seat" class="content">
                    <iframe id="toggle-iframe-seat" src="/seat" style="width: 100%; height: 500px;" frameborder="0"></iframe>
                </div>
            </div>
            <div class="toggle-section">
                <div class="summary-header-row">
                    <div class="summary-header">
                        📦 <b>상품 현황</b><br>
                        <div class="summary-header">
                            1회 이용권 구매가능: {product_summary}<br>1회 이용권 연장가능: {extendable_summary}
                            <div class="updated">Updated {product_updated}</div>
                        </div>
                    </div>
                </div>
                <button class="toggle-button" onclick="toggle('product')">자세히 보기</button>
                <div id="product" class="content">
                    <iframe id="toggle-iframe-product" src="/product" style="width: 100%; height: 500px;" frameborder="0"></iframe>
                </div>
            </div>
            {payment_monthly_blocks}
            <div class="toggle-section">
                <div class="summary-header-row">
                    <div class="summary-header">
                        📘 <b>스터디룸 예약현황</b><br>
                        {'🔴' if using_2 else '⚪'} 2인실 : 예약 {count_2}건 <br>
                        {'🔴' if using_4 else '⚪'} 4인실 : 예약 {count_4}건 <br>
                        <div class="updated">Updated {studyroom_updated}</div>
                    </div>
                    <div class="summary-buttons">
                    {"".join([
                      '<form method="post" action="/run_r_output"><button class="pill small" type="submit">📜 </button></form>'
                    ]) if is_admin and not is_viewer else ""}
                    </div>
                </div>
                <button class="toggle-button" onclick="toggle('studyroom')">자세히 보기</button>
                <div id="studyroom" class="content">
                    <iframe id="toggle-iframe-studyroom" src="/studyroom" style="width: 100%; height: 500px;" frameborder="0"></iframe>
                </div>
            </div>
        </div>
        <script>
            function toggle(id) {{
                const el = document.getElementById(id);
                el.style.display = (el.style.display === "block") ? "none" : "block";
            }}
        </script>
    </body>
    </html>
    """
# --- .env config routes ---
from dotenv import set_key
from pathlib import Path

@app.route("/env_config", methods=["GET"])
def env_config():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    danger = int(os.getenv("DANGER_THRESHOLD", "5"))
    warning = int(os.getenv("WARNING_THRESHOLD", "8"))
    cum = int(os.getenv("WARNING_CUM_THRESHOLD", "50"))
    return f"""
<!DOCTYPE html>
<html lang='ko'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>.env 설정</title>
    <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_app.css">
</head>
<body>
    <a class="floating-refresh reload" href="/admin">⬅️</a> 
    <div class="log-container">
        <div class="log-title">⚙️ .env 임계값 설정</div>
        <form method="POST" action="/update_env_config">
            <label>DANGER_THRESHOLD: <input type="number" name="danger" value={danger}></label><br>
            <label>WARNING_THRESHOLD: <input type="number" name="warning" value={warning}></label><br>
            <label>WARNING_CUM_THRESHOLD: <input type="number" name="cum" value={cum}></label><br>
            <div style="margin-top: 1rem;"></div>
            <button class="pill small" type="submit">저장</button>
        </form>
    </div>

</body>
</html>
"""

@app.route("/update_env_config", methods=["POST"])
def update_env_config():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    env_path = Path("/home/mmkkshim/anding_bot/.env")
    danger = request.form.get("danger", "5")
    warning = request.form.get("warning", "8")
    cum = request.form.get("cum", "50")
    set_key(str(env_path), "DANGER_THRESHOLD", danger)
    set_key(str(env_path), "WARNING_THRESHOLD", warning)
    set_key(str(env_path), "WARNING_CUM_THRESHOLD", cum)
    load_dotenv(dotenv_path=env_path, override=True)
    return redirect(url_for("admin_dashboard"))

@app.route("/seat")
def seat_dashboard():
    path = os.path.join(DASHBOARD_PATH, "seat_dashboard.html")
    if not os.path.exists(path):
        return "Seat dashboard not found", 404
    if session.get("is_admin"):
        return send_file(path)
    else:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
        # Find the table with the 이름 column
        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue
            header_cells = thead.find_all(["th", "td"])
            name_col_idx = None
            for idx, cell in enumerate(header_cells):
                if "이름" in cell.get_text():
                    name_col_idx = idx
                    break
            if name_col_idx is None:
                continue
            tbody = table.find("tbody")
            if not tbody:
                continue
            # Check if this is the "종료 예정 자유석" table by column headers
            col_names = [cell.get_text(strip=True) for cell in header_cells]
            is_expiring_seat = "종료" in "".join(col_names) and "자유석" in "".join(col_names)
            # Find index for "종료시각" column if exists
            end_col_idx = None
            for idx, cell in enumerate(header_cells):
                if "종료시각" in cell.get_text():
                    end_col_idx = idx
                    break
            # If it's the expiring seat table, add 남은시간 column and highlight if < 1 hour
            if is_expiring_seat and end_col_idx is not None:
                # Add "남은시간" column header if not already present
                if not any("남은시간" in cell.get_text() for cell in header_cells):
                    new_th = soup.new_tag("th")
                    new_th.string = "남은시간"
                    thead.find("tr").append(new_th)
                # For each row, add the 남은시간 cell and highlight if < 1 hour
                for row in tbody.find_all("tr"):
                    tds = row.find_all("td")
                    if len(tds) > end_col_idx:
                        end_time_str = tds[end_col_idx].get_text(strip=True)
                        # Try parsing end_time_str
                        try:
                            # Accept both "YYYY.MM.DD HH:MM" and "YYYY-MM-DD HH:MM" etc.
                            end_time_str_fixed = re.sub(r"[.]", "-", end_time_str[:10]) + end_time_str[10:]
                            # If only date and time, fill seconds as :00
                            if len(end_time_str_fixed) == 16:
                                end_time_str_fixed += ":00"
                            kst = pytz.timezone("Asia/Seoul")
                            end_dt_naive = datetime.strptime(end_time_str_fixed, "%Y-%m-%d %H:%M:%S")
                            end_dt = kst.localize(end_dt_naive)
                            now = datetime.now(kst)
                            diff = end_dt - now
                            if diff.total_seconds() < 0:
                                remain_str = "만료"
                            else:
                                hours = int(diff.total_seconds() // 3600)
                                minutes = int((diff.total_seconds() % 3600) // 60)
                                remain_str = f"{hours}시간 {minutes}분"
                        except Exception:
                            remain_str = "N/A"
                            diff = None
                        new_td = soup.new_tag("td")
                        new_td.string = remain_str
                        if diff is not None and diff.total_seconds() < 3600:
                            new_td['style'] = "color:red; font-weight:bold;"
                        row.append(new_td)
            # Mask names in name column
            for row in tbody.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) > name_col_idx:
                    td = tds[name_col_idx]
                    orig = td.get_text()
                    # Updated masking logic
                    if len(orig) == 2:
                        masked = re.sub(r"^([가-힣])[가-힣]$", r"\1x", orig)
                    elif len(orig) >= 3:
                        masked = re.sub(r"^([가-힣])[가-힣]{2,}$", r"\1xx", orig)
                    else:
                        masked = orig
                    td.string = masked
        return str(soup)


# --- Product dashboard route ---
@app.route("/product")
def product():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    path = os.path.join(DASHBOARD_PATH, "product_dashboard.html")
    return send_file(path) if os.path.exists(path) else ("Product dashboard not found", 404)

@app.route("/payment")
def payment_dashboard():
    path = os.path.join(DASHBOARD_PATH, "payment_dashboard.html")
    return send_file(path) if os.path.exists(path) else ("Payment dashboard not found", 404)


@app.route("/studyroom")
def studyroom_dashboard():
    path = os.path.join(DASHBOARD_PATH, "studyroom_dashboard.html")
    if not os.path.exists(path):
        return "Studyroom dashboard not found", 404
    if session.get("is_admin"):
        return send_file(path)
    else:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
        # Find all tables with 이름 column and mask that column
        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue
            header_cells = thead.find_all(["th", "td"])
            name_col_idx = None
            for idx, cell in enumerate(header_cells):
                if "이름" in cell.get_text():
                    name_col_idx = idx
                    break
            if name_col_idx is None:
                continue
            tbody = table.find("tbody")
            if not tbody:
                continue
            for row in tbody.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) > name_col_idx:
                    td = tds[name_col_idx]
                    orig = td.get_text()
                    # Updated masking logic
                    if len(orig) == 2:
                        masked = re.sub(r"^([가-힣])[가-힣]$", r"\1x", orig)
                    elif len(orig) >= 3:
                        masked = re.sub(r"^([가-힣])[가-힣]{2,}$", r"\1xx", orig)
                    else:
                        masked = orig
                    td.string = masked
        return str(soup)

# --- Monthly cumulative payments graph/dashboard ---
@app.route("/monthly")
def monthly_graph():
    path = os.path.join(DASHBOARD_PATH, "calendar_dashboard.html")
    return send_file(path) if os.path.exists(path) else ("Monthly calendar dashboard not found", 404)



# --- Log routes ---
@app.route("/run_all_output", methods=["POST"])
def run_all_output():
    return render_log("/home/mmkkshim/anding_bot/logs/run_all.log")

# 좌석 현황 로그
@app.route("/run_s_output", methods=["POST"])
def run_s_output():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_log("/home/mmkkshim/anding_bot/logs/run_s.log")

# 결제 현황 로그
@app.route("/run_p_output", methods=["POST"])
def run_p_output():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_log("/home/mmkkshim/anding_bot/logs/run_p.log")

# 스터디룸 예약현황 로그
@app.route("/run_r_output", methods=["POST"])
def run_r_output():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_log("/home/mmkkshim/anding_bot/logs/run_r.log")

# 월별 누적 매출 로그
@app.route("/run_m_output", methods=["POST"])
def run_m_output():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_log("/home/mmkkshim/anding_bot/logs/run_m.log")

def render_log(log_path):
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        content = f"⚠️ 로그를 불러오는 중 오류 발생: {e}"
    return f"""
    <!DOCTYPE html>
    <html lang='ko'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>실행 로그</title>
        <link rel="stylesheet" href="https://mmkkshim.pythonanywhere.com/style/dashboard_app.css">
    </head>
    <body>
        <a class="floating-refresh reload" href="/admin">⬅️</a> 
        <div class="log-container">
            <div class="log-title">실행 로그</div>
            <pre class="log-output">{content}</pre>
        </div>
    </body>
    </html>
    """

# --- Route to run the shell script ---
@app.route("/run_all", methods=["POST"])
def run_all():
    os.system("bash /home/mmkkshim/anding_bot/run_all.sh &")
    return redirect(url_for("render_dashboard"))

# --- Individual script execution routes ---
@app.route("/run_s", methods=["POST"])
def run_s():
    os.system("bash /home/mmkkshim/anding_bot/run_s.sh > /home/mmkkshim/anding_bot/logs/run_s.log 2>&1 &")
    return redirect(url_for("render_dashboard"))

@app.route("/run_p", methods=["POST"])
def run_p():
    os.system("bash /home/mmkkshim/anding_bot/run_p.sh > /home/mmkkshim/anㅁding_bot/logs/run_p.log 2>&1 &")
    return redirect(url_for("render_dashboard"))

@app.route("/run_r", methods=["POST"])
def run_r():
    os.system("bash /home/mmkkshim/anding_bot/run_r.sh > /home/mmkkshim/anding_bot/logs/run_r.log 2>&1 &")
    return redirect(url_for("render_dashboard"))

@app.route("/run_m", methods=["POST"])
def run_m():
    os.system("bash /home/mmkkshim/anding_bot/run_m.sh > /home/mmkkshim/anding_bot/logs/run_m.log 2>&1 &")
    return redirect(url_for("render_dashboard"))

@app.route("/run_kill", methods=["POST"])
def run_kill():
    os.system("bash /home/mmkkshim/anding_bot/kill.sh > /home/mmkkshim/anding_bot/logs/kill.log 2>&1 &")
    return redirect(url_for("render_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
