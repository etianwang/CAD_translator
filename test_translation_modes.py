import unittest
from types import SimpleNamespace

from main import CADChineseTranslator, output_prefix
from web_api import default_output_name


class TranslationModeTests(unittest.TestCase):
    def test_deepl_language_pairs_and_output_prefixes(self):
        translator = CADChineseTranslator()
        expected = {
            "zh_to_fr": ("zh-cn", "fr", "fr"),
            "fr_to_zh": ("fr", "zh-cn", "zh"),
            "zh_to_en": ("zh-cn", "en-us", "en"),
            "en_to_zh": ("en", "zh-cn", "zh"),
        }
        for mode, (source, target, prefix) in expected.items():
            self.assertEqual((translator.language_configs[mode]["source"], translator.language_configs[mode]["target"]), (source, target))
            self.assertEqual(output_prefix(mode), prefix)
            self.assertTrue(default_output_name(mode, "drawing")["name"].startswith(f"{prefix}_drawing_"))

    def test_chinese_to_english_keeps_deepl_english_variant(self):
        calls = []

        class Translator:
            def translate_text(self, text, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(text="cement structure")

        translator = CADChineseTranslator(log_callback=lambda *args, **kwargs: None)
        translator.deepl_translator = Translator()
        self.assertEqual(translator.translate_text("水泥结构", "zh_to_en"), "cement structure")
        self.assertEqual(calls, [{"source_lang": "ZH", "target_lang": "EN-US"}])

    def test_glossary_bypasses_deepl_for_exact_cad_labels(self):
        class Translator:
            def translate_text(self, *args, **kwargs):
                raise AssertionError("exact glossary entries must not call DeepL")

        translator = CADChineseTranslator(log_callback=lambda *args, **kwargs: None)
        translator.deepl_translator = Translator()
        self.assertEqual(translator.translate_text("天花", "zh_to_fr"), "plafond")
        self.assertEqual(translator.translate_text("PLAFOND", "fr_to_zh"), "天花")
        self.assertEqual(translator.translate_text("剪力墙", "zh_to_fr"), "voile de contreventement")
        self.assertEqual(translator.translate_text("VOILE DE CONTREVENTEMENT", "fr_to_zh"), "剪力墙")
        self.assertEqual(translator.translate_text("LOCAL INFORMATIQUE", "fr_to_zh"), "计算机房")
        self.assertEqual(translator.translate_text("天花图", "zh_to_en"), "reflected ceiling plan")
        self.assertEqual(translator.translate_text("CABLE TRAY", "en_to_zh"), "桥架")


if __name__ == "__main__":
    unittest.main()
