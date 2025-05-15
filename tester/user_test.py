import matplotlib.pyplot as plt
import pandas as pd

import matplotlib.pyplot as plt


# 예: NanumGothic 폰트 설치되어 있을 경우
plt.rcParams['font.family'] = 'AppleGothic'

# 모든 시트 불러오기
xls = pd.ExcelFile("user_2504.xlsx")
print(xls.sheet_names)  # 시트 이름 목록 출력

# 특정 시트 불러오기
df = pd.read_excel(xls, sheet_name="Sheet1")
print(df.head())

df = df.loc[~df['번호'].isin(['19번', '20번', '21번', '22번', '23번', '34번', '35번', '36번', '37번', '38번', '39번'])]



# 시작시간과 종료시간을 timestamp 형식으로 변환
df['시작시간'] = pd.to_datetime(df['시작시간'], errors='coerce')
df['종료시간'] = pd.to_datetime(df['종료시간'], errors='coerce')


# 날짜 범위 (4/1 ~ 4/30)
date_range = pd.date_range("2025-04-01", "2025-04-30", freq='D')


# 2025-04-01 기준 데이터 준비
target_day = pd.Timestamp("2025-04-01")
start_of_day = target_day + pd.Timedelta(hours=5)
end_of_day = start_of_day + pd.Timedelta(hours=24)
cutoff_13 = start_of_day + pd.Timedelta(hours=8)

# 시간 단위 (분)별 동시 체류 인원 계산
minute_range = pd.date_range(start=start_of_day, end=end_of_day, freq='1min')
minute_counts = []

for t in minute_range:
    concurrent_users = df[(df['시작시간'] <= t) & (df['종료시간'] > t)]['HP'].nunique()
    minute_counts.append(concurrent_users)


# 누적 유입자 수 (시작시간 < 현재 시간인 인원)
cumulative_entries = [df[(df['시작시간'] < t)]['HP'].nunique() for t in minute_range]

# •	주말은 13시 체류자 수 ≥ 20명 조건이 꽤 괜찮은 혼잡 예측 기준
# 15시까지 유입자 수 ≥ 21명

# 그래프 그리기
plt.figure(figsize=(14, 6))
plt.plot(minute_range, minute_counts, label="동시 이용자 수")
plt.plot(minute_range, cumulative_entries, label="누적 유입자 수")
plt.axvline(x=cutoff_13, color='gray', linestyle='--', label='13시 기준')
plt.axhline(y=25, color='red', linestyle='--', label='혼잡 기준선 (25명)')
plt.title("2025-04-01 | 시간별 이용자 비교 (5시~다음날 5시)")
plt.xlabel("시간")
plt.ylabel("인원 수")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
plt.savefig("png/2025-04-01_이용자그래프.png", dpi=300, bbox_inches='tight')  # 고해상도 저장





