import tkinter as tk
from tkinter import ttk, filedialog

class CADTranslatorGUI:
    def __init__(self, translator):
        self.translator = translator
        self.root = tk.Tk()
        self.root.title("CAD 中法互译工具")
        self.setup_ui()

    def setup_ui(self):
        # 设置窗口组件
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()

        ttk.Label(self.root, text="选择输入文件").pack()
        ttk.Entry(self.root, textvariable=self.input_file).pack()
        ttk.Button(self.root, text="浏览", command=self.browse_input_file).pack()

        ttk.Label(self.root, text="选择输出目录").pack()
        ttk.Entry(self.root, textvariable=self.output_dir).pack()
        ttk.Button(self.root, text="浏览", command=self.browse_output_dir).pack()

        self.start_button = ttk.Button(self.root, text="开始翻译", command=self.start_translation)
        self.start_button.pack()

        self.log_text = tk.Text(self.root)
        self.log_text.pack()

    def browse_input_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.input_file.set(filename)

    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)

    def start_translation(self):
        input_file = self.input_file.get()
        output_dir = self.output_dir.get()

        if not input_file or not output_dir:
            print("请选择文件和输出目录")
            return

        print(f"开始翻译文件: {input_file}")
        # 这里用的是简化的示例
        translated = self.translator.translate_text(input_file, "zh", "fr")
        self.log_text.insert(tk.END, f"翻译完成: {translated}\n")
        self.root.mainloop()
