def save_dashboard_html(used_free, total_free, used_laptop, total_laptop, remaining, status_emoji):
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    history_path = "log/seat_history.csv"
    history_rows = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            history_rows = lines[-10:]  # 마지막 10개만 추출

    timestamps = []
    used_frees = []

    for line in history_rows:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            timestamps.append(parts[0])
            used_frees.append(int(parts[1]))

    chart_script = f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const ctx = document.getElementById('seatChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {timestamps},
                datasets: [{{
                    label: '자유석 사용 수',
                    data: {used_frees},
                    fill: false,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.1
                }}]
            }},
            options: {{
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: {total_free}
                    }}
                }}
            }}
        }});
    </script>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>앤딩스터디카페 좌석 현황</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{
                font-family: 'Apple SD Gothic Neo', 'Arial', sans-serif;
                background: #f4f4f4;
                margin: 0;
                padding: 1rem;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .box {{
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h1 {{
                font-size: 1.4rem;
                margin-bottom: 1rem;
                color: #333;
            }}
            .emoji {{
                font-size: 2.5rem;
                margin-bottom: 1rem;
            }}
            .stat {{
                font-size: 1.1rem;
                margin: 0.3rem 0;
            }}
            .updated {{
                font-size: 0.8rem;
                color: #888;
                margin-top: 1rem;
            }}
            .history {{
                text-align: left;
                max-height: 200px;
                overflow-y: auto;
                margin-top: 1.5rem;
                color: #444;
            }}
            .history ul {{
                padding-left: 1.2rem;
                margin: 0;
            }}
            .history li {{
                margin-bottom: 0.3rem;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🪑 앤딩스터디카페 좌석 현황</h1>
            <div class="emoji">{status_emoji}</div>
            <div class="stat">자유석: {used_free}/{total_free}</div>
            <div class="stat">노트북석: {used_laptop}/{total_laptop}</div>
            <div class="stat">남은 자유석: {remaining}석</div>
            <div class="updated">업데이트 시각: {now_str}</div>
            <div class="history">
                <h2 style="font-size:1rem; margin-top:1.5rem; color:#444;">📈 최근 자유석 이용 추이</h2>
                <canvas id="seatChart" height="200"></canvas>
                {chart_script}
            </div>
        </div>
    </body>
    </html>
    """
    with open("seat_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
