import ezdxf
import re
import time
import csv
from googletrans import Translator
from datetime import datetime


class CADChineseTranslator:
    def __init__(self, log_callback=None):
        self.translator = Translator()
        self.translated_cache = {}
        self.log_callback = log_callback
        
        # 语言配置
        self.language_configs = {
            'zh_to_fr': {
                'source': 'zh',
                'target': 'fr',
                'name': '中文→法语',
                'context': self.get_architectural_context_fr()
            },
            'fr_to_zh': {
                'source': 'fr',
                'target': 'zh',
                'name': '法语→中文',
                'context': self.get_architectural_context_zh()
            },
            'zh_to_en': {
                'source': 'zh',
                'target': 'en',
                'name': '中文→英语',
                'context': self.get_architectural_context_en()
            },
            'en_to_zh': {
                'source': 'en',
                'target': 'zh',
                'name': '英语→中文',
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
        if not text:
            return ""

        try:
            if not isinstance(text, str):
                text = str(text)

            text = ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
            text.encode('utf-8')
            return text

        except Exception as e:
            self.log(f"⚠️ encode_text_safely 出错: {e}，正在强制清理字符")
            try:
                cleaned = ''.join(c for c in text if c.isprintable() and not (0xD800 <= ord(c) <= 0xDFFF))
                return cleaned
            except:
                return "??"

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

        decoded_text = self.decode_text_safely(text)
        cleaned = self.clean_text(decoded_text)

        if not cleaned or not cleaned.strip():
            self.log(f"跳过空文本或无效文本: \"{text}\"")
            return self.encode_text_safely(decoded_text)

        # 判断文本是否可读（防止乱码）
        printable_chars = sum(1 for char in cleaned if char.isprintable() or '\u4e00' <= char <= '\u9fff')
        if len(cleaned) > 0 and printable_chars / len(cleaned) < 0.5:
            self.log(f"跳过损坏文本(可读字符比例过低): \"{cleaned}\"")
            return self.encode_text_safely(decoded_text)

        if force_lang_config not in self.language_configs:
            self.log(f"无效的翻译配置: {force_lang_config}")
            return self.encode_text_safely(decoded_text)

        lang_config_key = force_lang_config
        lang_config = self.language_configs[lang_config_key]

        try:
            context = self.get_contextual_translation(cleaned, lang_config_key)
            self.log(f"翻译中 ({lang_config['name']}): {self.encode_text_safely(cleaned)}")
            if context != cleaned:
                self.log(f"提示术语: {self.encode_text_safely(context)}")

            # 发起翻译请求（不指定 src）
            result = self.translator.translate(cleaned, dest=lang_config['target'])

            raw_result = result.text
            raw_result = self.encode_text_safely(raw_result)  # 强制清理非法字符

            final = self.post_process_translation(raw_result, cleaned, lang_config_key)
            final = self.encode_text_safely(final)

            if final.strip() == cleaned.strip():
                self.log(f"⚠️ 可能网络中断或翻译失败，结果无变化: \"{cleaned}\"")
                raise ConnectionError("翻译无效")

            self.translated_cache[text] = final
            self.log(f"✔ 翻译完成 ({lang_config['name']}): \"{self.encode_text_safely(cleaned)}\" → \"{final}\"")
            time.sleep(0.5)
            return final

        except Exception as e:
            self.log(f"⚠️ 翻译异常，尝试备用方法: {e}")
            try:
                result = self.translator.translate(cleaned, src='auto', dest=lang_config['target'])
                raw_result = result.text
                raw_result = self.encode_text_safely(raw_result)
                final = self.post_process_translation(raw_result, cleaned, lang_config_key)
                final = self.encode_text_safely(final)

                self.translated_cache[text] = final
                self.log(f"✔ 备用翻译成功: \"{self.encode_text_safely(cleaned)}\" → \"{final}\"")
                time.sleep(0.5)
                return final
            except Exception as e2:
                self.log(f"❌ 备用翻译失败: {e2} → 保持原文: \"{self.encode_text_safely(cleaned)}\"")
                return self.encode_text_safely(text)

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
                    'original_text': self.encode_text_safely(item['original_text']),
                    'translated_text': self.encode_text_safely(item.get('translated_text', ''))
                })

    def extract_text_entities(self, doc, lang_config, include_blocks=False):
        """提取所有需要翻译的文本实体，不进行语言检测"""
        items = []
        # 处理模型空间和布局空间
        for space in [doc.modelspace()] + list(doc.layouts):
            for e in space:
                if e.dxftype() in ['TEXT', 'MTEXT']:
                    txt = self.get_entity_text(e)
                    if txt and txt.strip():  # 只要有文本就处理，不检测语言
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
                        if txt and txt.strip():  # 只要有文本就处理，不检测语言
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