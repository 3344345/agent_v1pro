场景: 网页自动化与复杂交互
说明: 系统为你提供了三层网页操作武器。请按照“DOM -> 交互 -> 视觉”的顺序降级使用。

【第一层：导航与观察 (首选)】
1. `browser_goto` 打开网页。
2. `browser_snapshot` 获取纯文本，分析页面结构。
3. `browser_evaluate` 仅在需要抓取复杂 DOM（如表格、列表）时使用。严禁在最外层写 `return`！

【第二层：原生物理交互 (最稳)】
- 必须优先使用原生工具，它们自带“自动等待”机制。
- `browser_fill("#search-input", "内容")` 填写输入框。
- `browser_click("text=搜索")` 或 `browser_click("#btn")` 模拟点击。
- `browser_press("Enter")` 模拟键盘回车。

【第三层：视觉 OCR 兜底 (终极武器)】
- 适用场景：页面是纯图片、Canvas、极度反混淆，导致 `snapshot` 没字，且 `browser_click` 报错找不到元素时。
- 提取文字：`browser_ocr_extract()`。
- 视觉点击：`browser_ocr_click("登录")`（系统会自动截图、识别坐标并物理点击）。
- ⚠️【死线】：OCR 速度慢且只认当前屏幕。只要能通过选择器点击，**绝对禁止**用 OCR！

验证: 
- 遇到 `Illegal return statement` 报错，立刻去掉 `evaluate` 里的顶层 `return`。
- 如果点击没反应，用 `browser_wait(2)` 等两秒再试。

## 弹窗拦截与遮挡处理
遇到 `browser_click` 超时，90% 是因为页面有 Cookie 弹窗或广告。
1. 先调用 `browser_snapshot(interactive_only=True)`，寻找有没有“Accept all”、“同意”、“关闭 (Close)”之类的按钮，先把它点了。
2. 如果找不到弹窗，尝试 `browser_click(force=True)`。