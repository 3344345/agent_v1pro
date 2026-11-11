# 文件下载通用法则与安全校验 (Download Core)

**【触发词】** 下载、download、镜像、获取文件、保存到、安装包。

### 🚨 铁律 1：禁止复合命令与死等
绝对禁止使用 `wget -O file || curl -L -o file`！这会导致假成功。
单步使用 `curl -L -f -C - -o <路径> "<直链>"`，如果网络差，加上 `--connect-timeout 10 --max-time 1800`。

### 🚨 铁律 2：国内镜像加速源（开发常备）
如果下载遭遇超时或速度极慢，绝对不要死磕，立刻替换为国内镜像：
1. **HuggingFace (模型)**：将 `https://huggingface.co/` 替换为 `https://hf-mirror.com/`
2. **Python (pip)**：安装命令加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`（清华）或 `-i https://mirrors.cloud.tencent.com/pypi/simple`（腾讯）
3. **Ubuntu/Debian 软件源**：将 `archive.ubuntu.com` 替换为 `mirrors.aliyun.com` 或 `mirrors.tuna.tsinghua.edu.cn`

### 🚨 铁律 3：大厂软件必须走官方 CDN（禁止去 GitHub 瞎猜）
如果你要下载以下知名软件，**绝对不要去 GitHub 查 Release**，它们不放在那里。直接使用以下官方直链：
- **VS Code (Linux deb)**：`https://update.code.visualstudio.com/latest/linux-deb-x64/stable`
- **VS Code (Windows exe)**：`https://update.code.visualstudio.com/latest/win32-x64-user/stable`
- **Chrome (Linux deb)**：`https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`
- **Docker 安装脚本**：`https://get.docker.com`
- **NVM (Node版本管理器)**：`https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh`

### 🚨 铁律 4：跨界处理（遇到 GitHub 链接怎么办）
在通用下载任务中，如果你发现获取到的链接包含 `github.com`：
1. **如果链接是网页形式**（如 `https://github.com/user/repo` 或带 `releases/latest` 但没有具体文件名）：**绝对禁止直接用 curl 下载**！请立刻切换到 GitHub 专属规则（调用 API 提取 `browser_download_url`）。
2. **如果链接是真实的文件直链**（包含 `/releases/download/`）：请用 `curl -L -f` 下载，但**必须加上国内镜像前缀**：
   `curl -L -f -o <路径> "https://ghproxy.com/<原GitHub直链>"`

### 🚨 铁律5：不要被 `file` 命令骗了！
`file` 命令只能识别文件头。一个下载了 10% 的 `.deb` 文件，`file` 依然会报 `Debian binary package`。
你必须结合**常识基线**来判断：
- VS Code / Chrome 的 `.deb` 包通常在 **80MB 以上**。
- 如果文件大小只有几 MB 或十几 MB，说明绝对没下完。
遇到这种情况，必须立刻删除残骸文件，重新下载。

### 🛠️ 标准下载 SOP
1. **下载**：使用 `execute_command` 运行 `curl -L -f -o <目标路径> "<直链>"`。
2. **强制校验**：
   - `ls -lh <目标路径>` 看大小（几KB必是假页面）。
   - `file <目标路径>` 看类型（若是 `HTML document` 立刻宣告失败）。
3. **反爬补救**：如果是 HTML，改用 `execute_python` 的 `requests` 加上 `User-Agent` 头重试。