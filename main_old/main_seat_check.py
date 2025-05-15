from module.set import login, find_location, create_driver, send_broadcast_and_update
from module.set import load_flags, save_flags, update_dashboard, send_telegram_and_log



import os
import time
import pickle
import csv
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



# === 설정 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except:
    pass

COOKIE_FILE = os.getenv("COOKIE_FILE") or "log/last_payment_id.pkl"
SEAT_CACHE_FILE = os.getenv("SEAT_CACHE_FILE") or "log/last_seat_state.pkl"
FLAGS_FILE = "log/broadcast_flags.pkl"

FIX_SEATS = int(os.getenv("FIX_SEATS", 5))
LAPTOP_SEATS = int(os.getenv("LAPTOP_SEATS", 6))

BASE_URL = "https://partner.cobopay.co.kr"
SEAT_URL = f"{BASE_URL}/use/seatUse"
TOTAL_FREE_SEATS = 39 - FIX_SEATS - LAPTOP_SEATS

kst = pytz.timezone("Asia/Seoul")

# === 좌석 CSV 기록 ===
def log_seat_status_to_csv(used_free, used_laptop, remaining, available_numbers):
    os.makedirs("log", exist_ok=True)
    log_path = "log/log_seat.csv"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "used_free", "used_laptop", "remaining_free", "available_free_seat_numbers"])
        writer.writerow([now, used_free, used_laptop, remaining, "|".join(map(str, available_numbers))])


def load_last_seat_state():
    try:
        with open("log/last_seat_state.pkl", "rb") as f:
            return pickle.load(f)
    except (EOFError, FileNotFoundError):
        return {}


# === 좌석 상태 체크 ===
def check_seat_status(driver):
    used_free_seats = 0
    used_labtop_seats = 0
    used_fixed_seats = 0
    all_seat_numbers = []

    fixed_seat_numbers = [19, 20, 21, 22, 23, 39]
    laptop_seat_numbers = [34, 35, 36, 37, 38]

    driver.get(SEAT_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))

    flags = load_flags()
    current_time = datetime.now(kst)
    current_date = current_time.strftime("%Y-%m-%d")
    current_hour = current_time.hour

    if flags.get("date") != current_date:
        flags = {"date": current_date, "warn_5": False, "warn_7": False, "recovery": False, "fixed_missing": False}
        save_flags(flags)

    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 3:
                continue

            seat_type = cols[1].text.strip()
            seat_number_text = cols[2].text.strip().replace("\uac1c", "").replace("\ubc88", "").strip()

            try:
                seat_number = int(seat_number_text)
                all_seat_numbers.append(seat_number)
            except:
                continue

            if seat_type == "개인석":
                if seat_number in fixed_seat_numbers:
                    used_fixed_seats += 1
                elif seat_number in laptop_seat_numbers:
                    used_labtop_seats += 1
                else:
                    used_free_seats += 1

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'ul.pagination li.active + li a')
            if "javascript:;" in next_btn.get_attribute("href"):
                break
            next_btn.click()
            time.sleep(1)
        except:
            break

    TOTAL_FREE_SEATS = 39 - len(fixed_seat_numbers) - len(laptop_seat_numbers)
    remaining_seats = TOTAL_FREE_SEATS - used_free_seats
    all_free_seat_numbers = [n for n in range(1, 34) if n not in fixed_seat_numbers and n not in laptop_seat_numbers]
    available_free_seat_numbers = sorted(set(all_free_seat_numbers) - set([n for n in all_seat_numbers if n not in laptop_seat_numbers and n not in fixed_seat_numbers]))

    # === 좌석 색상 상태 정의
    if remaining_seats <= 5:
        status_emoji = "🔴"
    elif remaining_seats <= 7:
        status_emoji = "🟡"
    else:
        status_emoji = "🟢"

    # === 메시지 작성
    msg = (
        f"[좌석 알림] {status_emoji}\n"
        f"자유석 현재 입실: {used_free_seats}/{TOTAL_FREE_SEATS}\n"
        f"노트북석 현재 입실: {used_labtop_seats}/{len(laptop_seat_numbers)}\n"
        f"남은 자유석: {remaining_seats}석"
    )

    # === 항상 대시보드 업데이트
    # update_dashboard("seat", msg)

    # === 변경 체크해서 broadcast
    changed = False
    if os.path.exists(SEAT_CACHE_FILE):
        last_state = load_last_seat_state()

        changed = (
            last_state.get("used_free_seats", -1) != used_free_seats or
            last_state.get("used_labtop_seats", -1) != used_labtop_seats
        )
    else:
        changed = True

    if changed:
        send_broadcast_and_update(msg, broadcast=False,  category="seat")

    # === 주의/경고/복구
    if remaining_seats <= 5 and not flags.get("warn_5"):
        send_broadcast_and_update("[경고] 🚨 자유석 5석 이하 - 일일권 제한 강화 필요", broadcast=True, category="seat")
        flags["warn_5"] = True
    elif remaining_seats <= 7 and not flags.get("warn_7"):
        send_broadcast_and_update("[주의] ⚠️ 자유석 7석 이하 - 이용 주의 필요", broadcast=True, category="seat")
        flags["warn_7"] = True
    elif current_hour >= 20 and remaining_seats >= 10 and not flags.get("recovery"):
        send_broadcast_and_update("[안내] ✅ 자유석 여유 확보 (10석 이상) - 일일권 이용 제한 해제", broadcast=False, category="seat")
        flags["recovery"] = True

    save_flags(flags)

    # === 최종 CSV 로그
    with open(SEAT_CACHE_FILE, "wb") as f:
        pickle.dump({
            "used_free_seats": used_free_seats,
            "used_labtop_seats": used_labtop_seats
        }, f)

    log_seat_status_to_csv(used_free_seats, used_labtop_seats, remaining_seats, available_free_seat_numbers)
    return msg

# === 메인 실행 ===
def main_check_seat(headless=True):
    # ✅ 인증번호 파일 초기화
    if os.path.exists("auth_code.txt"):
        os.remove("auth_code.txt")

    loop_min = 5
    total_loops = 1440 // loop_min
    now = datetime.now()
    minutes_since_midnight = now.hour * 60 + now.minute
    current_loop = (minutes_since_midnight // loop_min) + 1

    location_tag = find_location()
    send_telegram_and_log(f"📢 [좌석 - 모니터링] 시작합니다.")

    driver = create_driver(headless=headless)

    try:
        if login(driver):
            seat_status_msg = check_seat_status(driver)
            now_full_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            loop_msg = (
                f"\n\n🪑 좌석 모니터링 정상 동작 중\n"
                f"Loop {current_loop}/{total_loops}\n"
                f"⏰ 날짜 + 실행 시각: {now_full_str}"
            )
            full_msg = loop_msg + "\n\n" + seat_status_msg
            send_broadcast_and_update(full_msg, broadcast=False, category="seat")

            send_telegram_and_log(f"{location_tag} ✅ [좌석 - 모니터링] 정상 종료되었습니다.")
        else:
            send_broadcast_and_update("❌ [좌석] 로그인 실패", broadcast=False, category="seat")
    except Exception as e:
        send_broadcast_and_update(f"❌ [좌석 오류] {e}", broadcast=False, category="seat")
    finally:
        driver.quit()


from datetime import datetime
import pytz

kst = pytz.timezone("Asia/Seoul")
now = datetime.now(kst)


if __name__ == "__main__":
    # 정오(12시)부터 자정(24시)까지만 실행
    if not (12 <= now.hour < 24):
        print(f"⏹️ 실행 시간 아님 (현재 시각: {now.strftime('%H:%M')}) - 종료")
        exit()
    else:
        main_check_seat(headless=True)
