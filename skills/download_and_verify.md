场景: 下载 GitHub / SpigotMC 等站点上的文件并验证
步骤:
  1. 优先用 curl -L -o，不用 wget -O；两者对 -H 的语义不同
  2. 下载后立即 file <文件> 看类型、ls -lh <文件> 看大小
  3. file 显示 HTML 或大小明显低于预期（如几 KB 的 jar），判定失败
  4. 失败后上网搜索替代来源：Hangar、GitHub releases、Modrinth
验证: file 显示对应类型（jar 应为 "Java archive data"），大小在合理区间