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

def create_folder(service, name, parent_id=None):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]
    folder = service.files().create(body=file_metadata, fields="id").execute()
    print(f"[폴더 생성 완료] {name} → ID: {folder.get('id')}")
    return folder.get("id")

def upload_file(filepath, service, folder_id, dated_filename):
    base_filename = dated_filename  # dated_filename is now just the filename without prefix
    file_metadata = {
        "name": base_filename,
        "parents": [folder_id],
    }
    media = MediaFileUpload(filepath, resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        print(f"[업로드 완료] {base_filename} → https://drive.google.com/file/d/{file.get('id')}")
    except Exception as e:
        print(f"[업로드 실패] {base_filename}: {e}")

def main():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds)

    ROOT_FOLDER_ID = "1BE8GLf2VrtOxqDvkEY_E2L6GDoZHeMXs"
    created_folder_ids = {}
    for folder_name in ["seat", "main", "payment", "studyroom"]:
        created_folder_ids[folder_name] = create_folder(service, folder_name, ROOT_FOLDER_ID)

    today_str = datetime.now().strftime("%Y-%m-%d")
    screenshot_folder = os.path.join(LOCAL_SCREENSHOT_DIR, today_str)

    if not os.path.exists(screenshot_folder):
        print(f"[오류] 경로 없음: {screenshot_folder}")
        return

    for file in os.listdir(screenshot_folder):
        if file.endswith(".png"):
            prefix = file.split("_")[0]
            folder_id = created_folder_ids.get(prefix)
            if not folder_id:
                print(f"[건너뜀] 알 수 없는 prefix: {prefix}")
                continue
            dated_filename = f"{file.split('.')[0]}_{today_str}.png"
            upload_file(os.path.join(screenshot_folder, file), service, folder_id, dated_filename)

if __name__ == "__main__":
    main()