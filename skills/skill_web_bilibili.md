# B站 (Bilibili) 专属自动化指南

**【触发词】** B站、Bilibili、哔哩哔哩、BV号、UP主、视频搜索。

### 🎯 搜索与列表点击（一击必杀）
1. **搜索**：输入框选择器固定为 `.nav-search-input`，填完后必须 `browser_press("Enter")`。
2. **精准点击视频**：视频标题通常不在 `<a>` 标签里，而在 `<h3>` 里，且链接的 `href` 必定包含 `/video/`。
   **终极代码**：直接用 `browser_evaluate` 执行：
   `document.querySelector('a[href*="/video/"]')?.click()`
   *或者匹配文字：*
   `Array.from(document.querySelectorAll('h3')).find(el => el.innerText.includes('关键词'))?.closest('a')?.click()`

### 🏁 B站任务成功的绝对信号
如果在点击后，你看到以下情况，**立刻宣告任务完成，绝对禁止再 `wait`**：
1. URL 变成了 `https://www.bilibili.com/video/BVxxxx`。
2. 页面出现了视频播放器、弹幕输入框、UP主“关注”按钮。
3. 快照里有 `00:02 / 00:15` 这种播放时间戳。