import traceback
import datetime
from config.config import TelegramSetting
from time import sleep

def send_error_telegram(ex, context="", bot=None):
    if bot is None:
        return
    try:
        tb = traceback.format_exc()  # lấy stack trace
        telegram_msg = f"""🚨 ERROR ALERT 🚨

Context: {context}
Error Type: {type(ex).__name__}
Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error Message:
{str(ex)}

Traceback:
{tb}"""
        bot.send_message(TelegramSetting.CHAT_ERROR_ID, telegram_msg)
    except Exception as telegram_ex:
        print("Failed to send telegram: {}".format(str(telegram_ex)))

    sleep(1)