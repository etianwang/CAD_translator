import PyInstaller.__main__
import os
import glob
import sys

# 获取当前目录
current_dir = os.getcwd()

# 1. 自动收集所有需要打包的非 Python 数据文件
data_files = []
file_patterns = ['*.yaml', '*.json', '*.ico', '*.txt', '*.md']
exclude_patterns = ['*.py', '*.exe', '*.spec', '*.log', '*.csv', '*.dxf', '*.dwg']

print("🔍 正在扫描数据文件...")
for pattern in file_patterns:
    files = glob.glob(os.path.join(current_dir, pattern))
    for file in files:
        filename = os.path.basename(file)
        is_excluded = False
        for exc in exclude_patterns:
            if filename.endswith(exc.replace('*', '')):
                is_excluded = True
                break
        
        if not is_excluded and os.path.isfile(file):
            # 格式: (源文件绝对路径, 目标相对路径)
            data_files.append((file, '.'))
            print(f"   ✅ 已添加: {filename}")

if not data_files:
    print("⚠️ 警告: 未找到任何数据文件 (yaml, json, ico)，请检查当前目录。")

# 2. 构建 --add-data 参数字符串
# Windows 必须使用分号 (;) 作为源和目标的内部分隔符
# 多个文件之间用逗号分隔（由 PyInstaller 列表处理），但在单个字符串参数中：
# 格式应为: "file1;.;file2;.;file3;."

if sys.platform.startswith('win'):
    separator = ';'
else:
    separator = ':'

# 构建列表: ["src1;dest", "src2;dest", ...]
# PyInstaller 的 run 函数接受一个列表，每个元素是一个完整的 "src;dest" 字符串
add_data_args = []
for src, dst in data_files:
    add_data_args.append(f"{src}{separator}{dst}")

# 3. 定义 PyInstaller 基础参数
args = [
    'main.py',
    '--name=Honsen_CAD_Translator_v2.2',
    '--onefile',
    '--windowed',
    '--noconfirm',
    '--clean',
]

# 添加图标 (如果存在)
icon_path = os.path.join(current_dir, 'ico.ico')
if os.path.exists(icon_path):
    args.append(f'--icon={icon_path}')
else:
    print("⚠️ 未找到 ico.ico，将使用默认图标。")

# 添加隐藏导入
hidden_imports = ['ezdxf', 'googletrans', 'deepl', 'openai', 'yaml', 'text_cleaning_utils']
for imp in hidden_imports:
    args.append(f'--hidden-import={imp}')

# 【关键修复】动态添加 --add-data 参数
# 注意：PyInstaller.__main__.run 接收的是参数列表
# 每个 --add-data 应该作为一个独立的参数项，或者合并为一个长字符串取决于调用方式
# 官方推荐方式是将所有数据对合并成一个字符串传给 --add-data，或者多次调用
# 在这里，我们将所有文件合并成一个字符串传给 --add-data，使用操作系统正确的分隔符连接“对”，
# 但实际上 PyInstaller 命令行解析器期望的是：--add-data "src1;dest1;src2;dest2" (Windows)
# 或者更稳妥的方式：为每个文件添加一个 --add-data 参数？
# 不，PyInstaller 允许在一个 --add-data 中通过 ; 分隔多组 (Windows)，但语法容易混淆。
# 最稳妥的方法是：为每个文件生成一个独立的 --add-data 参数。

for src, dst in data_files:
    args.append(f"--add-data={src}{separator}{dst}")

print("\n🚀 开始打包...")
print(f"📂 工作目录: {current_dir}")
print(f"📦 包含的数据文件数量: {len(data_files)}")
print(f"🔧 使用的分隔符: '{separator}'")
print(f"📝 完整参数预览: {' '.join(args[:5])} ... (省略中间参数)")

try:
    PyInstaller.__main__.run(args)
    print("\n✅ 打包成功！")
    print(f"📁 生成的文件位于: {os.path.join(current_dir, 'dist')}")
except Exception as e:
    print(f"\n❌ 打包失败: {e}")
    import traceback
    traceback.print_exc()