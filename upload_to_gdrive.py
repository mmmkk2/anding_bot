import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

# --- 환경변수 및 설정 ---
SERVICE_ACCOUNT_FILE = "credentials/service_account.json"  # OAuth 2.0 인증 JSON 파일 경로
FOLDER_ID = "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs"  # 업로드할 Google Drive 폴더 ID
LOCAL_SCREENSHOT_DIR = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/") + "/screenshots"

def upload_file(filepath, service):
    filename = os.path.basename(filepath)
    file_metadata = {
        "name": filename,
        "parents": [FOLDER_ID],
    }
    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    print(f"[업로드 완료] {filename} → https://drive.google.com/file/d/{file.get('id')}")

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

    for file in os.listdir(screenshot_folder):
        if file.endswith(".png"):
            upload_file(os.path.join(screenshot_folder, file), service)

if __name__ == "__main__":
    main()