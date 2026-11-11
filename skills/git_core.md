# Git 原生操作指南 (Git Core)

**【触发词】** git、clone、仓库、源码、拉取、分支、提交。

### ⚠️ 致命幻觉警告
不要用 curl 或 wget 去下载 `.git` 结尾的网页，那是乱码。

### 🛠️ 核心操作 SOP
1. **极速克隆（首选）**：只拉取最新代码，不带历史记录，防超时：
   `git clone --depth 1 <仓库URL> <目标目录>`
2. **查看状态**：如果目录已存在，进入后 `git pull` 或查看状态 `git status`。
3. **如果有超大文件或历史丢失**：移除 `--depth 1` 重新克隆。

### 🛡️ 异常处理
- 如果遇到 `Connection timed out` 或网络错误，立刻加上代理前缀重试：
  `git clone --depth 1 https://ghproxy.com/<仓库URL> <目标目录>`