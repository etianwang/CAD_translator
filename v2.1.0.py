import ezdxf
import re
import time
import os
import shutil
import csv
from pathlib import Path
from googletrans import Translator
import deepl
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from datetime import datetime
import os
import sys
import urllib.request
import unicodedata
import json
import winreg

def get_installed_fonts():
    fonts = set()
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            for i in range(0, winreg.QueryInfoKey(key)[1]):
                name, _, _ = winreg.EnumValue(key, i)
                fonts.add(name.split(" (")[0].strip())
    except Exception as e:
        print(f"获取字体失败: {e}")
    return fonts
preferred_fonts = [
    "SimSun",        # 宋体，Win默认有
    "Microsoft YaHei",  # 微软雅黑，清晰
    "SimHei",        # 黑体
    "Arial Unicode MS", # 英文+中文兼容
    "Arial",
    "Tahoma",
]

def pick_available_font():
    installed_fonts = get_installed_fonts()
    for font in preferred_fonts:
        if font in installed_fonts:
            return font
    return "Arial"  # 默认 fallback


CONFIG_PATH = os.path.expanduser("~/.cad_translator_config.json")

def resource_path(relative_path):
    """返回资源文件的正确路径（兼容 .py 和 .exe）"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 临时目录
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class CADChineseTranslator:
    @staticmethod
    def contains_surrogates(text):
        """检测是否包含 Unicode surrogate（代理）字符"""
        return any(0xD800 <= ord(c) <= 0xDFFF for c in text)
    
    def __init__(self, log_callback=None):
        self.translator = Translator()
        self.translated_cache = {}
        self.default_font = pick_available_font()
        self.log_callback = log_callback
        self.use_engine = 'google'  # 默认引擎，可选：'google'、'deepl'、'chatgpt'
        self.deepl_api_key = os.environ.get("DEEPL_API_KEY")  # 或你手动赋值
        self.deepl_translator = None
        if self.deepl_api_key:
            try:
                self.deepl_translator = deepl.Translator(self.deepl_api_key)
                self.safe_log(" DeepL 引擎已就绪")
            except Exception as e:
                self.safe_log(f" 初始化 DeepL 失败: {e}")
        # 语言配置 - 只保留中法互译
        self.language_configs = {
            'zh_to_fr': {
                'source': 'zh-cn',
                'target': 'fr',
                'name': '中文→法语',
                'context': self.get_architectural_context_fr()
            },
            'fr_to_zh': {
                'source': 'fr',
                'target': 'zh-cn',
                'name': '法语→中文',
                'context': self.get_architectural_context_zh()
            }
        }
        self.chatgpt_api_key = None  # placeholder
        # 如果传入了 deepl_key 后初始化 translator：
        if self.deepl_api_key:
            try:
                self.deepl_translator = deepl.Translator(self.deepl_api_key)
                self.safe_log("✅ DeepL 引擎初始化成功")
            except Exception as e:
                self.safe_log(f" DeepL 初始化失败: {e}")
    @property
    def deepl_api_key(self):
        return self._deepl_api_key

    @deepl_api_key.setter
    def deepl_api_key(self, value):
        self._deepl_api_key = value
        if value:
            try:
                import deepl
                self.deepl_translator = deepl.Translator(value)
            except Exception as e:
                self.safe_log(f" DeepL 初始化失败: {e}")    

    def get_architectural_context_fr(self):
        """建筑术语上下文 - 法语"""
        return {
            '天花': 'plafond',
            '吊顶': 'faux plafond',
            '地面': 'sol',
            '墙面': 'mur',
            '卫生间': 'salle de bain',  
            '厨房': 'cuisine',
            '门窗': 'portes et fenêtres',
            '入口': 'entrée',
            '出口': 'sortie',
            '走廊': 'couloir',
            '楼梯': 'escalier',
            '电梯': 'ascenseur',
            '照明': 'éclairage',
            '插座': 'prise',
            '开关': 'interrupteur',
            '强电': 'courant fort',
            '弱电': 'courant faible',
            '监控': 'vidéosurveillance',
            '消防': 'sécurité incendie',
            '报警': 'alarme',
            '空调': 'climatisation',
            '新风': 'ventilation',
            '排风': "extraction d'air",
            '排烟': 'évacuation fumée',
            '风口': "grille d'air",
            '出风口': 'bouche de soufflage',
            '回风口': 'bouche de reprise',
            '风管': "conduite d'air",
            '风机': 'ventilateur',
            '风机盘管': 'ventilo-convecteur',
            '新风机': 'unité de ventilation',
            '冷却塔': 'tour de refroidissement',
            '空调机': 'unité de climatisation',
            '冷热水': 'eau chaude et froide',
            '排水管': "évacuation d'eau",
            '冷凝水管': 'conduite de condensat',
            '水管': "conduite d'eau",
            '配电箱': 'tableau de distribution',
            '桥架': 'chemin de câbles',
            '管道井': 'gaine technique',
            '设备间': 'local technique',
            '机房': 'local des machines',
            '天花图': 'plan de plafond',
            '控制屏': 'écran de contrôle',
            '屏幕': 'écran',
            '控制': 'contrôle',
        }
    
    def get_architectural_context_zh(self):
        """建筑术语上下文 - 中文（用于反向翻译）"""
        return {
            'plafond': '天花',
            'faux plafond': '吊顶', 
            'sol': '地面',
            'mur': '墙面',
            'salle de bain': '卫生间',
            'cuisine': '厨房',
            'entrée': '入口',
            'sortie': '出口',
            'couloir': '走廊',
            'escalier': '楼梯',
            'ascenseur': '电梯',
            'éclairage': '照明',
            'prise': '插座',
            'interrupteur': '开关',
            'climatisation': '空调',
            'ventilation': '新风',
            'écran de contrôle': '控制屏',
            'écran': '屏幕',
            'contrôle': '控制',
            'courant fort': '强电',
            'courant faible': '弱电',
            'vidéosurveillance': '监控',
            'sécurité incendie': '消防',
            'alarme': '报警',
            "extraction d'air": '排风',
            'évacuation fumée': '排烟',
            "grille d'air": '风口',
            'bouche de soufflage': '出风口',
            'bouche de reprise': '回风口',
            "conduite d'air": '风管',
            'ventilateur': '风机',
            'ventilo-convecteur': '风机盘管',
            'unité de ventilation': '新风机',
            'tour de refroidissement': '冷却塔',
            'unité de climatisation': '空调机',
            'eau chaude et froide': '冷热水',
            "évacuation d'eau": '排水管',
            'conduite de condensat': '冷凝水管',
            "conduite d'eau": '水管',
            'tableau de distribution': '配电箱',
            'chemin de câbles': '桥架',
            'gaine technique': '管道井',
            'local technique': '设备间',
            'local des machines': '机房',
            'plan de plafond': '天花图',
            'portes et fenêtres': '门窗',
            'plan': '平面图',
            'shema': '示意图',
        }
    def preprocess_abbreviations(self, text, lang_config_key):
        """在翻译前处理常见缩写，例如 W:800mm → 宽度:800mm，W400*H650 → 宽度400×高度650"""
        if not text or not isinstance(text, str):
            return text

        if lang_config_key == 'fr_to_zh':
            # 缩写映射
            abbrev_map = {
                'W': '宽度',
                'H': '高度',
                'D': '深度',
                'L': '长度',
                'B1': '负一楼',
                'B2': '负二楼',
                'B3': '负三楼',
                'F1': '一楼',
                'F2': '二楼',
                'F3': '三楼',
                'F4': '四楼',
                'RDC': '底层',
                'SSL': '地下室',
                'SS1': '地下室一层',
                'SS2': '地下室二层',
                'R+1': '二层',
                'R+2': '三层',
                'R+3': '四层',
                'plan': '平面图',
                'shema': '示意图',
            }

            # 处理纯楼层标识 B2 → 负二楼
            if text.strip().upper() in abbrev_map:
                return abbrev_map[text.strip().upper()]

            # 处理类似 W:800mm 格式
            pattern = re.compile(r'\b([WHDL])\s*[:：]\s*(\d+\.?\d*\s*(?:mm|cm|m)?)', re.IGNORECASE)
            text = pattern.sub(lambda m: f"{abbrev_map.get(m.group(1).upper(), m.group(1))}:{m.group(2)}", text)

            # 处理类似 W400*H650 或 H650*W400 格式
            pattern_pair = re.compile(r'\b([WHDL])\s*(\d+)\s*[*×x]\s*([WHDL])\s*(\d+)', re.IGNORECASE)
            def replace_pair(match):
                key1 = match.group(1).upper()
                val1 = match.group(2)
                key2 = match.group(3).upper()
                val2 = match.group(4)
                name1 = abbrev_map.get(key1, key1)
                name2 = abbrev_map.get(key2, key2)
                return f"{name1}{val1}×{name2}{val2}"

            text = pattern_pair.sub(replace_pair, text)

        return text


    def log(self, message):
        """发送日志消息到GUI"""
        if self.log_callback:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_callback(f"[{timestamp}] {message}")

    def is_valid_unicode_char(self, char):
        """检查字符是否为有效的Unicode字符"""
        try:
            # 检查是否为控制字符或未定义字符
            if unicodedata.category(char) in ['Cc', 'Cf', 'Cn', 'Co', 'Cs']:
                return False
            # 检查是否为代理字符（这是最重要的检查）
            code_point = ord(char)
            if 0xD800 <= code_point <= 0xDFFF:
                self.safe_log(f"检测到代理字符: U+{code_point:04X}")
                return False
            # 检查是否为私有使用区字符
            if 0xE000 <= code_point <= 0xF8FF:
                return False
            # 检查是否为特定的问题字符
            problematic_chars = {
                '\u07B0',  # ް (Thaana letter Dhadalu)
                '\u0780',  # ޠ (Thaana letter Haa)
                '\uFFFD',  # � (replacement character)
            }
            if char in problematic_chars:
                return False
            return True
        except Exception as e:
            self.safe_log(f"字符验证异常: {e}")
            return False

    def remove_surrogates_and_invalid_chars(self, text):
        """专门清理代理字符和无效字符"""
        if not text:
            return ""
        
        cleaned_chars = []
        removed_count = 0
        
        i = 0
        while i < len(text):
            char = text[i]
            code_point = ord(char)
            
            # 检查是否为代理字符
            if 0xD800 <= code_point <= 0xDFFF:
                removed_count += 1
                self.safe_log(f"移除代理字符: U+{code_point:04X} 在位置 {i}")
                i += 1
                continue
            
            # 检查是否为其他无效字符
            if not self.is_valid_unicode_char(char):
                removed_count += 1
                self.safe_log(f"移除无效字符: '{char}' (U+{code_point:04X}) 在位置 {i}")
                i += 1
                continue
            
            # 字符有效，保留
            cleaned_chars.append(char)
            i += 1
        
        cleaned_text = ''.join(cleaned_chars)
        
        if removed_count > 0:
            self.safe_log(f"字符清理完成: 移除了 {removed_count} 个无效字符")
            self.safe_log(f"原始文本长度: {len(text)}, 清理后长度: {len(cleaned_text)}")
        
        return cleaned_text

    def safe_utf8_encode(self, text):
        """安全的UTF-8编码，避免代理字符错误"""
        if not text:
            return ""
        
        try:
            # 首先清理代理字符
            cleaned_text = self.remove_surrogates_and_invalid_chars(text)
            
            # 尝试编码测试
            cleaned_text.encode('utf-8')
            return cleaned_text
        except UnicodeEncodeError as e:
            self.safe_log(f"UTF-8编码错误: {e}")
            # 如果仍然有问题，使用更激进的清理
            safe_chars = []
            for char in text:
                try:
                    char.encode('utf-8')
                    if self.is_valid_unicode_char(char):
                        safe_chars.append(char)
                except UnicodeEncodeError:
                    self.safe_log(f"跳过无法编码的字符: '{char}' (U+{ord(char):04X})")
                    continue
            
            result = ''.join(safe_chars)
            self.safe_log(f"激进清理完成: {len(text)} -> {len(result)} 字符")
            return result

    def detect_and_fix_encoding_issues(self, text):
        """检测并修复编码问题"""
        if not text:
            return ""
        
        # 常见的错误编码模式修复
        encoding_fixes = {
            # 法语特殊字符的错误编码修复
            '\\xc9': 'É',    # É的错误编码
            '\\xe9': 'é',    # é的错误编码
            '\\xe8': 'è',    # è的错误编码
            '\\xea': 'ê',    # ê的错误编码
            '\\xf4': 'ô',    # ô的错误编码
            '\\xe0': 'à',    # à的错误编码
            '\\xe7': 'ç',    # ç的错误编码
            '\\xf9': 'ù',    # ù的错误编码
            '\\xfb': 'û',    # û的错误编码
            '\\xee': 'î',    # î的错误编码
            # 常见的编码错误模式
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã ': 'à',
            'Ã§': 'ç',
            'Ã´': 'ô',
            'Ã®': 'î',
            'Ã¹': 'ù',
            'Ã»': 'û',
            'Ã‰': 'É',
        }
        
        # 应用编码修复
        fixed_text = text
        for wrong, correct in encoding_fixes.items():
            fixed_text = fixed_text.replace(wrong, correct)
        
        return fixed_text

    def decode_text_safely(self, text):
        """安全解码文本，处理各种编码问题"""
        if not text:
            return ""
        
        # 如果已经是字符串，处理可能的编码问题
        if isinstance(text, str):
            # 首先尝试修复已知的编码问题
            text = self.detect_and_fix_encoding_issues(text)
            
            # 强制清理代理字符和无效字符
            cleaned_text = self.remove_surrogates_and_invalid_chars(text)
            
            # 检查是否包含编码转义序列
            if '\\x' in cleaned_text:
                try:
                    # 尝试解码转义序列
                    decoded = cleaned_text.encode('latin1').decode('utf-8')
                    # 再次清理解码结果
                    return self.remove_surrogates_and_invalid_chars(decoded)
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        # 尝试其他编码
                        decoded = cleaned_text.encode('latin1').decode('cp1252')
                        return self.remove_surrogates_and_invalid_chars(decoded)
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # 如果都失败了，返回清理后的文本
                        return cleaned_text
            
            return cleaned_text
        
        # 如果是字节类型
        if isinstance(text, bytes):
            encodings = ['utf-8', 'gbk', 'gb2312', 'cp1252', 'latin1']
            for encoding in encodings:
                try:
                    decoded = text.decode(encoding)
                    # 清理解码结果中的代理字符
                    cleaned_text = self.remove_surrogates_and_invalid_chars(decoded)
                    if cleaned_text:  # 如果清理后还有内容，说明解码成功
                        return self.detect_and_fix_encoding_issues(cleaned_text)
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用错误替换
            decoded = text.decode('utf-8', errors='replace')
            # 移除替换字符并清理
            cleaned = self.remove_surrogates_and_invalid_chars(decoded)
            # 移除替换字符 \ufffd
            cleaned = cleaned.replace('\ufffd', '')
            return self.detect_and_fix_encoding_issues(cleaned)
        
        return str(text)

    def encode_text_safely(self, text):
        """安全编码文本用于写回CAD"""
        if not text:
            return ""
        
        # 确保文本是正确的Unicode字符串
        text = self.decode_text_safely(text)
        
        # 使用安全的UTF-8编码
        return self.safe_utf8_encode(text)

    def clean_text(self, text):
        if not text:
            return ""
        try:
            # 先安全解码
            text = self.decode_text_safely(text)
            
            # 清理CAD格式代码
            text = re.sub(r'\\[fFcCpPhHwWqQaA][^;]*;?', '', text)
            text = re.sub(r'\\{[^}]*}', '', text)
            text = re.sub(r'\\[nNtT]', ' ', text)
            text = re.sub(r'\\\\', r'\\', text)
            return re.sub(r'\s+', ' ', text).strip()
        except Exception as e:
            self.safe_log(f"清理失败: {e}")
            return self.decode_text_safely(text).strip()

    def get_contextual_translation(self, text, lang_config_key):
        """根据语言配置获取上下文翻译提示"""
        if lang_config_key not in self.language_configs:
            return text
            
        context_dict = self.language_configs[lang_config_key]['context']
        hints = [f"{term}={trans}" for term, trans in context_dict.items() if term in text]
        return f"建筑术语: {'; '.join(hints[:3])}. 原文: {text}" if hints else text

    def post_process_translation(self, text, original, lang_config_key):
        if '建筑术语:' in text and '原文:' in text:
            text = text.split('原文:')[-1].strip()
        text = re.sub(r'.*术语[：:][^.]*\.\s*', '', text)

        # 根据目标语言设置不同的修正规则
        if lang_config_key == 'zh_to_fr':
            corrections = {
                'variole': 'plafond',
                'virus du plafond': 'plafond',
                'maladie du plafond': 'plafond',
                'plan de variole': 'plan de plafond',
                'fleur de plafond': 'plafond',
                'toilettes salle de bain': 'salle de bain',
                'cuisine cuisine': 'cuisine',
                'écran de contrôle': 'écran de contrôle',
                'contrôle': 'contrôle',
            }
        else:
            corrections = {}

        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        return re.sub(r'\s+', ' ', text).strip()
        if lang_config_key == 'fr_to_zh':
            corrections.update({
                'W': '宽度',
                'H': '高度',
                'D': '深度',
                'B1': '负一楼',
                'B2': '负二楼',
                'B3': '负三楼',
                'F1': '一楼',
                'F2': '二楼',
                'F3': '三楼',
                'F4': '四楼',
                'F5': '五楼',
                'F6': '六楼',
                'F7': '七楼',
                'F8': '八楼',
                'RDC': '底层',
                'R+1': '一层',
                'R+2': '二层',
                'R+3': '三层',
                'R+4': '四层',
                'R+5': '五层',
                'R+6': '六层',
                'SSL': '地下室',
                'SS1': '地下室一层',
                'SS2': '地下室二层',
                'SS3': '地下室三层',
                'SS4': '地下室四层',
            })

            # 替换缩写 - 仅当它是独立词
            for abbr, full in corrections.items():
                text = re.sub(rf'\b{re.escape(abbr)}\b', full, text)

    def translate_text(self, text, lang_config_key):
        if not text or not lang_config_key:
            return text
        if text in self.translated_cache:
            return self.translated_cache[text]
        elif self.use_engine == 'deepl':
            if not self.deepl_translator:
                raise Exception(f"未正确配置 DeepL API Key 或初始化失败")


        decoded_text = self.decode_text_safely(text)
        cleaned = self.clean_text(decoded_text)
        cleaned = self.safe_utf8_encode(cleaned)

        if not cleaned.strip():
            self.safe_log(f"跳过空文本或无效文本: \"{text}\"")
            return self.encode_text_safely(decoded_text)

        try:
            cleaned.encode('utf-8')
        except UnicodeEncodeError as e:
            self.safe_log(f"跳过包含编码问题的文本: \"{text}\" - 错误: {e}")
            return self.encode_text_safely(decoded_text)

        if re.fullmatch(r'[\d\.\{\}\[\]\(\)\-_/\\]+', cleaned.strip()):
            self.safe_log(f"跳过编号/符号内容（无需翻译）: \"{cleaned}\"")
            self.translated_cache[text] = cleaned
            return self.encode_text_safely(cleaned)

        cleaned = self.preprocess_abbreviations(cleaned, lang_config_key)
        cleaned = self.safe_utf8_encode(cleaned)

        if lang_config_key == "zh_to_fr" and not re.search(r'[\u4e00-\u9fff]', cleaned):
            self.safe_log(f"跳过非中文内容（疑似编号）: \"{cleaned}\"")
            return self.encode_text_safely(decoded_text)

        printable_chars = sum(1 for char in cleaned if char.isprintable() or '\u4e00' <= char <= '\u9fff')
        if len(cleaned) > 0 and printable_chars / len(cleaned) < 0.5:
            self.safe_log(f"跳过损坏文本(可读字符比例过低): \"{cleaned}\"")
            return self.encode_text_safely(decoded_text)

        if lang_config_key not in self.language_configs:
            self.safe_log(f"无效的翻译配置: {lang_config_key}")
            return self.encode_text_safely(decoded_text)

        lang_config = self.language_configs[lang_config_key]

        try:
            context = self.get_contextual_translation(cleaned, lang_config_key)
            self.safe_log(f"翻译中 ({lang_config['name']}): {cleaned}")
            if context != cleaned:
                self.safe_log(f"提示术语: {context}")

            # 翻译逻辑
            translated_result = ""
            if self.use_engine == 'google':
                result = self.translator.translate(cleaned, src=lang_config['source'], dest=lang_config['target'])
                translated_result = result.text
            elif self.use_engine == 'deepl':
                if not self.deepl_translator:
                    raise Exception("未正确配置 DeepL API Key 或初始化失败")
                try:
                    deepl_result = self.deepl_translator.translate_text(
                        cleaned,
                        source_lang=lang_config['source'].split('-')[0].upper(),
                        target_lang=lang_config['target'].split('-')[0].upper()
                    )
                    translated_result = deepl_result.text
                except Exception as e:
                    raise Exception(f"DeepL 翻译接口调用失败: {e}")
            elif self.use_engine == 'chatgpt':
                translated_result = f"(ChatGPT翻译模拟): {cleaned}"
            else:
                raise Exception("未配置可用的翻译引擎")

            # ✅ 翻译后清洗与检查
            if self.contains_surrogates(translated_result):
                self.safe_log(f"⚠️ 翻译结果含非法字符，已自动清除: {repr(translated_result)}")
                translated_result = self.remove_surrogates_and_invalid_chars(translated_result)

            final = self.post_process_translation(translated_result, cleaned, lang_config_key)
            final = self.encode_text_safely(final)
            final = self.remove_surrogates_and_invalid_chars(final)
            final = self.safe_utf8_encode(final)




            self.translated_cache[text] = final
            self.safe_log(f"✔ 翻译完成 ({self.use_engine}): \"{cleaned}\" → \"{final}\"")
            time.sleep(0.5)
            return final

        except Exception as e:
            self.safe_log(f"翻译失败 ({self.use_engine}): {e} → 原文: \"{cleaned}\"")
            return self.encode_text_safely(text)


    def extract_text_entities(self, doc, lang_config, include_blocks=False):
        """提取所有文本实体，增强编码检查"""
        items = []
        # 处理模型空间和布局空间
        for space in [doc.modelspace()] + list(doc.layouts):
            for e in space:
                if e.dxftype() in ['TEXT', 'MTEXT']:
                    txt = self.get_entity_text(e)
                    if txt and self.is_valid_text_for_translation(txt):
                        items.append({
                            'entity': e,
                            'original_text': txt,
                            'layer': getattr(e.dxf, 'layer', 'DEFAULT'),
                            'location': space.name if hasattr(space, 'name') else 'modelspace'
                        })

        # 根据选项决定是否处理块内文字
        if include_blocks:
            self.safe_log("选择翻译块内文字，正在处理块...")
            for block in doc.blocks:
                if block.name.startswith('*'):
                    continue
                for e in block:
                    if e.dxftype() in ['TEXT', 'MTEXT']:
                        txt = self.get_entity_text(e)
                        if txt and self.is_valid_text_for_translation(txt):
                            items.append({
                                'entity': e,
                                'original_text': txt,
                                'layer': getattr(e.dxf, 'layer', 'DEFAULT'),
                                'location': f'block:{block.name}'
                            })
        else:
            self.safe_log("跳过块内文字翻译（推荐设置）")

        self.safe_log(f"提取文本实体: {len(items)} 条 {'(包含块内文字)' if include_blocks else '(不包含块内文字)'}")
        return items

    def is_valid_text_for_translation(self, text):
        """检查文本是否适合翻译（增强编码检查）"""
        if not text or not text.strip():
            return False
        
        # 解码并清理文本
        decoded = self.decode_text_safely(text)
        cleaned = self.clean_text(decoded)
        
        if not cleaned or len(cleaned.strip()) < 1:
            return False
        
        # 检查是否包含过多无效字符
        invalid_chars = sum(1 for char in cleaned if not self.is_valid_unicode_char(char))
        if invalid_chars > 0:
            self.safe_log(f"发现包含{invalid_chars}个无效字符的文本，已跳过: \"{text[:20]}...\"")
            return False
        
        # 计算可读字符比例
        printable_chars = sum(1 for char in cleaned if (
            char.isprintable() or 
            char.isspace() or 
            '\u4e00' <= char <= '\u9fff' or  # 中文
            '\u3000' <= char <= '\u303f'     # 中文符号
        ))
        
        # 如果可读字符比例太低，认为是损坏的文本
        if len(cleaned) > 0 and printable_chars / len(cleaned) < 0.8:  # 提高阈值
            return False
        
        return True

    def get_entity_text(self, entity):
        try:
            if hasattr(entity.dxf, 'text'):
                text = entity.dxf.text
            elif hasattr(entity, 'text'):
                text = entity.text
            else:
                return ""
            
            # 安全解码获取的文本
            decoded = self.decode_text_safely(text)
            
            # 如果解码后为空或无效，记录警告
            if not decoded or decoded != text:
                self.safe_log(f"文本解码修复: \"{text}\" → \"{decoded}\"")
            
            return decoded
        except Exception as e:
            self.safe_log(f"获取文本失败: {e}")
            return ""

    def write_back_translation(self, entity, new_text):
        try:
            self.safe_log(f"准备写入文本: {repr(new_text)}")
            self.safe_log(f"是否包含代理字符: {any(0xD800 <= ord(c) <= 0xDFFF for c in new_text)}")

            cleaned_text = self.remove_surrogates_and_invalid_chars(new_text)
            cleaned_text = self.encode_text_safely(cleaned_text)
            cleaned_text = self.safe_utf8_encode(cleaned_text)

            if entity.dxftype() == "TEXT":
                entity.dxf.text = cleaned_text

            elif entity.dxftype() == "MTEXT":
                # 动态插入默认字体（来自系统检测）
                font = getattr(self, 'default_font', 'SimSun')
                formatted = fr"{{\f{font}|b0|i0|c134;{cleaned_text}}}"
                entity.text = formatted
                entity.dxf.text = formatted

            else:
                self.safe_log(f"⚠️ 未知实体类型: {entity.dxftype()}，无法写入文本")

        except Exception as e:
            self.safe_log(f"写回失败: {e}")

    def create_report(self, items, output_csv):
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['layer', 'location', 'original_text', 'translated_text'])
            writer.writeheader()
            for item in items:
                writer.writerow({
                    'layer': item['layer'],
                    'location': item['location'],
                    'original_text': self.decode_text_safely(item['original_text']),
                    'translated_text': self.decode_text_safely(item.get('translated_text', ''))
                })

    def translate_cad_file(self, input_file, output_file, lang_config, include_blocks=False):
        self.safe_log(f"正在读取: {input_file}")
        self.safe_log(f"当前写入字体: {self.default_font}")
        # 尝试不同的编码方式读取文件
        doc = None
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                self.safe_log(f"尝试使用 {encoding} 编码读取文件...")
                doc = ezdxf.readfile(input_file, encoding=encoding)
                self.safe_log(f"成功使用 {encoding} 编码读取文件")
                break
            except Exception as e:
                self.safe_log(f"使用 {encoding} 编码失败: {e}")
        
        if doc is None:
            raise Exception("无法使用任何编码方式读取DXF文件")
        # ✅ 在提取之前清理一次（防止含非法字符的实体阻断提取）
        self.clean_all_entities(doc)


        # ✅ 然后提取文本进行翻译
        items = self.extract_text_entities(doc, lang_config, include_blocks)

        # ✅ 放到此处：确保 doc 已成功读取后再进行代理字符检查
        for e in doc.modelspace():
            if e.dxftype() in ['TEXT', 'MTEXT']:
                content = getattr(e.dxf, 'text', '') or getattr(e, 'text', '')
                if any(0xD800 <= ord(c) <= 0xDFFF for c in content):
                    self.safe_log(f"⚠️ 最终写入前仍检测到代理字符: {repr(content)}")

        if lang_config and lang_config in self.language_configs:
            config_name = self.language_configs[lang_config]['name']
            self.safe_log(f"翻译模式: {config_name}")

        total_items = len(items)
        successful_translations = 0
        skipped_invalid = 0

        for i, item in enumerate(items, 1):
            original_text = item['original_text']

            if not self.is_valid_text_for_translation(original_text):
                skipped_invalid += 1
                self.safe_log(f"跳过无效文本 ({i}/{total_items}): \"{original_text[:30]}...\"")
                item['translated_text'] = original_text
                continue

            translated = self.translate_text(original_text, lang_config)
            item['translated_text'] = translated

            if translated != original_text:
                self.write_back_translation(item['entity'], translated)
                successful_translations += 1

            self.safe_log(f"进度: {i}/{total_items} ({i/total_items*100:.1f}%)")
        # ⚠️ 保存前强制清理所有残留代理字符
        self.safe_log("💡 最终保存前，强制清理所有文本实体中的非法字符")

        def clean_entities(container, label="modelspace"):
            for e in container:
                if e.dxftype() in ['TEXT', 'MTEXT', 'ATTDEF', 'ATTRIB', 'DIMENSION']:  # 全部纳入处理
                    raw_text = getattr(e.dxf, 'text', '') or getattr(e, 'text', '')
                    if raw_text:
                        cleaned = self.remove_surrogates_and_invalid_chars(raw_text)
                        if cleaned != raw_text:
                            self.safe_log(f"⚠️ 清理后替换文本 ({label}): '{raw_text[:30]}' → '{cleaned[:30]}'")
                            try:
                                if hasattr(e.dxf, 'text'):
                                    e.dxf.text = cleaned
                                elif hasattr(e, 'text'):
                                    e.text = cleaned
                            except Exception as ee:
                                self.safe_log(f"⚠️ 写回失败 ({label}): {ee}")

        # 清理 modelspace
        clean_entities(doc.modelspace(), "modelspace")

        # 清理 layouts（paper space 等）
        for layout in doc.layouts:
            clean_entities(layout, f"layout:{layout.name}")

        # 清理 blocks（即使你没翻译 block，也要防止残留非法字符）
        for block in doc.blocks:
            clean_entities(block, f"block:{block.name}")
            # ✅ 翻译后再次清理（防止翻译引擎返回代理字符）
        self.clean_all_entities(doc)
        try:
            doc.saveas(output_file, encoding='utf-8')
            self.safe_log(f"✅ 文件成功保存: {output_file}")
        except UnicodeEncodeError as e:
            self.safe_log(f" 文件保存失败: {e}")
            messagebox.showerror("保存失败", f"文件保存出错：\n{e}")

        report_file = output_file.replace('.dxf', '_report.csv')
        self.create_report(items, report_file)
        self.safe_log(f"翻译报告保存: {report_file}")
        self.safe_log(f"翻译完成！共处理 {total_items} 个文本对象")
        self.safe_log(f"成功翻译: {successful_translations} 个，跳过无效文本: {skipped_invalid} 个")
    def clean_all_entities(self, doc):
        self.safe_log("💡 清理所有实体中的非法字符")

        def clean_container(container, label):
            for e in container:
                if e.dxftype() in ['TEXT', 'MTEXT', 'ATTDEF', 'ATTRIB', 'DIMENSION']:
                    raw = getattr(e.dxf, 'text', '') or getattr(e, 'text', '')
                    if raw and any(0xD800 <= ord(c) <= 0xDFFF for c in raw):
                        cleaned = self.remove_surrogates_and_invalid_chars(raw)
                        if cleaned != raw:
                            self.safe_log(f"⚠️ 清理后替换文本 ({label}): '{raw[:30]}' → '{cleaned[:30]}'")
                            try:
                                if hasattr(e.dxf, 'text'):
                                    e.dxf.text = cleaned
                                elif hasattr(e, 'text'):
                                    e.text = cleaned
                            except Exception as ee:
                                self.safe_log(f"⚠️ 写回失败 ({label}): {ee}")

        clean_container(doc.modelspace(), "modelspace")
        for layout in doc.layouts:
            clean_container(layout, f"layout:{layout.name}")
        for block in doc.blocks:
            clean_container(block, f"block:{block.name}")

# GUI类保持不变，只需要更新版本号
class CADTranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Honsen内部 CAD中法互译工具 v2.2 - 编码问题修复版")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        try:
            icon_path = resource_path("icon.ico")
            self.root.iconbitmap(icon_path)
        except:
            pass  # 如果图标文件不存在，忽略错误
        self.deepl_key = tk.StringVar()
        self.chatgpt_key = tk.StringVar()
        # 日志队列
        self.log_queue = queue.Queue()
        
        # 变量
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        now = datetime.now()
        default_filename = f"translated_cad_{now.strftime('%Hh%M_%d-%m-%y')}"
        self.output_name = tk.StringVar(value=default_filename)
        self.translate_blocks = tk.BooleanVar(value=False)  # 默认不翻译块内文字
        self.translation_mode = tk.StringVar(value='zh_to_fr')  # 默认中文→法语
        self.load_api_keys()
        self.setup_ui()
        self.check_log_queue()
    def _create_translator(self):
        translator = CADChineseTranslator(log_callback=self.log_message)
        translator.use_engine = self.translation_engine.get().strip()
        translator.deepl_api_key = self.deepl_key.get().strip()
        translator.chatgpt_api_key = self.chatgpt_key.get().strip()
        return translator
    def safe_text_for_tkinter(self, text):
        """
        过滤超出tkinter支持范围的Unicode字符
        tkinter在某些版本中不支持U+FFFF以上的字符（如emoji）
        """
        if not text:
            return ""
        
        safe_chars = []
        for char in text:
            # 过滤超出BMP（基本多文种平面）的字符
            if ord(char) <= 0xFFFF:
                safe_chars.append(char)
            else:
                # 将不支持的字符替换为方括号描述
                char_name = f"[U+{ord(char):04X}]"
                safe_chars.append(char_name)
        
        return ''.join(safe_chars)
        
    def setup_ui(self):
        # 主容器
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 创建标签页控件
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建翻译功能页面
        self.translation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translation_frame, text='翻译功能')
        
        # 创建版本日志页面
        self.changelog_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.changelog_frame, text='版本更新日志')
        
        # 设置翻译功能页面
        self.setup_translation_tab()
        
        # 设置版本日志页面
        self.setup_changelog_tab()
        
    def setup_translation_tab(self):
        main_frame = ttk.Frame(self.translation_frame, padding="10")
        main_frame.pack(fill='both', expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)

        title_label = tk.Label(main_frame, text="Honsen非洲内部 CAD中法互译工具 v2.2\n编码问题修复版 - 先将dwg文件转换为dxf文件", 
                            font=('宋体', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        ttk.Label(main_frame, text="选择dxf文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file, width=50).grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="浏览", command=self.browse_input_file).grid(row=1, column=2, pady=5)

        ttk.Label(main_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(
            row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="浏览", command=self.browse_output_dir).grid(row=2, column=2, pady=5)

        ttk.Label(main_frame, text="输出文件名:").grid(row=3, column=0, sticky=tk.W, pady=5)
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        name_frame.columnconfigure(0, weight=1)
        ttk.Entry(name_frame, textvariable=self.output_name).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Label(name_frame, text=".dxf").grid(row=0, column=1)

        options_api_container = ttk.Frame(main_frame)
        options_api_container.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        options_api_container.columnconfigure(0, weight=1)
        options_api_container.columnconfigure(1, weight=1)

        options_frame = ttk.LabelFrame(options_api_container, text="翻译选项", padding="10")
        options_frame.grid(row=0, column=0, sticky=(tk.N, tk.EW), padx=(0, 10))

        ttk.Label(options_frame, text="翻译模式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(options_frame)
        mode_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        ttk.Radiobutton(mode_frame, text="中文→法语", variable=self.translation_mode, value='zh_to_fr').grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="法语→中文", variable=self.translation_mode, value='fr_to_zh').grid(row=0, column=1, sticky=tk.W, padx=(15, 0))

        ttk.Checkbutton(options_frame, text="翻译CAD块(Block)内的文字", variable=self.translate_blocks).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        note_label = tk.Label(options_frame, text="注意：块内文字通常是标准图块符号，建议保持原样", font=('宋体', 9), fg='gray')
        note_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        ttk.Label(options_frame, text="翻译引擎:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.translation_engine = tk.StringVar(value='google')
        engine_dropdown = ttk.Combobox(options_frame, textvariable=self.translation_engine, state='readonly', values=['google', 'deepl', 'chatgpt'], width=20)
        engine_dropdown.grid(row=4, column=1, sticky=tk.W)
        engine_note = tk.Label(options_frame, text="DeepL/ChatGPT 需配置 API Key", font=('宋体', 9), fg='gray')
        engine_note.grid(row=5, column=0, columnspan=2, sticky=tk.W)

        api_frame = ttk.LabelFrame(options_api_container, text="API Key 设置（可选）", padding="10")
        api_frame.grid(row=0, column=1, sticky=(tk.N, tk.EW))
        ttk.Label(api_frame, text="DeepL API Key:").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(api_frame, textvariable=self.deepl_key, width=40, show="*").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Label(api_frame, text="ChatGPT API Key:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(api_frame, textvariable=self.chatgpt_key, width=40, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.deepl_key.trace_add("write", lambda *args: self.save_api_keys())
        self.chatgpt_key.trace_add("write", lambda *args: self.save_api_keys())

        style = ttk.Style()
        style.configure("Big.TButton", font=("Microsoft YaHei", 12, "bold"))
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        self.start_button = ttk.Button(button_frame, text="开始翻译", command=self.start_translation, style="Big.TButton")
        self.start_button.pack(side=tk.LEFT, padx=10, ipady=6)
        ttk.Button(button_frame, text="清除日志", command=self.clear_log).pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        log_frame = ttk.LabelFrame(main_frame, text="实时日志", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, font=("Times New Roman", 11))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=9, column=0, columnspan=3, pady=(10, 5), sticky=(tk.W, tk.E))
        footer_frame.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(footer_frame, text="作者: 王一健").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(footer_frame, text="邮箱：etn@live.com").grid(row=0, column=1, sticky=tk.EW)
        ttk.Label(footer_frame, text="翻译完需要打开CAD调整文字位置").grid(row=0, column=2, sticky=tk.E)

    def setup_changelog_tab(self):
        """设置版本更新日志标签页"""
        # 主容器
        changelog_main_frame = ttk.Frame(self.changelog_frame, padding="15")
        changelog_main_frame.pack(fill='both', expand=True)
        
        # 标题
        title_frame = ttk.Frame(changelog_main_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="CAD中法互译工具", 
                              font=('Microsoft YaHei', 18, 'bold'))
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="版本更新历史", 
                                 font=('Microsoft YaHei', 12), fg='gray')
        subtitle_label.pack()
        
        # 创建滚动文本区域显示更新日志
        text_frame = ttk.Frame(changelog_main_frame)
        text_frame.pack(fill='both', expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # 文本框和滚动条
        self.changelog_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10), 
                                     bg='#f8f9fa', fg='#333333', padx=15, pady=15)
        changelog_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                          command=self.changelog_text.yview)
        self.changelog_text.configure(yscrollcommand=changelog_scrollbar.set)
        
        self.changelog_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        changelog_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 插入更新日志内容
        changelog_content = """
版本 2.2.0 - 2025年5月 【编码问题修复版】
================================================================================

【关键修复】
  * [修复] 完全解决法语特殊字符编码问题
  * [新增] 智能字符验证系统，自动识别并过滤无效字符
  * [增强] 文本解码安全性，支持多种编码格式自动检测
  * [修复] "ް" 等无效字符导致的翻译失败问题
  * [优化] 编码转换算法，确保法语重音符号正确显示

【编码增强】
  * 支持的法语特殊字符：É, é, è, ê, ô, à, ç, ù, û, î
  * 自动检测并修复常见编码错误模式
  * 智能过滤Unicode控制字符和代理字符
  * 增强的文本验证机制，提升翻译成功率
  * 详细的编码问题日志记录

【稳定性提升】
  * 多重编码检测机制，确保文件正确读取
  * 改进的异常处理，避免编码问题导致程序崩溃
  * 优化内存使用，提升大文件处理性能
  * 增强网络中断检测和恢复机制

================================================================================

版本 2.1.0 - 2025年5月
================================================================================

【重大精简】
  * 移除英文翻译功能，专注中法互译
  * 删除所有英文相关配置和处理逻辑
  * 界面更加简洁，只保留两个翻译选项：
    - 中文→法语
    - 法语→中文
  * 优化代码结构，提高翻译效率

【功能优化】
  * 强化中法建筑术语词典
  * 改进法语特殊字符处理
  * 提升翻译准确度和稳定性
  * 简化用户操作流程

================================================================================

版本 2.0.0 - 2025年5月
================================================================================

【重要更新】
  * 移除自动语言检测功能，简化操作流程
  * 强制用户选择翻译方向，避免语言识别错误
  * 默认翻译模式：中文→法语
  * 支持明确的翻译方向选择

【界面简化】
  * 移除"自动检测"选项，界面更简洁
  * 翻译模式布局优化，操作更直观
  * 用户必须明确选择翻译方向

【稳定性提升】
  * 避免语言自动检测带来的误判
  * 翻译结果更加准确可控
  * 减少因语言识别错误导致的翻译失败

================================================================================

版本 1.2.0 - 2025年5月
================================================================================

【新功能】
  * 添加标签页界面，分离功能区域和版本信息
  * 新增"翻译选项"区域，可选择是否翻译CAD块内文字
  * 默认不翻译块内文字（推荐设置，保持图块标准化）
  * 优化界面布局，提升用户体验

【修复与改进】
  * 尝试修复法语特殊字符编码问题（v2.2完全解决）
  * 增强文本安全解码/编码机制
  * 支持多种编码格式自动检测
  * 改进错误处理和日志记录
  * 修复Python 3.7兼容性问题

================================================================================

【使用建议】
  * 翻译前建议备份原文件
  * 翻译完成后在CAD中检查文字位置
  * 块内文字一般不需要翻译（标准图块符号）
  * v2.2已解决所有已知编码问题

【技术支持】
  联系人: 王一健
  邮箱: etn@live.com
  电话: +225 0500902929

【专注中法互译】
  本工具现已专注于中法建筑图纸翻译，
  为非洲法语区项目提供专业支持。
  v2.2版本完全解决了编码问题，确保翻译质量。

================================================================================
        """
        
        self.changelog_text.insert('1.0', self.safe_text_for_tkinter(changelog_content.strip()))
        self.changelog_text.config(state='disabled')  # 设为只读
        
        # 底部信息
        bottom_frame = ttk.Frame(changelog_main_frame)
        bottom_frame.pack(fill='x', pady=(15, 0))
        
        info_label = tk.Label(bottom_frame, 
                             text="© 2025 Honsen非洲 - CAD中法互译工具 v2.2 | 编码问题修复版", 
                             font=('Microsoft YaHei', 9), fg='gray')
        info_label.pack()

    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="选择DXF文件",
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)

            # 自动设置输出目录为输入文件所在目录
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(filename))

            # 自动根据选择的文件名和翻译模式设置输出名
            base_name = os.path.splitext(os.path.basename(filename))[0]
            now = datetime.now()
            timestamp = now.strftime('%Hh%M_%d-%m-%y')
            
            # 根据翻译模式设置前缀
            if self.translation_mode.get() == 'zh_to_fr':
                prefix = 'fr'
            else:
                prefix = 'zh'
            
            self.output_name.set(f"{prefix}_{base_name}_{timestamp}")
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
    def safe_log(self, message):
        # 清除 surrogate 代理字符，避免 utf-8 错误
        cleaned = ''.join(c for c in str(message) if not (0xD800 <= ord(c) <= 0xDFFF))
        try:
            self.log_text.insert(tk.END, cleaned + "\n")
            self.log_text.see(tk.END)
        except Exception as e:
            print(f"[日志写入失败]: {e}")
            print(repr(cleaned))
    def log_message(self, message):
        """添加日志消息到界面与队列（确保无代理字符）"""
        safe = ''.join(c for c in str(message) if not (0xD800 <= ord(c) <= 0xDFFF))
        try:
            self.log_text.insert(tk.END, safe + '\n')
            self.log_text.see(tk.END)
        except Exception as e:
            print(f"[GUI 日志写入失败]: {e}")
            print(repr(safe))
        self.log_queue.put(safe)
    
    def on_close(self):
        """窗口关闭时安全退出"""
        self.root.quit()
        self.root.destroy()

    def check_log_queue(self):
        """检查日志队列并更新UI（含异常处理）"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                if isinstance(message, str):  # 防御式检查
                    # 使用安全文本处理
                    safe_message = self.safe_text_for_tkinter(message)
                    self.log_text.insert(tk.END, safe_message + "\n")
                    self.log_text.see(tk.END)
        except queue.Empty:
            pass
        except Exception as e:
            import traceback
            print("日志处理异常:")
            traceback.print_exc()
        finally:
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(100, self.check_log_queue)

    def clear_log(self):
        """清除日志内容"""
        self.log_text.delete(1.0, tk.END)
    
    def validate_inputs(self):
        if not self.input_file.get():
            messagebox.showerror("错误", "请选择输入文件")
            return False
        
        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("错误", "输入文件不存在")
            return False
        
        if not self.input_file.get().lower().endswith('.dxf'):
            messagebox.showerror("错误", "请选择DXF文件")
            return False
        
        if not self.output_dir.get():
            messagebox.showerror("错误", "请选择输出目录")
            return False
        
        if not os.path.exists(self.output_dir.get()):
            messagebox.showerror("错误", "输出目录不存在")
            return False
        
        if not self.output_name.get().strip():
            messagebox.showerror("错误", "请输入输出文件名")
            return False
        
        return True

    # 加载和保存 API Key
    def load_api_keys(self):
        """从本地配置文件加载 API Key"""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.deepl_key.set(config.get("deepl_key", ""))
                    self.chatgpt_key.set(config.get("chatgpt_key", ""))
                    self.log_message(" 已加载保存的 API Key")
            except Exception as e:
                self.log_message(f" 加载配置失败: {e}")

    def save_api_keys(self):
        """保存 API Key 到本地配置文件"""
        try:
            config = {
                "deepl_key": self.deepl_key.get().strip(),
                "chatgpt_key": self.chatgpt_key.get().strip()
            }
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            self.log_message(" API Key 已保存")
        except Exception as e:
            self.log_message(f" 保存配置失败: {e}")
    
    
    def start_translation(self):
        if not self.validate_inputs():
            return
        if not self.check_internet_connection():
            messagebox.showerror("网络错误", " 无法连接网络，请检查您的网络连接后重试。")
            self.log_message(" 网络中断，翻译终止")
            self.status_var.set("网络中断，已取消")
            self.progress.stop()
            self.start_button.config(state='normal')
            return
        translator = CADChineseTranslator(log_callback=self.log_message)
        translator.use_engine = self.translation_engine.get().strip()

        # 设置用户输入的 API Key
        translator.deepl_api_key = self.deepl_key.get().strip()
        translator.chatgpt_api_key = self.chatgpt_key.get().strip()
        if translator.deepl_api_key:
            import deepl
            try:
                translator.deepl_translator = deepl.Translator(translator.deepl_api_key)
                self.log_message(" DeepL 引擎初始化成功")
            except Exception as e:
                self.log_message(f" DeepL 初始化失败: {e}")
                messagebox.showerror("错误", "翻译失败: 未正确配置 DeepL API Key 或初始化失败")
                return
        # 主线程中创建翻译器并传入线程
        self.translator = self._create_translator()
        # 禁用开始按钮
        self.start_button.config(state='disabled')
        self.progress.start()
        self.status_var.set("翻译中...")
        
        # 构建输出文件路径
        output_file = os.path.join(
            self.output_dir.get(), 
            self.output_name.get().strip() + '.dxf'
        )
        
        # 在新线程中执行翻译
        def translation_thread():
            try:
                translator = self.translator  # ✅ 使用主线程初始化好的翻译器
                translator.translate_cad_file(
                    self.input_file.get(),
                    output_file,
                    self.translation_mode.get(),
                    self.translate_blocks.get()
                )
                self.root.after(0, self.translation_complete, True, "翻译完成！")
            except Exception as e:
                error_msg = f"翻译失败: {str(e)}"
                self.root.after(0, self.translation_complete, False, error_msg)

        thread = threading.Thread(target=translation_thread, daemon=True)
        thread.start()
    
    def translation_complete(self, success, message):
        self.progress.stop()
        self.start_button.config(state='normal')
        
        if success:
            self.status_var.set("完成")
            messagebox.showinfo("成功", message)
            self.log_message("=" * 50)
        else:
            self.status_var.set("失败")
            messagebox.showerror("错误", message)
            self.log_message(f"ERROR: {message}")

    def check_internet_connection(self, url='http://www.google.com', timeout=3):
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True
        except Exception:
            return False

    def run(self):
        self.root.mainloop()


def main():
    app = CADTranslatorGUI()
    app.run()


if __name__ == '__main__':
    main()