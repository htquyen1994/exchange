import traceback
import datetime
import time

_last_error_sent = {}

def send_error_telegram(ex, context="", bot=None, chat_id=None, error_topic=None):
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

        bot.send_message(chat_id, telegram_msg, message_thread_id=error_topic)
        _last_error_sent[error_key] = now

    except Exception as telegram_ex:
        print("Failed to send telegram:", telegram_ex)

    time.sleep(1)
