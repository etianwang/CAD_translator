import ezdxf
import re
import time
import os
import shutil
import csv
from pathlib import Path
from googletrans import Translator
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from datetime import datetime
import os
import sys
import urllib.request

def resource_path(relative_path):
    """返回资源文件的正确路径（兼容 .py 和 .exe）"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 临时目录
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class CADChineseTranslator:
    def __init__(self, log_callback=None):
        self.translator = Translator()
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+')
        self.french_pattern = re.compile(r'[àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ]')
        self.english_pattern = re.compile(r'^[a-zA-Z\s\.,;:!?\-\'\"()]+$')
        self.translated_cache = {}
        self.log_callback = log_callback
        
        # 语言配置
        self.language_configs = {
            'zh_to_fr': {
                'source': 'zh',
                'target': 'fr',
                'name': '中文→法语',
                'detect_pattern': self.chinese_pattern,
                'context': self.get_architectural_context_fr()
            },
            'fr_to_zh': {
                'source': 'fr',
                'target': 'zh',
                'name': '法语→中文',
                'detect_pattern': self.french_pattern,
                'context': self.get_architectural_context_zh()
            },
            'zh_to_en': {
                'source': 'zh',
                'target': 'en',
                'name': '中文→英语',
                'detect_pattern': self.chinese_pattern,
                'context': self.get_architectural_context_en()
            },
            'en_to_zh': {
                'source': 'en',
                'target': 'zh',
                'name': '英语→中文',
                'detect_pattern': self.english_pattern,
                'context': self.get_architectural_context_zh()
            }
        }
        
    def get_architectural_context_fr(self):
        """建筑术语上下文 - 法语"""
        return {
            '天花': 'plafond',
            '吊顶': 'faux plafond',
            '地面': 'sol',
            '墙面': 'mur',
            '卫生间': 'salle de bain',  
            '厨房': 'cuisine',
            '门窗': 'portes et fenetres',
            '入口': 'entree',
            '出口': 'sortie',
            '走廊': 'couloir',
            '楼梯': 'escalier',
            '电梯': 'ascenseur',
            '照明': 'eclairage',
            '插座': 'prise',
            '开关': 'interrupteur',
            '强电': 'courant fort',
            '弱电': 'courant faible',
            '监控': 'videosurveillance',
            '消防': 'securite incendie',
            '报警': 'alarme',
            '空调': 'climatisation',
            '新风': 'ventilation',
            '排风': "extraction d'air",
            '排烟': 'evacuation fumee',
            '风口': "grille d'air",
            '出风口': 'bouche de soufflage',
            '回风口': 'bouche de reprise',
            '风管': "conduite d'air",
            '风机': 'ventilateur',
            '风机盘管': 'ventilo-convecteur',
            '新风机': 'unite de ventilation',
            '冷却塔': 'tour de refroidissement',
            '空调机': 'unite de climatisation',
            '冷热水': 'eau chaude et froide',
            '排水管': "evacuation d'eau",
            '冷凝水管': 'conduite de condensat',
            '水管': "conduite d'eau",
            '配电箱': 'tableau de distribution',
            '桥架': 'chemin de cables',
            '管道井': 'gaine technique',
            '设备间': 'local technique',
            '机房': 'local des machines',
            '天花图': 'plan de plafond',
            '控制屏': 'ecran de controle',
            '屏幕': 'ecran',
            '控制': 'controle',
        }
    
    def get_architectural_context_en(self):
        """建筑术语上下文 - 英语"""
        return {
            '天花': 'ceiling',
            '吊顶': 'suspended ceiling',
            '地面': 'floor',
            '墙面': 'wall',
            '卫生间': 'bathroom',
            '厨房': 'kitchen',
            '门窗': 'doors and windows',
            '入口': 'entrance',
            '出口': 'exit',
            '走廊': 'corridor',
            '楼梯': 'staircase',
            '电梯': 'elevator',
            '照明': 'lighting',
            '插座': 'outlet',
            '开关': 'switch',
            '强电': 'power supply',
            '弱电': 'low voltage',
            '监控': 'surveillance',
            '消防': 'fire safety',
            '报警': 'alarm',
            '空调': 'air conditioning',
            '新风': 'fresh air',
            '排风': 'exhaust air',
            '排烟': 'smoke exhaust',
            '风口': 'air vent',
            '出风口': 'supply air outlet',
            '回风口': 'return air inlet',
            '风管': 'air duct',
            '风机': 'fan',
            '风机盘管': 'fan coil unit',
            '新风机': 'fresh air unit',
            '冷却塔': 'cooling tower',
            '空调机': 'air handling unit',
            '冷热水': 'chilled/hot water',
            '排水管': 'drain pipe',
            '冷凝水管': 'condensate pipe',
            '水管': 'water pipe',
            '配电箱': 'distribution panel',
            '桥架': 'cable tray',
            '管道井': 'utility shaft',
            '设备间': 'equipment room',
            '机房': 'machine room',
            '天花图': 'ceiling plan',
            '控制屏': 'control screen',
            '屏幕': 'screen',
            '控制': 'control',
        }
    
    def get_architectural_context_zh(self):
        """建筑术语上下文 - 中文（用于反向翻译）"""
        fr_to_zh = {
            'plafond': '天花',
            'faux plafond': '吊顶', 
            'sol': '地面',
            'mur': '墙面',
            'salle de bain': '卫生间',
            'cuisine': '厨房',
            'entree': '入口',
            'sortie': '出口',
            'couloir': '走廊',
            'escalier': '楼梯',
            'ascenseur': '电梯',
            'eclairage': '照明',
            'prise': '插座',
            'interrupteur': '开关',
            'climatisation': '空调',
            'ventilation': '新风',
            'ecran de controle': '控制屏',
            'ecran': '屏幕',
            'controle': '控制',
        }
        
        en_to_zh = {
            'ceiling': '天花',
            'suspended ceiling': '吊顶',
            'floor': '地面',
            'wall': '墙面',
            'bathroom': '卫生间',
            'kitchen': '厨房',
            'entrance': '入口',
            'exit': '出口',
            'corridor': '走廊',
            'staircase': '楼梯',
            'elevator': '电梯',
            'lighting': '照明',
            'outlet': '插座',
            'switch': '开关',
            'air conditioning': '空调',
            'fresh air': '新风',
            'control screen': '控制屏',
            'screen': '屏幕',
            'control': '控制',
        }
        
        # 合并两个词典
        combined = {}
        combined.update(fr_to_zh)
        combined.update(en_to_zh)
        return combined

    def log(self, message):
        """发送日志消息到GUI"""
        if self.log_callback:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_callback(f"[{timestamp}] {message}")

    def contains_chinese(self, text):
        """检测是否包含中文字符"""
        return bool(self.chinese_pattern.search(text)) if text else False
    
    def contains_target_language(self, text, lang_config):
        """根据翻译配置检测文本是否包含目标语言内容"""
        if not text or not lang_config:
            return False
            
        if lang_config == 'zh_to_fr' or lang_config == 'zh_to_en':
            # 中文到其他语言：检测是否包含中文
            return self.contains_chinese(text)
        elif lang_config == 'fr_to_zh':
            # 法语到中文：检测是否包含法语或拉丁字母
            return self.contains_french(text) or bool(re.search(r'[a-zA-Z]', text))
        elif lang_config == 'en_to_zh':
            # 英语到中文：检测是否包含英语或拉丁字母
            return self.contains_english(text) or bool(re.search(r'[a-zA-Z]', text))
        
        return False
    
    def contains_french(self, text):
        """检测是否包含法语特征（更智能的检测）"""
        if not text:
            return False
        
        # 1. 检测法语特殊字符
        if self.french_pattern.search(text):
            return True
        
        # 2. 检测法语特有词汇
        french_indicators = [
            # 冠词和介词
            r'\ble\b', r'\bla\b', r'\bles\b', r'\bdes\b', r'\bdu\b', r'\bde\b', r'\bet\b',
            r'\bun\b', r'\bune\b', r'\bdans\b', r'\bsur\b', r'\bavec\b', r'\bpour\b',
            # 常见动词
            r'\best\b', r'\bsont\b', r'\betre\b', r'\bavoir\b', r'\bfaire\b',
            # 建筑相关法语词汇
            r'\bplafond\b', r'\bsalle\b', r'\bmur\b', r'\bsol\b', r'\beclairage\b',
            r'\bcuisine\b', r'\bentree\b', r'\bsortie\b', r'\bequipe\b',
            # 其他法语特征词
            r'\bqui\b', r'\bque\b', r'\bout\b', r'\bmais\b', r'\btres\b', r'\bnotre\b'
        ]
        
        text_lower = text.lower()
        french_matches = sum(1 for pattern in french_indicators if re.search(pattern, text_lower))
        
        # 3. 检测法语语法特征（如单词结尾）
        french_endings = [r'tion\b', r'ment\b', r'eur\b', r'euse\b', r'aux\b']
        ending_matches = sum(1 for pattern in french_endings if re.search(pattern, text_lower))
        
        # 如果有法语特征词汇或语法特征，认为是法语
        return french_matches > 0 or ending_matches > 0
    
    def contains_english(self, text):
        """检测是否为英语文本（排除法语可能性）"""
        if not text:
            return False
        
        # 先检查是否可能是法语
        if self.contains_french(text):
            return False
        
        # 检测英语特有词汇
        english_indicators = [
            # 英语冠词和介词
            r'\bthe\b', r'\ba\b', r'\ban\b', r'\band\b', r'\bof\b', r'\bin\b', r'\bto\b',
            r'\bfor\b', r'\bwith\b', r'\bon\b', r'\bat\b', r'\bby\b', r'\bfrom\b',
            # 常见英语动词
            r'\bis\b', r'\bare\b', r'\bwas\b', r'\bwere\b', r'\bhave\b', r'\bhas\b',
            # 建筑相关英语词汇
            r'\bceiling\b', r'\bfloor\b', r'\bwall\b', r'\broom\b', r'\blighting\b',
            r'\boutlet\b', r'\bswitch\b', r'\bcontrol\b', r'\bscreen\b',
            # 其他英语特征词
            r'\bthis\b', r'\bthat\b', r'\bwhere\b', r'\bwhen\b', r'\bwhat\b'
        ]
        
        text_lower = text.lower()
        english_matches = sum(1 for pattern in english_indicators if re.search(pattern, text_lower))
        
        # 同时检查是否全为英文字母（排除数字和特殊符号过多的情况）
        alpha_chars = re.sub(r'[^a-zA-Z]', '', text)
        if len(alpha_chars) < 2:  # 太短的文本不判断
            return False
        
        # 如果有英语特征词汇且文本主要由英文字母组成，认为是英语
        return english_matches > 0 and len(alpha_chars) / len(text.replace(' ', '')) > 0.7
    
    def detect_language_and_config(self, text):
        """自动检测文本语言并返回对应的翻译配置"""
        if not text:
            return None
        
        text_clean = text.strip().lower()
            
        # 1. 优先检测中文（最明确的特征）
        if self.contains_chinese(text):
            # 如果同时包含中文和其他语言，需要判断主要语言
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            total_chars = len(re.sub(r'\s+', '', text))
            
            if chinese_chars / max(total_chars, 1) > 0.3:  # 中文字符占比超过30%
                # 检查是否有其他语言提示来决定翻译目标
                if self.contains_french(text) or 'fr' in text_clean:
                    return 'zh_to_fr'  # 默认中文翻译到法语
                elif self.contains_english(text) or 'en' in text_clean:
                    return 'zh_to_en'
                else:
                    return 'zh_to_fr'  # 默认中文翻译到法语
        
        # 2. 检测法语（使用改进的检测方法）
        if self.contains_french(text):
            return 'fr_to_zh'
        
        # 3. 检测英语（确保不与法语冲突）
        if self.contains_english(text):
            return 'en_to_zh'
        
        # 4. 对于模糊情况，使用上下文线索
        # 检查是否包含建筑术语来帮助判断
        french_architectural_terms = ['plafond', 'salle', 'cuisine', 'eclairage', 'entree', 'sortie']
        english_architectural_terms = ['ceiling', 'room', 'kitchen', 'lighting', 'entrance', 'exit']
        
        for term in french_architectural_terms:
            if term in text_clean:
                return 'fr_to_zh'
        
        for term in english_architectural_terms:
            if term in text_clean:
                return 'en_to_zh'
        
        # 5. 最后的判断：如果文本主要是字母且没有明确特征
        if re.match(r'^[a-zA-Z\s\.,;:!?\-\'\"()]+$', text.strip()):
            # 使用统计方法：检查常见单词
            words = text_clean.split()
            french_score = 0
            english_score = 0
            
            # 常见词汇评分
            common_french = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'un', 'une', 'dans', 'sur']
            common_english = ['the', 'a', 'an', 'and', 'of', 'in', 'to', 'for', 'with', 'on', 'at']
            
            for word in words:
                if word in common_french:
                    french_score += 1
                if word in common_english:
                    english_score += 1
            
            if french_score > english_score:
                return 'fr_to_zh'
            elif english_score > french_score:
                return 'en_to_zh'
            else:
                # 如果还是无法确定，默认当作英语处理（因为英语更常见）
                return 'en_to_zh'
        
        return None

    def decode_text_safely(self, text):
        """安全解码文本，处理各种编码问题"""
        if not text:
            return ""
        
        # 如果已经是字符串，处理可能的编码问题
        if isinstance(text, str):
            # 检查是否包含代理字符
            try:
                # 尝试编码测试，如果有代理字符会失败
                text.encode('utf-8')
            except UnicodeEncodeError:
                # 移除代理字符
                text = ''.join(char for char in text if not (0xD800 <= ord(char) <= 0xDFFF))
                self.log(f"警告: 检测到损坏编码，已清理代理字符")
            
            # 检查是否包含编码转义序列
            if '\\x' in text:
                try:
                    # 尝试解码转义序列
                    decoded = text.encode('latin1').decode('utf-8')
                    return decoded
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        # 尝试其他编码
                        decoded = text.encode('latin1').decode('cp1252')
                        return decoded
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # 如果都失败了，清理不可打印字符后返回
                        cleaned = ''.join(char for char in text if char.isprintable() or char.isspace())
                        return cleaned
            
            # 清理不可打印字符（保留中文和基本符号）
            cleaned = ''.join(char for char in text if (
                char.isprintable() or 
                char.isspace() or 
                '\u4e00' <= char <= '\u9fff' or  # 中文字符
                '\u3000' <= char <= '\u303f' or  # 中文符号
                '\uff00' <= char <= '\uffef'     # 全角字符
            ))
            return cleaned
        
        # 如果是字节类型
        if isinstance(text, bytes):
            encodings = ['utf-8', 'gbk', 'gb2312', 'cp1252', 'latin1']
            for encoding in encodings:
                try:
                    decoded = text.decode(encoding)
                    # 检查解码结果是否包含代理字符
                    try:
                        decoded.encode('utf-8')
                        return decoded
                    except UnicodeEncodeError:
                        # 如果包含代理字符，清理后返回
                        cleaned = ''.join(char for char in decoded if not (0xD800 <= ord(char) <= 0xDFFF))
                        return cleaned
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用错误替换并清理
            decoded = text.decode('utf-8', errors='replace')
            cleaned = ''.join(char for char in decoded if char != '\ufffd')  # 移除替换字符
            return cleaned
        
        return str(text)

    def encode_text_safely(self, text):
        """安全编码文本用于写回CAD"""
        if not text:
            return ""
        
        # 确保文本是正确的Unicode字符串
        text = self.decode_text_safely(text)
        
        # 再次检查并清理代理字符
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            text = ''.join(char for char in text if not (0xD800 <= ord(char) <= 0xDFFF))
            self.log(f"警告: 编码时检测到代理字符，已清理")
        
        # 处理特殊的法语字符
        replacements = {
            '\xc9': 'É',
            '\xe9': 'é',
            '\xe8': 'è',
            '\xea': 'ê',
            '\xf4': 'ô',
            '\xe0': 'à',
            '\xe7': 'ç',
            '\xf9': 'ù',
            '\xfb': 'û',
            '\xee': 'î',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text

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
            self.log(f"清理失败: {e}")
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
                'crdn de contr': 'ecran de controle',
                'contr': 'controle',
            }
        elif lang_config_key == 'zh_to_en':
            corrections = {
                'ceiling plan': 'ceiling plan',
                'air condition': 'air conditioning',
                'electric box': 'electrical panel',
                'water pipe line': 'water pipe',
            }
        else:
            corrections = {}

        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        return re.sub(r'\s+', ' ', text).strip()

    def translate_text(self, text, force_lang_config):
        if not text or not force_lang_config:
            return text
        if text in self.translated_cache:
            return self.translated_cache[text]

        # 先解码文本
        decoded_text = self.decode_text_safely(text)
        cleaned = self.clean_text(decoded_text)
        
        # 检查清理后的文本是否为空或只包含特殊字符
        if not cleaned or not cleaned.strip():
            self.log(f"跳过空文本或无效文本: \"{text}\"")
            return self.encode_text_safely(decoded_text)
        
        # 检查是否包含过多损坏字符
        printable_chars = sum(1 for char in cleaned if char.isprintable() or '\u4e00' <= char <= '\u9fff')
        if len(cleaned) > 0 and printable_chars / len(cleaned) < 0.5:
            self.log(f"跳过损坏文本(可读字符比例过低): \"{cleaned}\"")
            return self.encode_text_safely(decoded_text)
        
        # 使用指定的翻译配置
        lang_config_key = force_lang_config
        if lang_config_key not in self.language_configs:
            self.log(f"无效的翻译配置: {lang_config_key}")
            return self.encode_text_safely(decoded_text)
        
        lang_config = self.language_configs[lang_config_key]
        
        try:
            # 记录上下文，但不传递给翻译器
            context = self.get_contextual_translation(cleaned, lang_config_key)
            self.log(f"翻译中 ({lang_config['name']}): {cleaned}")
            if context != cleaned:
                self.log(f"提示术语: {context}")

            # 不指定源语言，让Google自动检测，避免混合语言文本的问题
            result = self.translator.translate(cleaned, dest=lang_config['target'])
            final = self.post_process_translation(result.text, cleaned, lang_config_key)
            
            # 安全编码结果
            final = self.encode_text_safely(final)

            # 防止网络断导致未翻译
            if final.strip() == cleaned.strip():
                self.log(f"⚠️ 可能网络中断，翻译结果无变化: \"{cleaned}\"")
                raise ConnectionError("网络中断，翻译无效")

            self.translated_cache[text] = final
            self.log(f"✔ 翻译完成 ({lang_config['name']}): \"{cleaned}\" → \"{final}\"")
            time.sleep(0.5)
            return final

        except Exception as e:
            # 如果翻译失败，尝试备用方法
            if "invalid source language" in str(e).lower():
                self.log(f"源语言检测失败，尝试备用翻译方法: \"{cleaned}\"")
                try:
                    # 使用auto作为源语言
                    result = self.translator.translate(cleaned, src='auto', dest=lang_config['target'])
                    final = self.post_process_translation(result.text, cleaned, lang_config_key)
                    final = self.encode_text_safely(final)
                    
                    self.translated_cache[text] = final
                    self.log(f"✔ 备用翻译成功 ({lang_config['name']}): \"{cleaned}\" → \"{final}\"")
                    time.sleep(0.5)
                    return final
                except Exception as e2:
                    self.log(f"备用翻译也失败: {e2} → 保持原文: \"{cleaned}\"")
                    return self.encode_text_safely(text)
            else:
                self.log(f"翻译失败: {e} → 原文: \"{cleaned}\"")
                return self.encode_text_safely(text)

    def extract_text_entities(self, doc, lang_config, include_blocks=False):
        items = []
        # 处理模型空间和布局空间
        for space in [doc.modelspace()] + list(doc.layouts):
            for e in space:
                if e.dxftype() in ['TEXT', 'MTEXT']:
                    txt = self.get_entity_text(e)
                    if txt and self.should_translate_text(txt, lang_config):
                        # 验证文本质量
                        if self.is_valid_text_for_translation(txt):
                            items.append({
                                'entity': e,
                                'original_text': txt,
                                'layer': getattr(e.dxf, 'layer', 'DEFAULT'),
                                'location': space.name if hasattr(space, 'name') else 'modelspace'
                            })
                        else:
                            self.log(f"跳过损坏文本: \"{txt}\"")

        # 根据选项决定是否处理块内文字
        if include_blocks:
            self.log("选择翻译块内文字，正在处理块...")
            for block in doc.blocks:
                if block.name.startswith('*'):
                    continue
                for e in block:
                    if e.dxftype() in ['TEXT', 'MTEXT']:
                        txt = self.get_entity_text(e)
                        if txt and self.should_translate_text(txt, lang_config):
                            if self.is_valid_text_for_translation(txt):
                                items.append({
                                    'entity': e,
                                    'original_text': txt,
                                    'layer': getattr(e.dxf, 'layer', 'DEFAULT'),
                                    'location': f'block:{block.name}'
                                })
                            else:
                                self.log(f"跳过块内损坏文本: \"{txt}\"")
        else:
            self.log("跳过块内文字翻译（推荐设置）")

        self.log(f"提取文本实体: {len(items)} 条 {'(包含块内文字)' if include_blocks else '(不包含块内文字)'}")
        return items

    def should_translate_text(self, text, lang_config):
        """判断文本是否需要翻译（基于指定的语言配置）"""
        if not text or not lang_config:
            return False
        
        # 使用更灵活的检测方法
        return self.contains_target_language(text, lang_config)

    def is_valid_text_for_translation(self, text):
        """检查文本是否适合翻译"""
        if not text or not text.strip():
            return False
        
        # 解码并清理文本
        decoded = self.decode_text_safely(text)
        cleaned = self.clean_text(decoded)
        
        if not cleaned or len(cleaned.strip()) < 2:
            return False
        
        # 计算可读字符比例
        printable_chars = sum(1 for char in cleaned if (
            char.isprintable() or 
            char.isspace() or 
            '\u4e00' <= char <= '\u9fff' or  # 中文
            '\u3000' <= char <= '\u303f'     # 中文符号
        ))
        
        # 如果可读字符比例太低，认为是损坏的文本
        if len(cleaned) > 0 and printable_chars / len(cleaned) < 0.6:
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
            return self.decode_text_safely(text)
        except Exception as e:
            self.log(f"获取文本失败: {e}")
            return ""

    def write_back_translation(self, entity, new_text):
        try:
            # 安全编码新文本
            encoded_text = self.encode_text_safely(new_text)
            
            if hasattr(entity.dxf, 'text'):
                entity.dxf.text = encoded_text
            elif hasattr(entity, 'text'):
                entity.text = encoded_text
        except Exception as e:
            self.log(f"写回失败: {e}")

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
        self.log(f"正在读取: {input_file}")
        doc = ezdxf.readfile(input_file, encoding='utf-8')
        items = self.extract_text_entities(doc, lang_config, include_blocks)

        if lang_config and lang_config in self.language_configs:
            config_name = self.language_configs[lang_config]['name']
            self.log(f"翻译模式: {config_name}")

        total_items = len(items)
        for i, item in enumerate(items, 1):
            translated = self.translate_text(item['original_text'], lang_config)
            item['translated_text'] = translated
            self.write_back_translation(item['entity'], translated)
            self.log(f"进度: {i}/{total_items} ({i/total_items*100:.1f}%)")

        doc.saveas(output_file, encoding='utf-8')
        self.log(f"文件保存: {output_file}")

        report_file = output_file.replace('.dxf', '_report.csv')
        self.create_report(items, report_file)
        self.log(f"翻译报告保存: {report_file}")
        self.log(f"翻译完成！共处理 {total_items} 个文本对象")


class CADTranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Honsen内部 CAD多语言翻译工具 v2.0")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        try:
            icon_path = resource_path("icon.ico")
            self.root.iconbitmap(icon_path)
        except:
            pass  # 如果图标文件不存在，忽略错误
        
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
        
        self.setup_ui()
        self.check_log_queue()
        
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
        """设置翻译功能标签页"""
        # 主容器 - 使用 translation_frame 而不是 main_frame
        main_frame = ttk.Frame(self.translation_frame, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)  # 日志区域可扩展
        
        # 标题
        title_label = tk.Label(main_frame, text="Honsen非洲内部 CAD多语言翻译工具\n 先将dwg文件转换为dxf文件（有问题找Etienne）", 
                               font=('宋体', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 输入文件选择
        ttk.Label(main_frame, text="选择dxf文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file, width=50).grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="浏览", command=self.browse_input_file).grid(
            row=1, column=2, pady=5)
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(
            row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="浏览", command=self.browse_output_dir).grid(
            row=2, column=2, pady=5)
        
        # 输出文件名
        ttk.Label(main_frame, text="输出文件名:").grid(row=3, column=0, sticky=tk.W, pady=5)
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        name_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(name_frame, textvariable=self.output_name).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Label(name_frame, text=".dxf").grid(row=0, column=1)
        
        # 翻译选项
        options_frame = ttk.LabelFrame(main_frame, text="翻译选项", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 翻译模式选择
        ttk.Label(options_frame, text="翻译模式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(options_frame)
        mode_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        ttk.Radiobutton(mode_frame, text="中文→法语", variable=self.translation_mode, 
                       value='zh_to_fr').grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="法语→中文", variable=self.translation_mode, 
                       value='fr_to_zh').grid(row=0, column=1, sticky=tk.W, padx=(15, 0))
        ttk.Radiobutton(mode_frame, text="中文→英语", variable=self.translation_mode, 
                       value='zh_to_en').grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        ttk.Radiobutton(mode_frame, text="英语→中文", variable=self.translation_mode, 
                       value='en_to_zh').grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 块内文字选项
        ttk.Checkbutton(options_frame, text="翻译CAD块(Block)内的文字", 
                       variable=self.translate_blocks).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # 说明文字
        note_label = tk.Label(options_frame, text="注意：块内文字通常是标准图块符号，建议保持原样", 
                             font=('宋体', 9), fg='gray')
        note_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="开始翻译", 
                                      command=self.start_translation)
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(button_frame, text="清除日志", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=10)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="实时日志", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        # 创建日志文本框和滚动条
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, font=("Times New Roman", 11))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 底栏信息
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=9, column=0, columnspan=3, pady=(10, 5), sticky=(tk.W, tk.E))
        footer_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Label(footer_frame, text="作者: 王一健").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(footer_frame, text="邮箱：etn@live.com").grid(row=0, column=1, sticky=tk.EW)
        ttk.Label(footer_frame, text="翻译完需要打开CAD调整文字位置").grid(row=0, column=2, sticky=tk.E)

    def setup_changelog_tab(self):
        """设置版本更新日志标签页"""
        # 主容器
        changelog_main = ttk.Frame(self.changelog_frame, padding="15")
        changelog_main.pack(fill='both', expand=True)
        
        # 标题
        title_frame = ttk.Frame(changelog_main)
        title_frame.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="CAD多语言翻译工具", 
                              font=('Microsoft YaHei', 18, 'bold'))
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="版本更新历史", 
                                 font=('Microsoft YaHei', 12), fg='gray')
        subtitle_label.pack()
        
        # 创建滚动文本区域显示更新日志
        text_frame = ttk.Frame(changelog_main)
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
版本 2.0.0 - 2025年5月
════════════════════════════════════════════════════════════════

【重要更新】
  * 移除自动语言检测功能，简化操作流程
  * 强制用户选择翻译方向，避免语言识别错误
  * 默认翻译模式：中文→法语
  * 支持4种明确的翻译方向：
    - 中文→法语
    - 法语→中文  
    - 中文→英语
    - 英语→中文

【界面简化】
  * 移除"自动检测"选项，界面更简洁
  * 翻译模式布局优化，操作更直观
  * 用户必须明确选择翻译方向

【稳定性提升】
  * 避免语言自动检测带来的误判
  * 翻译结果更加准确可控
  * 减少因语言识别错误导致的翻译失败

════════════════════════════════════════════════════════════════

版本 2.0.1 - 2025年5月
════════════════════════════════════════════════════════════════

【重大更新】
  * 新增多语言翻译支持：
    - 中文 ↔ 法语（双向翻译）
    - 中文 ↔ 英语（双向翻译）
    - 自动语言检测模式
  * 智能语言识别系统：
    - 法语检测：特殊字符 + 词汇特征 + 语法特征
    - 英语检测：排除法语干扰，基于词汇和语法特征
    - 解决"orange"等法英同形词的识别问题
    - 支持混合语言文本的主语言判断
  * 专业术语词典扩展：支持法语和英语建筑术语
  * 翻译模式选择：可手动指定翻译方向或使用自动检测

【界面优化】
  * 新增翻译模式选择区域（单选按钮）
  * 支持5种翻译模式：自动检测、中→法、法→中、中→英、英→中
  * 优化选项布局，提升用户体验
  * 实时显示当前使用的翻译模式

【语法和兼容性修复】
  * 修复所有正则表达式语法错误
  * 移除法语特殊字符以提高兼容性
  * 确保Python 3.7完全兼容
  * 完善编码处理和错误捕获

════════════════════════════════════════════════════════════════

版本 1.2.0 - 2025年5月
════════════════════════════════════════════════════════════════

【新功能】
  * 添加标签页界面，分离功能区域和版本信息
  * 新增"翻译选项"区域，可选择是否翻译CAD块内文字
  * 默认不翻译块内文字（推荐设置，保持图块标准化）
  * 优化界面布局，提升用户体验

【修复与改进】
  * 完全修复法语特殊字符编码问题
  * 解决 \\xc9crdn de contr\\xf4le → Écran de contrôle 转换
  * 增强文本安全解码/编码机制
  * 支持多种编码格式自动检测 (UTF-8, GBK, GB2312, CP1252)
  * 改进错误处理和日志记录
  * 修复Python 3.7兼容性问题（移除不支持的Unicode字符）

════════════════════════════════════════════════════════════════

版本 1.1.0 - 2025年5月
════════════════════════════════════════════════════════════════

【主要功能】
  * 全新GUI界面设计，操作更直观
  * 支持DXF文件中文到法语自动翻译
  * 实时翻译进度显示和详细日志
  * 自动生成翻译报告CSV文件
  * 建筑术语智能识别和上下文翻译

【核心特性】
  * 建筑专业术语词典优化
  * 网络连接检测，避免翻译中断
  * 多线程处理，界面不卡顿
  * 自动文件命名和时间戳
  * 支持模型空间和布局空间文本

【稳定性】
  * 异常处理机制完善
  * 翻译缓存机制，避免重复翻译
  * 安全的文件读写操作
  * 内存管理优化

════════════════════════════════════════════════════════════════

版本 1.0.0 - 2025年5月 (初始版本)
════════════════════════════════════════════════════════════════

【基础功能】
  * 基本的DXF文件中文文本提取
  * 简单的Google翻译集成
  * 命令行界面操作
  * 基础的文本替换功能

════════════════════════════════════════════════════════════════

【技术支持】
  联系人: 王一健
  电话: +225 0500902929
  
【使用建议】
  * 翻译前建议备份原文件
  * 翻译完成后在CAD中检查文字位置
  * 块内文字一般不需要翻译（标准图块符号）
  * 网络不稳定时可能影响翻译质量

【持续更新】
  本工具会根据实际使用情况持续优化和更新，
  如有问题或建议请及时反馈。

【已知问题修复记录】
  * v2.2.0: 修复所有正则表达式语法错误
  * v2.2.0: 完善多语言检测系统
  * v2.1.0: 修复法语特殊字符编码问题
  * v2.1.0: 修复Python 3.7 Unicode兼容性
  * v2.1.0: 添加CAD块内文字翻译选项

════════════════════════════════════════════════════════════════
        """
        
        self.changelog_text.insert('1.0', changelog_content.strip())
        self.changelog_text.config(state='disabled')  # 设为只读
        
        # 底部信息
        bottom_frame = ttk.Frame(changelog_main)
        bottom_frame.pack(fill='x', pady=(15, 0))
        
        info_label = tk.Label(bottom_frame, 
                             text="© 2025 Honsen非洲 - CAD多语言翻译工具 v2.3 | 内部使用版本", 
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

            # 自动根据选择的文件名设置输出名
            base_name = os.path.splitext(os.path.basename(filename))[0]
            now = datetime.now()
            timestamp = now.strftime('%Hh%M_%d-%m-%y')
            self.output_name.set(f"fr_{base_name}_{timestamp}")
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
    
    def log_message(self, message):
        """添加日志消息到队列"""
        self.log_queue.put(message)
    
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
                    self.log_text.insert(tk.END, message + "\n")
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
    
    def start_translation(self):
        if not self.validate_inputs():
            return
        if not self.check_internet_connection():
            messagebox.showerror("网络错误", "⚠️ 无法连接网络，请检查您的网络连接后重试。")
            self.log_message("⚠️ 网络中断，翻译终止")
            self.status_var.set("网络中断，已取消")
            self.progress.stop()
            self.start_button.config(state='normal')
            return
        
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
                translator = CADChineseTranslator(log_callback=self.log_message)
                
                # 获取翻译配置
                lang_config = self.translation_mode.get()
                
                translator.translate_cad_file(self.input_file.get(), output_file, 
                                            lang_config, self.translate_blocks.get())
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
            self.log_message(f"ERROR {message}")

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
