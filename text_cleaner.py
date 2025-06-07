class TextCleaner:
    def clean_and_utf8_safe(self, text):
        """清洗代理字符并确保可以 UTF-8 编码"""
        if not text:
            return ''
        try:
            # 清理掉所有代理字符（即高低代理对）
            text = ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
            text = text.encode('utf-8', 'ignore').decode('utf-8')
        except UnicodeEncodeError as e:
            print(f"清理失败: {e}")
            text = f"[清理失败:{e}]"
        return text

    def remove_surrogates_and_invalid_chars(self, text):
        """移除无效字符，确保文本可以正常编码"""
        if not text:
            return ""
        return ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
