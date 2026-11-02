import os
import sys
import threading
import subprocess
import platform
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import time
import re
import shutil

# ================= 双语字典 =================
TEXTS = {
    "zh": {
        "title": "Agent V1 Pro 智能配置向导",
        "lang_label": "界面语言:",
        "warn_text": "⚠️ 注意：切换推理模型（Ollama ↔ 云端）不会丢失记忆。\n但如果切换 Embedding 后端（如在 Ollama 与 fastembed 间切换），会导致向量维度不匹配。\n若需切换 Embedding 后端，必须在终端执行 rm -rf data/chroma 清空旧记忆！",
        "frame_backend": "1. 选择推理后端",
        "radio_ollama": "Ollama (推荐，全自动本地部署)",
        "radio_cloud": "云端 API (轻量，纯 Python 本地向量)",
        "frame_config": "2. 配置参数",
        "radio_pull": "在线自动拉取 (需网络)",
        "radio_import": "本地 GGUF 导入",
        "lbl_planner_init": "Planner 模型: 未选",
        "lbl_router_init": "Router 模型: 未选",
        "lbl_planner_ok": "Planner: {}",
        "lbl_router_ok": "Router: {}",
        "btn_browse": "浏览",
        "lbl_api_key": "API Key:",
        "lbl_cloud_hint": "* 将使用 fastembed 进行轻量级本地记忆检索",
        "frame_agent_lang": "3. Agent 回答语言 (Agent Language)",
        "radio_agent_zh": "中文 (Chinese)",
        "radio_agent_en": "English",
        "btn_install": "开始自动化安装",
        "btn_installing": "安装中...",
        "btn_done": "✅ 完成",
        "btn_fail": "❌ 失败",
        "msg_success_title": "成功",
        "msg_success_text": "环境配置完毕！请关闭窗口并在终端运行 ./run.sh",
        "msg_err_title": "安装失败",
        "msg_missing_gguf": "请选择本地 Planner 和 Router 的 GGUF 文件！",
        "log_ollama_prep": "[1/5] 准备本地引擎 (Ollama)...",
        "log_ollama_install": "未检测到 Ollama，正在自动安装...",
        "log_ollama_done": "✅ Ollama 安装完成。",
        "log_pulling": "⬇️ 正在拉取 {}...",
        "log_timeout": "{} 下载超时。",
        "log_import_prep": "正在向 Ollama 导入本地 GGUF...",
        "log_cloud_prep": "[1/5] 正在生成云端配置...",
        "log_cloud_done": "✅ 配置生成完毕，完全无 Ollama 依赖。",
        "log_venv": "\n[2/5] 正在构建 Python 虚拟环境...",
        "log_deps": "\n[3/5] 正在安装 Python 依赖包...",
        "log_playwright": "\n[4/5] 正在下载 Playwright 浏览器内核 (用于网页操作)...",
        "log_playwright_done": "✅ Playwright 浏览器准备就绪。",
        "log_fastembed": "正在下载轻量级向量模型 (约 95MB)...",
        "log_fastembed_done": "✅ 轻量向量模型准备就绪！",
        "log_init": "\n[5/5] 初始化目录...",
        "log_finish": "\n🎉 安装成功！请关闭窗口并在终端运行 ./run.sh"
    },
    "en": {
        "title": "Agent V1 Pro Setup Wizard",
        "lang_label": "UI Language:",
        "warn_text": "⚠️ Warning: Switching inference models (Ollama ↔ Cloud) does not lose memory.\nHowever, switching the Embedding backend (e.g., between Ollama and fastembed) causes vector dimension mismatch.\nIf you switch Embedding backend, you MUST run `rm -rf data/chroma` to clear old memory!",
        "frame_backend": "1. Select Inference Backend",
        "radio_ollama": "Ollama (Recommended, Auto local deploy)",
        "radio_cloud": "Cloud API (Lightweight, fastembed for local memory)",
        "frame_config": "2. Configuration",
        "radio_pull": "Auto Pull (Requires network)",
        "radio_import": "Import Local GGUF",
        "lbl_planner_init": "Planner Model: Not selected",
        "lbl_router_init": "Router Model: Not selected",
        "lbl_planner_ok": "Planner: {}",
        "lbl_router_ok": "Router: {}",
        "btn_browse": "Browse",
        "lbl_api_key": "API Key:",
        "lbl_cloud_hint": "* Will use fastembed for lightweight local memory retrieval",
        "frame_agent_lang": "3. Agent Language",
        "radio_agent_zh": "中文 (Chinese)",
        "radio_agent_en": "English",
        "btn_install": "Start Automatic Setup",
        "btn_installing": "Installing...",
        "btn_done": "✅ Done",
        "btn_fail": "❌ Failed",
        "msg_success_title": "Success",
        "msg_success_text": "Environment configured! Close this window and run ./run.sh",
        "msg_err_title": "Setup Failed",
        "msg_missing_gguf": "Please select both Planner and Router GGUF files!",
        "log_ollama_prep": "[1/5] Preparing local engine (Ollama)...",
        "log_ollama_install": "Ollama not found, installing automatically...",
        "log_ollama_done": "✅ Ollama installed successfully.",
        "log_pulling": "⬇️ Pulling {}...",
        "log_timeout": "{} download timeout.",
        "log_import_prep": "Importing local GGUF into Ollama...",
        "log_cloud_prep": "[1/5] Generating cloud configuration...",
        "log_cloud_done": "✅ Config generated, completely Ollama-free.",
        "log_venv": "\n[2/5] Building Python virtual environment...",
        "log_deps": "\n[3/5] Installing Python dependencies...",
        "log_playwright": "\n[4/5] Downloading Playwright browser (for web tools)...",
        "log_playwright_done": "✅ Playwright browser ready.",
        "log_fastembed": "Downloading lightweight embedding model (~95MB)...",
        "log_fastembed_done": "✅ Embedding model ready!",
        "log_init": "\n[5/5] Initializing directories...",
        "log_finish": "\n🎉 Setup completed successfully! Close this window and run ./run.sh"
    }
}

class InstallWizard:
    def __init__(self, root):
        self.root = root
        self.root.geometry("700x720")
        self.root.configure(padx=20, pady=10)
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.gguf_planner = None
        self.gguf_router = None
        self.current_lang = "zh" 
        
        self._build_ui()
        self._apply_language()

    def _build_ui(self):
        # 顶部：标题 + 语言切换
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", pady=(0, 5))
        
        self.lbl_title = tk.Label(top_frame, text="", font=("Arial", 16, "bold"))
        self.lbl_title.pack(side="left")
        
        self.lang_combo = ttk.Combobox(top_frame, values=["中文", "English"], width=8, state="readonly")
        self.lang_combo.current(0)
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        # 警告标签
        self.warn_frame = tk.Frame(self.root, bg="#fff3cd", highlightbackground="#ffeeba", highlightthickness=1)
        self.warn_frame.pack(fill="x", pady=(0, 10))
        self.lbl_warn = tk.Label(self.warn_frame, text="", bg="#fff3cd", fg="#856404", font=("Arial", 10), justify="left", pady=5, padx=5)
        self.lbl_warn.pack(fill="x")

        # 模块 1：推理后端
        self.frame_mode = tk.LabelFrame(self.root, text="")
        self.frame_mode.pack(fill="x", pady=5)

        self.mode_var = tk.StringVar(value="ollama")
        self.radio_ollama = tk.Radiobutton(self.frame_mode, text="", variable=self.mode_var, value="ollama", command=self._toggle_mode)
        self.radio_ollama.pack(anchor="w")
        self.radio_cloud = tk.Radiobutton(self.frame_mode, text="", variable=self.mode_var, value="cloud", command=self._toggle_mode)
        self.radio_cloud.pack(anchor="w")

        # 模块 2：动态配置区
        self.frame_config = tk.LabelFrame(self.root, text="")
        self.frame_config.pack(fill="x", pady=5)

        # 2.1 Ollama 配置区
        self.frame_ollama = tk.Frame(self.frame_config)
        self.ollama_source = tk.StringVar(value="pull")
        self.radio_pull = tk.Radiobutton(self.frame_ollama, text="", variable=self.ollama_source, value="pull", command=self._toggle_ollama_source)
        self.radio_pull.pack(anchor="w")
        self.radio_import = tk.Radiobutton(self.frame_ollama, text="", variable=self.ollama_source, value="import", command=self._toggle_ollama_source)
        self.radio_import.pack(anchor="w")
        
        self.frame_import = tk.Frame(self.frame_ollama)
        self.lbl_planner = tk.Label(self.frame_import, text="", fg="#cf222e")
        self.lbl_router = tk.Label(self.frame_import, text="", fg="#cf222e")
        self.btn_browse_planner = tk.Button(self.frame_import, text="", command=lambda: self._browse("planner"))
        self.btn_browse_router = tk.Button(self.frame_import, text="", command=lambda: self._browse("router"))
        
        self.lbl_planner.grid(row=0, column=0, sticky="w", pady=2)
        self.btn_browse_planner.grid(row=0, column=1)
        self.lbl_router.grid(row=1, column=0, sticky="w", pady=2)
        self.btn_browse_router.grid(row=1, column=1)

        # 2.2 云端 API 配置区
        self.frame_cloud = tk.Frame(self.frame_config)
        self.lbl_api_key = tk.Label(self.frame_cloud, text="")
        self.lbl_api_key.pack(side="left")
        self.ent_api = tk.Entry(self.frame_cloud, width=40, show="*")
        self.ent_api.pack(side="left", padx=5)
        self.lbl_cloud_hint = tk.Label(self.frame_cloud, text="", fg="#6b7280")
        self.lbl_cloud_hint.pack(anchor="w", pady=(5,0))

        # 2.3 Agent 语言配置区
        self.frame_agent_lang = tk.Frame(self.frame_config)
        self.agent_lang_var = tk.StringVar(value="zh")
        self.radio_agent_zh = tk.Radiobutton(self.frame_agent_lang, text="", variable=self.agent_lang_var, value="zh")
        self.radio_agent_en = tk.Radiobutton(self.frame_agent_lang, text="", variable=self.agent_lang_var, value="en")
        self.radio_agent_zh.pack(anchor="w")
        self.radio_agent_en.pack(anchor="w")

        # 模块 3：日志
        self.log_text = scrolledtext.ScrolledText(self.root, height=8, state="disabled", bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(fill="both", expand=True, pady=10)

        self.btn_install = tk.Button(self.root, text="", bg="#0969da", fg="white", font=("Arial", 12, "bold"), command=self.start_install)
        self.btn_install.pack(pady=5)

    def _on_lang_change(self, event):
        self.current_lang = "zh" if self.lang_combo.current() == 0 else "en"
        self._apply_language()

    def _apply_language(self):
        t = TEXTS[self.current_lang]
        self.root.title(t["title"])
        self.lbl_title.config(text=t["title"])
        self.lbl_warn.config(text=t["warn_text"])
        
        self.frame_mode.config(text=t["frame_backend"])
        self.radio_ollama.config(text=t["radio_ollama"])
        self.radio_cloud.config(text=t["radio_cloud"])
        
        self.frame_config.config(text=t["frame_config"])
        self.radio_pull.config(text=t["radio_pull"])
        self.radio_import.config(text=t["radio_import"])
        
        if self.gguf_planner:
            self.lbl_planner.config(text=t["lbl_planner_ok"].format(os.path.basename(self.gguf_planner)))
        else:
            self.lbl_planner.config(text=t["lbl_planner_init"])
            
        if self.gguf_router:
            self.lbl_router.config(text=t["lbl_router_ok"].format(os.path.basename(self.gguf_router)))
        else:
            self.lbl_router.config(text=t["lbl_router_init"])
            
        self.btn_browse_planner.config(text=t["btn_browse"])
        self.btn_browse_router.config(text=t["btn_browse"])
        
        self.lbl_api_key.config(text=t["lbl_api_key"])
        self.lbl_cloud_hint.config(text=t["lbl_cloud_hint"])
        
        self.frame_agent_lang.config(text=t["frame_agent_lang"])
        self.radio_agent_zh.config(text=t["radio_agent_zh"])
        self.radio_agent_en.config(text=t["radio_agent_en"])
        
        self.btn_install.config(text=t["btn_install"])
        self._toggle_mode()

    def _toggle_mode(self):
        mode = self.mode_var.get()
        # 隐藏所有配置区
        self.frame_ollama.pack_forget()
        self.frame_cloud.pack_forget()
        self.frame_agent_lang.pack_forget()

        # 根据模式显示配置
        if mode == "ollama":
            self.frame_ollama.pack(fill="x")
            self._toggle_ollama_source()
        else:
            self.frame_cloud.pack(fill="x")
            
        # Agent 语言配置一直显示在最后
        self.frame_agent_lang.pack(fill="x", pady=(10, 0))

    def _toggle_ollama_source(self):
        if self.ollama_source.get() == "import":
            self.frame_import.pack(fill="x", pady=5)
        else:
            self.frame_import.pack_forget()

    def _browse(self, target):
        filepath = filedialog.askopenfilename(filetypes=[("GGUF", "*.gguf")])
        if filepath:
            t = TEXTS[self.current_lang]
            if target == "planner":
                self.gguf_planner = filepath
                self.lbl_planner.config(text=t["lbl_planner_ok"].format(os.path.basename(filepath)), fg="#1a7f37")
            else:
                self.gguf_router = filepath
                self.lbl_router.config(text=t["lbl_router_ok"].format(os.path.basename(filepath)), fg="#1a7f37")

    def log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update()

    def start_install(self):
        t = TEXTS[self.current_lang]
        self.btn_install.config(state="disabled", text=t["btn_installing"])
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        threading.Thread(target=self._run_install, daemon=True).start()

    def _pull_model(self, model_name):
        t = TEXTS[self.current_lang]
        self.log(t["log_pulling"].format(model_name))
        process = subprocess.Popen(["ollama", "pull", model_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        last_time = time.time()
        for line in process.stdout:
            clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip()
            if clean:
                self.log(clean)
                last_time = time.time()
            if time.time() - last_time > 120:
                process.kill()
                raise TimeoutError(t["log_timeout"].format(model_name))
        process.wait()

    def _run_install(self):
        t = TEXTS[self.current_lang]
        try:
            mode = self.mode_var.get()
            env_file = os.path.join(self.base_dir, ".env")
            
            # 无论哪种模式，写入 Agent 语言
            lang_config = f"AGENT_LANG={self.agent_lang_var.get()}\n"

            # ================= 1. 生成 .env 与 模型准备 =================
            if mode == "ollama":
                self.log(t["log_ollama_prep"])
                if subprocess.run(["which", "ollama"], capture_output=True).returncode != 0:
                    self.log(t["log_ollama_install"])
                    subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh", "-o", "/tmp/ollama.sh"], check=True)
                    subprocess.run(["sh", "/tmp/ollama.sh"], check=True)
                    self.log(t["log_ollama_done"])

                self._pull_model("bge-m3")
                
                if self.ollama_source.get() == "import":
                    if not self.gguf_planner or not self.gguf_router:
                        raise Exception(t["msg_missing_gguf"])
                    
                    self.log(t["log_import_prep"])
                    models_dir = os.path.join(self.base_dir, "models")
                    os.makedirs(models_dir, exist_ok=True)
                    p_path = os.path.join(models_dir, "planner.gguf")
                    r_path = os.path.join(models_dir, "router.gguf")
                    shutil.copy(self.gguf_planner, p_path)
                    shutil.copy(self.gguf_router, r_path)
                    
                    with open("Modelfile", "w") as f: f.write(f"FROM {p_path}\n")
                    subprocess.run(["ollama", "create", "agent-planner", "-f", "Modelfile"], check=True)
                    with open("Modelfile", "w") as f: f.write(f"FROM {r_path}\n")
                    subprocess.run(["ollama", "create", "agent-router", "-f", "Modelfile"], check=True)
                    os.remove("Modelfile")
                    planner_name, router_name = "agent-planner", "agent-router"
                else:
                    self._pull_model("qwen2.5:7b")
                    self._pull_model("qwen2.5:1.5b-instruct")
                    planner_name, router_name = "qwen2.5:7b", "qwen2.5:1.5b-instruct"

                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(lang_config)
                    f.write("AGENT_LLM_BACKEND=ollama\nAGENT_ROUTER_BACKEND=ollama\n")
                    f.write("OLLAMA_URL=http://localhost:11434\n")
                    f.write(f"PLANNER_MODEL={planner_name}\nROUTER_MODEL={router_name}\n")
                    f.write("EMBED_BACKEND=ollama\nEMBED_MODEL=bge-m3\n")

            elif mode == "cloud":
                self.log(t["log_cloud_prep"])
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(lang_config)
                    f.write("AGENT_LLM_BACKEND=cloud_api\nAGENT_ROUTER_BACKEND=cloud_api\n")
                    f.write("AGENT_API_BASE=https://api.deepseek.com/v1\n")
                    f.write(f"AGENT_API_KEY={self.ent_api.get().strip()}\n")
                    f.write("AGENT_CLOUD_MODEL=deepseek-chat\n")
                    f.write("EMBED_BACKEND=fastembed\n")
                self.log(t["log_cloud_done"])

            # ================= 2. 建虚拟环境 =================
            self.log(t["log_venv"])
            venv_dir = os.path.join(self.base_dir, ".venv")
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
            pip_bin = os.path.join(venv_dir, "Scripts", "pip.exe") if sys.platform == "win32" else os.path.join(venv_dir, "bin", "pip")
            
            # ================= 3. 安装依赖 =================
            self.log(t["log_deps"])
            subprocess.run([pip_bin, "install", "-r", "requirements.txt"], check=True)

            # ================= 4. 自动下载 Playwright 浏览器 =================
            self.log(t["log_playwright"])
            python_bin = os.path.join(venv_dir, "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(venv_dir, "bin", "python3")
            subprocess.run([python_bin, "-m", "playwright", "install", "chromium"], check=True)
            self.log(t["log_playwright_done"])
            
            # 如果选了云端，预热下载一下向量模型
            if mode == "cloud":
                self.log(t["log_fastembed"])
                test_script = "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-zh-v1.5').embed(['test']))"
                subprocess.run([python_bin, "-c", test_script], check=True)
                self.log(t["log_fastembed_done"])

            # ================= 5. 初始化目录 =================
            self.log(t["log_init"])
            for d in ["data/chroma", "logs", "skills"]:
                os.makedirs(os.path.join(self.base_dir, d), exist_ok=True)

            self.log(t["log_finish"])
            self.root.after(0, lambda: self.btn_install.config(state="normal", text=t["btn_done"], bg="#1a7f37"))
            self.root.after(0, lambda: messagebox.showinfo(t["msg_success_title"], t["msg_success_text"]))

        except Exception as e:
            self.log(f"\n❌ {str(e)}")
            self.root.after(0, lambda: self.btn_install.config(state="normal", text=t["btn_fail"], bg="#cf222e"))
            self.root.after(0, lambda: messagebox.showerror(t["msg_err_title"], str(e)))

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallWizard(root)
    root.mainloop()