import ezdxf

class CADFileManager:
    def __init__(self):
        self.doc = None

    def open_file(self, input_file):
        """读取 DXF 文件"""
        try:
            self.doc = ezdxf.readfile(input_file)
            print(f"文件读取成功: {input_file}")
        except Exception as e:
            print(f"文件读取失败: {e}")
            return False
        return True

    def extract_text_entities(self, include_blocks=False):
        """提取所有文本实体"""
        items = []
        for space in [self.doc.modelspace()] + list(self.doc.layouts):
            for entity in space:
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    text = self.get_entity_text(entity)
                    if text:
                        items.append({
                            'entity': entity,
                            'original_text': text,
                            'layer': getattr(entity.dxf, 'layer', 'DEFAULT'),
                            'location': space.name if hasattr(space, 'name') else 'modelspace'
                        })
        if include_blocks:
            self.extract_text_from_blocks(items)
        return items

    def extract_text_from_blocks(self, items):
        """提取块内的文本实体"""
        for block in self.doc.blocks:
            if block.name.startswith('*'):  # 排除系统块
                continue
            for entity in block:
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    text = self.get_entity_text(entity)
                    if text:
                        items.append({
                            'entity': entity,
                            'original_text': text,
                            'layer': getattr(entity.dxf, 'layer', 'DEFAULT'),
                            'location': f'block:{block.name}'
                        })

    def get_entity_text(self, entity):
        """获取实体的文本内容"""
        try:
            return entity.dxf.text if hasattr(entity.dxf, 'text') else ""
        except Exception as e:
            print(f"获取文本失败: {e}")
            return ""
