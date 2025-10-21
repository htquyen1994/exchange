import traceback
import datetime
import time
from config.config import TelegramSetting

_last_error_sent = {}

def send_error_telegram(ex, context="", bot=None):
    global _last_error_sent

    if bot is None:
        return

    try:
        error_key = f"{context}:{type(ex).__name__}"
        now = time.time()
        last_sent = _last_error_sent.get(error_key, 0)
        cooldown_seconds = 10 * 60
        if now - last_sent < cooldown_seconds:
            return

        tb = traceback.format_exc()
        telegram_msg = f"""🚨 ERROR ALERT 🚨

Context: {context}
Error Type: {type(ex).__name__}
Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error Message:
{str(ex)}

Traceback:
{tb}"""

        bot.send_message(TelegramSetting.CHAT_ERROR_ID, telegram_msg)
        _last_error_sent[error_key] = now

    except Exception as telegram_ex:
        print("Failed to send telegram:", telegram_ex)

    time.sleep(1)
