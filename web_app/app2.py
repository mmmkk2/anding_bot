from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def summary_dashboard():
    seat_path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    payment_path = "/home/mmkkshim/anding_bot/payment_dashboard.html"

    def extract_inner_box(file_path):
        if not os.path.exists(file_path):
            return "<div class='box'>데이터 없음</div>"
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        start = html.find('<div class="box">')
        end = html.find("</div>", start)
        return html[start:end+6] if start != -1 else "<div class='box'>박스 형식 오류</div>"

    seat_summary = extract_inner_box(seat_path)
    payment_summary = extract_inner_box(payment_path)

    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>요약 대시보드</title>
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
                background: #f1f3f5;
                padding: 2rem;
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: start;
                gap: 2rem;
            }}
            .summary-wrapper {{
                max-width: 720px;
                width: 100%;
            }}
            .box {{
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="summary-wrapper">{seat_summary}</div>
        <div class="summary-wrapper">{payment_summary}</div>
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