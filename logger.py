# logger.py
# ---------
import re

class Logger:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def safe_log(self, message):
        if self.log_callback:
            try:
                clean_msg = self.clean_for_log(message)
                self.log_callback(clean_msg)
            except Exception as e:
                print("日志错误:", e)

    def clean_for_log(self, text):
        if not text:
            return ""
        text = str(text)
        text = ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
        emoji_pattern = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+", re.UNICODE)
        return emoji_pattern.sub('', text)
