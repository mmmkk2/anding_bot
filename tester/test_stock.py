# import gspread
# import pandas as pd
# from oauth2client.service_account import ServiceAccountCredentials

# # 1. 구글 시트 인증
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
# client = gspread.authorize(creds)

# # 2. 시트 열기
# sheet = client.open("재고관리시트")  # 문서 이름
# purchase_sheet = sheet.worksheet("구매내역")
# usage_sheet = sheet.worksheet("사용내역")

# # 3. 데이터 프레임 변

# 시트 불러오기

# from openpyxl import load_workbook

# wb = load_workbook("stock_master.xlsx")
# print(wb.sheetnames)  # 시트 목록 확인

# ws = wb["시트이름"]  # 특정 시트 열기
# print(ws["A1"].value)  # A1 셀 값 출력



import pandas as pd

# 모든 시트 불러오기
xls = pd.ExcelFile("stock_master.xlsx")
print(xls.sheet_names)  # 시트 이름 목록 출력

# 특정 시트 불러오기
df = pd.read_excel(xls, sheet_name="Transactions")
print(df.head())




sheet = client.open_by_key(SHEET_KEY).worksheet("구매내역")
df = pd.DataFrame(sheet.get_all_records())
df["날짜"] = pd.to_datetime(df["날짜"])
df = df[["날짜", "품목", "수량"]]

# 품목별 예측 계산
results = []
today = datetime.today()

for item, group in df.groupby("품목"):
   group = group.sort_values("날짜").reset_index(drop=True)

   if len(group) < 2:
       continue  # 예측 불가

   # 최근 2회 구매 정보
   latest = group.iloc[-1]
   previous = group.iloc[-2]

   days_between = (latest["날짜"] - previous["날짜"]).days
   used_quantity = previous["수량"]  # 이전 수량 전부 소진된 것으로 간주

   if days_between == 0 or used_quantity == 0:
       continue

   daily_usage = used_quantity / days_between
   remaining_days = int(latest["수량"] / daily_usage)
   estimated_out_date = latest["날짜"] + timedelta(days=remaining_days)

   results.append({
       "품목": item,
       "최근 구매일": latest["날짜"].date(),
       "최근 수량": latest["수량"],
       "일일 사용량 (최근)": round(daily_usage, 2),
       "예상 소진일": estimated_out_date.date(),
       "남은 일수": remaining_days
   })

# 결과 출력
df_result = pd.DataFrame(results)
print(df_result)