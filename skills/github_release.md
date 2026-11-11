# GitHub Release 产物下载指南

**【触发词】** GitHub下载、release、安装包、jar、exe、产物、源码、git。

### ⚠️ 致命幻觉警告
绝对不要用 `wget` 或 `curl` 去直接下载 `https://github.com/用户/仓库` 网页！那是 HTML，不是文件。必须找 `browser_download_url`。

### 🛠️ 核心操作 SOP：从 API 获取直链
1. **探查最新版本**：
   执行 `curl -sL https://api.github.com/repos/<用户>/<仓库>/releases/latest`
2. **提取直链并下载**（推荐用 `execute_python` 解析 JSON，提取 `browser_download_url`）：
   `curl -L -f -o <目标文件> "<提取到的直链>"`
3. **🚨 国内网络加速（极其重要）**：
   如果下载速度极慢或超时，必须且立刻在直链前面加上镜像前缀：
   `https://ghproxy.com/https://github.com/.../releases/download/...`
4. **强制校验（必须执行）**：
   `ls -lh <目标文件>` 和 `file <目标文件>`。如果发现大小只有几 KB，或者类型是 HTML，说明被反爬拦截或需要登录。

### 🔄 失败后的补救
1. 如果 API 被限流或下载失败，立刻改用 `web_search` 搜索 `"<软件名> release 下载"`。
2. 寻找替代分发源：`Modrinth`、`Hangar`、`CurseForge`、官网。

### 🛠️ 拉取源代码 (Git Clone)
直接使用 Git，不要下网页：
`git clone --depth 1 https://github.com/用户/仓库.git <目标目录>`
*如果超时，使用镜像：*
`git clone --depth 1 https://ghproxy.com/https://github.com/用户/仓库.git <目标目录>`