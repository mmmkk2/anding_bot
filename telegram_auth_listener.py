import os
import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import asyncio

# === 환경변수 로드 ===
try:
    load_dotenv("/home/mmkkshim/anding_bot/.env")
except Exception as e:
    print(f"[.env 로드 실패] {e}")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMERGENCY_CHAT_ID = os.getenv("EMERGENCY_CHAT_ID")  # ✅ broadcast용 채팅 ID
AUTH_CODE_PATH = "/home/mmkkshim/anding_bot/auth_code.txt"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.is_bot:
        return

    text = update.message.text
    match = re.search(r"\b(\d{4})\b", text)

    if match:
        code = match.group(1)
        print(f"📥 추출된 인증번호: {code}")

        try:
            with open(AUTH_CODE_PATH, "w") as f:
                f.write(code)
            print(f"✅ {AUTH_CODE_PATH} 저장 완료")
            await update.message.reply_text("✅ 인증번호 저장 완료")
        except Exception as e:
            print(f"❌ 인증번호 저장 실패: {e}")
            await update.message.reply_text("❌ 인증번호 저장 실패")
            return

        if BOT_TOKEN and EMERGENCY_CHAT_ID:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={"chat_id": EMERGENCY_CHAT_ID, "text": f"📲 인증번호 수신: {code}"}
                )
            except Exception as e:
                print(f"[Broadcast 전송 실패] {e}")


async def do_auth_listener():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    await app.run_polling(close_loop=False)


import nest_asyncio

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(do_auth_listener())

