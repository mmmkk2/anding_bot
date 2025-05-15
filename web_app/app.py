from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
@app.route("/seat")
def seat_dashboard():
    dashboard_path = "/home/mmkkshim/anding_bot/seat_dashboard.html"
    if os.path.exists(dashboard_path):
        return send_file(dashboard_path)
    else:
        return "Dashboard not found", 404