# -*- coding: utf-8 -*-
"""把当前应用打包成零依赖的单文件 HTML，方便直接发给别人试用。"""

from __future__ import annotations

import base64
import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:\工厂个人计件软件")
APP = ROOT / "app"
DIST = ROOT / "dist"
VERSION = "1.0.3"

DIST.mkdir(parents=True, exist_ok=True)
OUT_HTML = DIST / "计件通-单文件演示版.html"
OUT_TXT = DIST / "使用说明.txt"
OUT_ZIP = DIST / "计件通-单文件演示版.zip"

html = (APP / "index.html").read_text(encoding="utf-8")
css = (APP / "styles.css").read_text(encoding="utf-8")
icon_b64 = base64.b64encode((APP / "icons" / "icon-192.png").read_bytes()).decode("ascii")

# 移除依赖外部文件的标签
for pattern in [
    r'\s*<link rel="manifest"[^>]*>',
    r'\s*<link rel="icon"[^>]*>',
    r'\s*<link rel="apple-touch-icon"[^>]*>',
    r'\s*<link rel="stylesheet"[^>]*>',
    r'\s*<script src="\./(?:vendor/qrcode|core|pages-worker|pages-main|app)\.js[^"]*"\s*></script>',
]:
    html = re.sub(pattern, "", html)

# 内联样式与图标
html = html.replace(
    "</head>",
    f'  <link rel="icon" href="data:image/png;base64,{icon_b64}" />\n'
    f"  <style>\n{css}\n  </style>\n</head>",
)

# 内联脚本（顺序不能变）
sources = [
    "vendor/qrcode.js",
    "vendor/jsQR.js",
    "core.js",
    "pages-worker.js",
    "pages-main.js",
    "app.js",
]
blocks = []
for name in sources:
    js = (APP / name).read_text(encoding="utf-8").replace("</script", "<\\/script")
    blocks.append(f'  <script data-source="{name}">\n{js}\n  </script>')

html = html.replace("</body>", "\n".join(blocks) + "\n</body>")
html = html.replace(
    "<title>计件通 · 个人计件统计</title>",
    "<title>计件通 · 个人计件统计（单文件演示版）</title>\n"
    f"  <meta name=\"jitong-version\" content=\"{VERSION}\" />",
)
html = "<!-- 计件通单文件演示版，由 tools/build_portable.py 生成 -->\n" + html
OUT_HTML.write_text(html, encoding="utf-8")

guide = f"""计件通 · 单文件演示版 v{VERSION}
============================================================

【怎么打开】
1. 把“计件通-单文件演示版.html”保存到电脑。
2. 双击文件，用 Chrome 或 Edge 打开。
3. 不需要安装 Python，不需要启动服务器，断网也能打开。

【演示账号】
- 肖宏：写真打印
- 王坤：亚克力裁切
- 梁建华：过膜过板
- 肖尾珍：综合岗位
- 李厂长：管理端（新建订单、异常确认、人员矩阵、报表）

【这是什么】
这是一个可操作的单文件演示版，用来给客户、同事或管理层看流程和界面。
报工、订单、统计、异常确认、CSV 导出都可以操作。

【重要限制】
1. 数据只保存在当前浏览器（localStorage），不上传服务器。
2. 换电脑、换浏览器或清理缓存后，数据不会跟过去。
3. 不同手机之间不共享数据；这不是多人协同版。
4. 单文件版不支持相机扫码和 PWA 安装，请用“演示流转卡”或手动输入订单号。
5. 单文件版不能直接用于正式生产计件。

【如果要给工厂正式使用】
需要部署后端 + 数据库 + HTTPS + 账号权限，建议：
- 工人端：微信小程序
- 管理端：Web
- 服务端：FastAPI / Spring Boot + PostgreSQL
- 数据共享、离线队列、审批留痕、每日备份

【手机打开】
可以把 HTML 发到手机，用浏览器打开；部分微信/文件管理器会限制本地 HTML，
建议用“用其他应用打开”选择 Chrome/Edge/Safari。
如果要让多台手机访问同一套数据，必须部署服务器版本，不能靠这个单文件。

计件通项目目录：D:\\工厂个人计件软件
"""
OUT_TXT.write_text(guide, encoding="utf-8-sig")

with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(OUT_HTML, arcname=OUT_HTML.name)
    zf.write(OUT_TXT, arcname=OUT_TXT.name)

print("html", OUT_HTML, OUT_HTML.stat().st_size)
print("zip ", OUT_ZIP, OUT_ZIP.stat().st_size)
