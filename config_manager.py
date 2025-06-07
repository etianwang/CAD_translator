import json
import os

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.deepl_api_key = None
        self.chatgpt_api_key = None

    def load_api_keys(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.deepl_api_key = config.get("deepl_key", "")
                    self.chatgpt_api_key = config.get("chatgpt_key", "")
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_api_keys(self, deepl_key, chatgpt_key):
        try:
            config = {
                "deepl_key": deepl_key.strip(),
                "chatgpt_key": chatgpt_key.strip()
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")