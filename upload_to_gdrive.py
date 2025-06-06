import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

# --- 환경변수 및 설정 ---
SERVICE_ACCOUNT_FILE = "credentials/service_account.json"  # OAuth 2.0 인증 JSON 파일 경로
LOCAL_SCREENSHOT_DIR = os.getenv("DASHBOARD_PATH", "/home/mmkkshim/anding_bot/dashboard_log/") + "/screenshots"

# Google Drive 상의 폴더 ID 목록
FOLDER_IDS = {
    "main": "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs",
    "seat": "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs",
    "payment": "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs",
    "studyroom": "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs",
}

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
    else:
        folder = service.files().create(body=file_metadata, fields="id").execute()
        folder_id = folder.get("id")
        print(f"[폴더 생성 완료] {folder_name} → ID: {folder_id}")

    # 업로드
    for file in os.listdir(screenshot_folder):
        if file.endswith(".html") and file.startswith(folder_name):
            dated_filename = f"{file.split('.')[0]}_{today_str}.html"
            file_metadata = {
                "name": dated_filename,
                "parents": [folder_id],
            }
            media = MediaFileUpload(os.path.join(screenshot_folder, file), resumable=True)
            try:
                uploaded_file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
                print(f"[업로드 완료] {dated_filename} (HTML) → https://drive.google.com/file/d/{uploaded_file.get('id')}")
            except Exception as e:
                print(f"[업로드 실패] {dated_filename} (HTML): {e}")

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

    for folder_name in ["seat", "main", "payment", "studyroom"]:
        create_folder_and_upload_file(service, folder_name, FOLDER_IDS["main"], screenshot_folder, today_str)

if __name__ == "__main__":
    main()