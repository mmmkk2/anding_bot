import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import os

# ✅ 폰트 설정
plt.rcParams['font.family'] ='NanumGothicCoding'

# font_path = "/home/mmkkshim/.font/NanumGothicCoding.ttf"
# if os.path.exists(font_path):
#     font_prop = fm.FontProperties(fname=font_path)
#     plt.rcParams['font.family'] = font_prop.get_name()
# else:
#     print("❌ 폰트 파일이 존재하지 않습니다. 기본 폰트로 진행합니다.")
#     font_prop = None

# ✅ 데이터 로딩 및 전처리
xls = pd.ExcelFile("user_2504.xlsx")
df = pd.read_excel(xls, sheet_name="Sheet1")

excluded = [f"{n}번" for n in list(range(19, 24)) + list(range(34, 40))]
df = df.loc[~df['번호'].isin(excluded)]

df['시작시간'] = pd.to_datetime(df['시작시간'], errors='coerce')
df['종료시간'] = pd.to_datetime(df['종료시간'], errors='coerce')
df['날짜'] = df['시작시간'].dt.date

# ✅ 날짜 반복
date_range = pd.date_range("2025-04-01", "2025-04-30", freq='D')
cutoff_count = 20

# ✅ PDF 저장용 객체 생성
with PdfPages("혼잡예측_그래프모음.pdf") as pdf:
    for target_day in date_range:
        start_of_day = target_day + pd.Timedelta(hours=5)
        end_of_day = start_of_day + pd.Timedelta(hours=24)
        cutoff_12 = start_of_day + pd.Timedelta(hours=7)
        cutoff_13 = start_of_day + pd.Timedelta(hours=8)
        cutoff_15 = start_of_day + pd.Timedelta(hours=10)

        # 해당일 데이터 필터링
        day_df = df[(df['시작시간'] < end_of_day) & (df['종료시간'] > start_of_day)]
        if day_df.empty:
            continue

        # ✅ 동시 이용자 수 이벤트
        events = pd.concat([
            day_df[['시작시간']].rename(columns={'시작시간': '시간'}).assign(변화량=1),
            day_df[['종료시간']].rename(columns={'종료시간': '시간'}).assign(변화량=-1)
        ]).sort_values('시간')
        events['동시인원'] = events['변화량'].cumsum()

        # ✅ 누적 유입자 수
        entries = day_df[['시작시간']].rename(columns={'시작시간': '시간'})
        entries['유입'] = 1
        entries = entries.sort_values('시간')
        entries['누적유입자'] = entries['유입'].cumsum()

        # ✅ 그래프 생성
        plt.figure(figsize=(14, 6))
        plt.step(events['시간'], events['동시인원'], where='post', label="동시 이용자 수")
        plt.step(entries['시간'], entries['누적유입자'], where='post', label="누적 유입자 수")

        # 기준 시각선
        for cutoff_time, label in zip([cutoff_12, cutoff_13, cutoff_15], ["12시", "13시", "15시"]):
            plt.axvline(x=cutoff_time, color='gray', linestyle='--', label=f'{label} 기준')

        # 기준 인원선
        plt.axhline(y=25, color='red', linestyle='--', label='혼잡 기준선 (25명)')
        plt.axhline(y=cutoff_count, color='orange', linestyle='--', label=f'예측 기준선 ({cutoff_count}명)')

        plt.title(f"{target_day.date()} | 동시 이용자 + 누적 유입자 비교")
        plt.xlabel("시간")
        plt.ylabel("인원 수")
        plt.xlim(start_of_day, end_of_day)  # ✅ 5시부터 다음날 5시까지만 표시
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        pdf.savefig()
        plt.close()