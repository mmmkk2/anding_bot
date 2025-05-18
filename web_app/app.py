from flask import Flask, send_file
import os
import re
from datetime import datetime
import pytz  # 추가


app = Flask(__name__)

# --- Form-based login logic ---
from flask import request, redirect, url_for, session, render_template_string

app.secret_key = "your_secret_key"  # change this to a secure value



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "anding" and password == "study1234":
            session["logged_in"] = True
            return redirect(url_for("summary_dashboard"))
        return "로그인 실패", 401
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
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 90%;
        }
        h3 {
            margin-bottom: 1rem;
            font-size: 1.2rem;
            color: #333;
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
    if request.endpoint not in ("login", "static") and not session.get("logged_in"):
        return redirect(url_for("login"))


@app.route("/")
def summary_dashboard():
    kst = pytz.timezone("Asia/Seoul")  # KST 시간대
    today_str = datetime.now(kst).strftime("%Y-%m-%d")  # ✅ 여기에 KST 적용

    def extract_summary(filepath, type="seat"):
        if not os.path.exists(filepath):
            return "정보 없음", "⚪", "--:--:--"

        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()

        updated = re.search(r"업데이트 시각: ([\d\-: ]+)", html)
        updated_time = updated.group(1) if updated else "--:--:--"

        if type == "seat":
            stat = re.search(r"자유석: (\d+)/(\d+).*?노트북석: (\d+)/(\d+)", html, re.DOTALL)
            if stat:
                f_used, f_total, l_used, l_total = stat.groups()
                summary = f"자유석 {f_used}/{f_total} | 노트북석 {l_used}/{l_total}"
                remaining = int(f_total) - int(f_used)
                emoji = "🔴" if remaining <= 5 else ("🟡" if remaining <= 7 else "🟢")
                return summary, emoji, updated_time
        elif type == "payment":
            match = re.search(r"총 결제: (\d+)건 / ([\d,]+원)", html)
            if match:
                summary = f"총 결제 {match.group(1)}건 / {match.group(2)}"
                return summary, "", updated_time
        return "정보 없음", "⚪", updated_time

    seat_path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    payment_path = "/home/mmkkshim/anding_bot/payment_dashboard.html"

    seat_summary, seat_status, seat_updated = extract_summary(seat_path, "seat")
    payment_summary, _, payment_updated = extract_summary(payment_path, "payment")


    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta http-equiv="refresh" content="60" />
        <title>앤딩스터디카페 요약 - {today_str}</title>
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
                background: #f1f3f5;
                padding: 2rem;
                margin: 0;
                display: flex;
                justify-content: center;
            }}
            .box {{
                max-width: 720px;
                width: 100%;
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .toggle-section {{
                margin-bottom: 2rem;
            }}
            .summary-header {{
                font-size: 0.95rem;
                margin-bottom: 0.5rem;
                text-align: left;
            }}
            .status {{
                font-size: 1.2rem;
                margin-left: 0.3rem;
            }}
            .updated {{
                font-size: 0.75rem;
                color: #888;
                margin-top: 0.2rem;
            }}
            .toggle-button {{
                display: block;
                width: 100%;
                padding: 0.6rem;
                background: #adb5bd;
                color: white;
                border: none;
                border-radius: 0.5rem;
                font-size: 0.9rem;
                cursor: pointer;
                text-align: left;
                margin-top: 0.5rem;
            }}
            .content {{
                display: none;
                margin-top: 1rem;
            }}
            iframe {{
                width: 100%;
                min-height: 600px;
                border: none;
                border-radius: 0.5rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            @media (max-width: 480px) {{
              iframe {{
                min-height: 420px;  /* 또는 필요시 더 작게 */
              }}
            }}

        </style>
    </head>
    <body>
        <div class="box">
            <div class="toggle-section">
                <div class="summary-header">
                    🪑 <b>{seat_summary}</b> <span class="status">{seat_status}</span>
                    <div class="updated">업데이트: {seat_updated}</div>
                </div>
                <button class="toggle-button" onclick="toggle('seat')">자세히 보기</button>
                <div id="seat" class="content">
                    <iframe src="/seat"></iframe>
                </div>
            </div>
            <div class="toggle-section">
                <div class="summary-header">
                    💳 <b>{payment_summary}</b>
                    <div class="updated">업데이트: {payment_updated}</div>
                </div>
                <button class="toggle-button" onclick="toggle('payment')">자세히 보기</button>
                <div id="payment" class="content">
                    <iframe src="/payment"></iframe>
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

@app.route("/seat")
def seat_dashboard():
    path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    return send_file(path) if os.path.exists(path) else ("Seat dashboard not found", 404)

@app.route("/payment")
def payment_dashboard():
    path = "/home/mmkkshim/anding_bot/payment_dashboard.html"
    return send_file(path) if os.path.exists(path) else ("Payment dashboard not found", 404)

if __name__ == "__main__":
    app.run(debug=True)