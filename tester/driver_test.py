from module.set import create_driver  # 이미 작성한 create_driver 함수 불러오기
from selenium.webdriver.common.by import By

try:
    print("🚀 드라이버 실행 테스트 시작...")
    driver = create_driver()

    print("🌐 구글 접속 시도 중...")
    driver.get("https://www.google.com")

    # 검색창이 있는지 확인
    search_box = driver.find_element(By.NAME, "q")
    if search_box:
        print("✅ 크롬 드라이버 테스트 성공: Google 로딩 및 요소 탐지 완료")
    else:
        print("⚠️ 크롬 드라이버는 실행됐지만, 예상한 요소가 없음")

except Exception as e:
    print(f"❌ 테스트 실패: {e}")

finally:
    try:
        driver.quit()
        print("🧹 드라이버 종료 완료")
    except:
        pass