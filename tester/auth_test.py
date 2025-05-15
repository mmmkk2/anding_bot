import os
import asyncio
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from set import login, create_driver  # 필요한 함수만 임포트

# === 환경변수 로드 ===
try:
    load_dotenv("/home/mmkkshim/anding-study-bot/.env")
except Exception as e:
    print(f"[.env 로드 실패] {e}")

# === 외부 IP 출력 ===
ip = requests.get("https://api.ipify.org").text
print(f"현재 외부 IP 주소: {ip}")

# === 드라이버 생성 및 로그인 테스트 ===
driver = create_driver()  # headless 모드 권장

try:
    result = login(driver)
    print("✅ 로그인 결과:", result)
except Exception as e:
    print(f"❌ 로그인 중 오류 발생: {e}")
finally:
    driver.quit()