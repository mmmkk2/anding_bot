from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def combined_dashboard():
    seat_path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    payment_path = "/home/mmkkshim/anding_bot/payment_dashboard.html"

    seat_html = ""
    payment_html = ""

    if os.path.exists(seat_path):
        with open(seat_path, "r", encoding="utf-8") as f:
            seat_html = f.read()
    if os.path.exists(payment_path):
        with open(payment_path, "r", encoding="utf-8") as f:
            payment_html = f.read()

    combined_html = f"""
    <!DOCTYPE html>
    <html lang='ko'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>앤딩스터디카페 통합 대시보드</title>
        <style>
            body {{
                margin: 0;
                padding: 1rem;
                background: #f4f4f4;
                font-family: 'Apple SD Gothic Neo', Arial, sans-serif;
            }}
            .dashboard-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 1rem;
                justify-content: center;
            }}
            .dashboard-box {{
                flex: 1 1 600px;
                max-width: 600px;
                border-radius: 1rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                background: white;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                align-items: flex-start;
            }}
            iframe {{
                width: 100%;
                border: none;
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class='dashboard-container'>
            <div class='dashboard-box' style='align-items: flex-start;'>
                <iframe src='/seat' style='height: 1000px;'></iframe>
            </div>
            <div class='dashboard-box'>
                <iframe src='/payment' style='height: 1000px;'></iframe>
            </div>
        </div>
    </body>
    </html>
    """
    return combined_html

@app.route("/seat")
def seat_dashboard():
    dashboard_path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    if os.path.exists(dashboard_path):
        return send_file(dashboard_path)
    else:
        return "Dashboard not found", 404

@app.route("/payment")
def payment_dashboard():
    dashboard_path = "/home/mmkkshim/anding_bot/payment_dashboard.html"
    if os.path.exists(dashboard_path):
        return send_file(dashboard_path)
    else:
        return "Payment dashboard not found", 404