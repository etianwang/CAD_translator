from googletrans import Translator as GoogleTranslator
import deepl

class Translator:
    def __init__(self, engine='google', deepl_api_key=None):
        self.engine = engine
        self.deepl_api_key = deepl_api_key

    def translate_text(self, text, source_lang, target_lang):
        """根据翻译引擎进行文本翻译"""
        if self.engine == 'google':
            return self.translate_with_google(text, source_lang, target_lang)
        elif self.engine == 'deepl':
            return self.translate_with_deepl(text, source_lang, target_lang)
        return text  # 默认返回原文

    def translate_with_google(self, text, source_lang, target_lang):
        """使用 Google 翻译引擎翻译"""
        translator = GoogleTranslator()
        translated = translator.translate(text, src=source_lang, dest=target_lang)
        return translated.text

    def translate_with_deepl(self, text, source_lang, target_lang):
        """使用 DeepL 翻译引擎翻译"""
        if not self.deepl_api_key:
            raise Exception("DeepL API key 未设置")
        translator = deepl.Translator(self.deepl_api_key)
        result = translator.translate_text(text, source_lang=source_lang, target_lang=target_lang)
        return result.text
