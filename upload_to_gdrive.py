import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv

# --- 환경변수 및 설정 ---
SERVICE_ACCOUNT_FILE = "credentials/service_account.json"  # OAuth 2.0 인증 JSON 파일 경로
LOCAL_SCREENSHOT_DIR = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/") + "/screenshots"



# Google Drive 폴더 ID를 동적으로 가져오거나 생성하는 함수
def get_or_create_folder_id(service, folder_name, parent_id):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def create_folder_and_upload_file(service, folder_name, root_folder_id, screenshot_folder, today_str):
    # 폴더 생성
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [root_folder_id],
    }
    # 기존 폴더 확인
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{root_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        folder_id = folders[0]['id']
        print(f"[기존 폴더 존재] {folder_name} → ID: {folder_id}")
        # 폴더 권한 부여
        service.permissions().create(
            fileId=folder_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": "mmkkshim@gmail.com"
            },
            sendNotificationEmail=False
        ).execute()
    else:
        folder = service.files().create(body=file_metadata, fields="id").execute()
        folder_id = folder.get("id")
        print(f"[폴더 생성 완료] {folder_name} → ID: {folder_id}")
        # 폴더 권한 부여
        service.permissions().create(
            fileId=folder_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": "mmkkshim@gmail.com"
            },
            sendNotificationEmail=False
        ).execute()

    print(f"[DEBUG] 업로드 대상 폴더 ID: {folder_id}")
    # 업로드
    for file in os.listdir(screenshot_folder):
        if (
            file.startswith(folder_name)
            and file.endswith((".png", ".csv", ".html"))
        ):
            ext = file.split(".")[-1]
            dated_filename = f"{file.split('.')[0]}_{today_str}.{ext}"
            mime_map = {
                "png": "image/png",
                "csv": "text/csv",
                "html": "text/html",
            }
            file_metadata = {
                "name": dated_filename,
                "parents": [folder_id],
                "mimeType": mime_map.get(ext, "application/octet-stream"),
            }
            media = MediaFileUpload(os.path.join(screenshot_folder, file), resumable=True)
            try:
                uploaded_file = service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ).execute()
                service.permissions().create(
                    fileId=uploaded_file.get("id"),
                    body={"role": "reader", "type": "anyone"},
                ).execute()
                print(
                    f"[업로드 완료] {dated_filename} ({ext.upper()}) → https://drive.google.com/file/d/{uploaded_file.get('id')}"
                )
            except Exception as e:
                print(f"[업로드 실패] {dated_filename}: {e}")





import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/mmkkshim/anding_bot/.env")

try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass


DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/")

LOGIN_ID = os.getenv("LOGIN_ID", "anding_bot")
LOGIN_PWD = os.getenv("LOGIN_PWD", "871104tla#")


BASE_URL = "https://mmkkshim.pythonanywhere.com/"

today_str = (datetime.now() - timedelta(minutes=20)).strftime("%Y-%m-%d")
screenshot_dir = os.path.join(DASHBOARD_PATH, "screenshots", today_str)
os.makedirs(screenshot_dir, exist_ok=True)

import glob
import time

# 오래된 스크린샷 삭제 (1일 이상 지난 파일)
for folder in glob.glob(os.path.join(DASHBOARD_PATH, "screenshots", "*")):
    try:
        if os.path.isdir(folder):
            folder_time = os.path.getmtime(folder)
            if time.time() - folder_time > 86400:  # 1일(60*60*24초)
                import shutil
                shutil.rmtree(folder)
                print(f"[정리] 오래된 폴더 삭제됨: {folder}")
    except Exception as e:
        print(f"[정리 실패] {folder}: {e}")

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    # 그래픽 렌더링 개선
    options.add_argument("--enable-webgl")
    options.add_argument("--ignore-gpu-blocklist")
    options.add_argument("--use-gl=desktop")

    # 언어 및 타임존 설정
    options.add_argument("--lang=ko-KR")
    options.add_argument("--blink-settings=timezone=Asia/Seoul")

    driver = webdriver.Chrome(options=options)
    return driver

def capture_dashboard(name, path, driver):
    url = f"{BASE_URL}/{path}" if path else BASE_URL
    driver.get(url)

    if "login" in driver.current_url:
        print("[INFO] 로그인 필요 - 로그인 시도 중")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        driver.find_element(By.NAME, "username").send_keys(LOGIN_ID)
        driver.find_element(By.NAME, "password").send_keys(LOGIN_PWD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        driver.get(url)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(1)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "canvas, svg, table"))
    )
    time.sleep(2)

    html = driver.page_source
    html_path = os.path.join(screenshot_dir, f"{name}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[완료] HTML 저장됨: {html_path}")

    if name.startswith("seat"):
        screenshot_path = os.path.join(screenshot_dir, f"{name}.png")

        try:
            canvas_data = driver.execute_script("""
                const canvas = document.querySelector("canvas");
                return canvas ? canvas.toDataURL("image/png").substring("data:image/png;base64,".length) : null;
            """)
            if canvas_data:
                import base64
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(canvas_data))
                print(f"[완료] PNG 저장됨 (canvas): {screenshot_path}")
            else:
                raise Exception("canvas 없음")
        except Exception as e:
            print(f"[실패] 캔버스 추출 실패, 일반 스크린샷 시도: {e}")
            driver.save_screenshot(screenshot_path)
            print(f"[완료] PNG 저장됨 (fallback): {screenshot_path}")

    if name.startswith("payment"):
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr") if table else []

        csv_path = os.path.join(screenshot_dir, f"{name}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                writer.writerow(cols)
        print(f"[완료] CSV 저장됨: {csv_path}")

def main():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds)

    today_str = datetime.now().strftime("%Y-%m-%d")
    screenshot_folder = os.path.join(LOCAL_SCREENSHOT_DIR, today_str)

    if not os.path.exists(screenshot_folder):
        print(f"[오류] 경로 없음: {screenshot_folder}")
        return

    capture_targets = {
        "seat": "seat",
        "payment": "payment",
    }

    for name, path in capture_targets.items():
        driver = create_driver()
        try:
            capture_dashboard(f"{name}_dashboard", path, driver)
        finally:
            driver.quit()

        root_folder_id = get_or_create_folder_id(service, "anding-bot", "root")
        create_folder_and_upload_file(service, name, root_folder_id, screenshot_folder, today_str)

if __name__ == "__main__":
    main()