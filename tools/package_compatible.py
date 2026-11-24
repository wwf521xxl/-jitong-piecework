# -*- coding: utf-8 -*-
"""生成全英文文件名的兼容交付包，避免中文 ZIP 在部分解压工具中失败。"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(r"D:\工厂个人计件软件")
OUT = ROOT / "dist" / "jitong-production-delivery.zip"
PREFIX = "jitong-production"

FILES = {
    "README.md": "README.md",
    "生产版使用说明.txt": "README-production.txt",
    "启动生产版.bat": "START-HTTP.bat",
    "启动生产版.ps1": "START-HTTP.ps1",
    "启动生产版-HTTPS.bat": "START-HTTPS.bat",
    "设置密码.bat": "SET-PASSWORD.bat",
    "requirements-dev.txt": "requirements-dev.txt",
    "pytest.ini": "pytest.ini",
    "Dockerfile": "Dockerfile",
    "docker-compose.yml": "docker-compose.yml",
    "Caddyfile": "Caddyfile",
    ".env.example": ".env.example",
    "docs/生产版上线部署说明.md": "docs/deploy-cloud.md",
    "docs/本地HTTPS扫码部署说明.md": "docs/local-https.md",
    "docs/客户现场交付清单.md": "docs/customer-delivery-checklist.md",
    "docs/工厂个人计件软件_手机端设计方案.docx": "docs/design.docx",
    "docs/工厂个人计件软件_手机端设计方案.pdf": "docs/design.pdf",
    "docs/手机证书下载二维码.png": "docs/qr-cert.png",
    "docs/手机扫码报工二维码.png": "docs/qr-app.png",
}

DIRS = ["app", "server", "tools", "tests"]
EXCLUDE_PARTS = {"__pycache__", "data", "backups", "test_data", ".git", ".vscode", "dist", "certs"}
EXCLUDE_SUFFIX = {".pyc", ".log"}


def included(path: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in path.parts):
        return False
    return path.suffix.lower() not in EXCLUDE_SUFFIX


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        first = """计件通 · 兼容版交付包
============================================================
这个包内所有文件名都是英文，避免中文 ZIP 在部分电脑/手机上解压失败。

1. 不要用 WPS 的“解压”功能（容易卡在 0%）。
   请右键压缩包 → “全部解压缩”/“Extract All”，或安装 7-Zip 后右键解压。
   解压到 D:\\jitong-production，不要直接在压缩包里双击运行。
2. 电脑安装 Python 3.11+，安装时勾选 Add Python to PATH。
3. 双击 START-HTTPS.bat
4. 首次启动会自动生成：
   - data\\ 数据库和 17 个账号
   - certs\\ 本地 HTTPS 证书
5. 管理员初始密码在 data\\管理员初始密码.txt
6. 员工 PIN 在 data\\员工初始账号.csv
7. 手机证书下载地址会显示在启动窗口，例如：
   http://服务器IP:8788/
8. 手机安装证书后打开：
   https://服务器IP:8443

详细说明：
  README-production.txt
  docs\\local-https.md

注意：
- 不要把这个文件夹放到微信/QQ的临时目录里运行；
- 不要只把 zip 里的 START-HTTPS.bat 拖出来单独运行；
- 一定要先完整解压。
"""
        zf.writestr(f"{PREFIX}/README-FIRST.txt", first.encode("utf-8"))
        count += 1
        for src_name, dst_name in FILES.items():
            src = ROOT / src_name
            if src.exists():
                zf.write(src, arcname=f"{PREFIX}/{dst_name}")
                count += 1
        for dirname in DIRS:
            base = ROOT / dirname
            for path in base.rglob("*"):
                if path.is_file() and included(path.relative_to(ROOT)):
                    rel = path.relative_to(ROOT).as_posix()
                    zf.write(path, arcname=f"{PREFIX}/{rel}")
                    count += 1
    print(f"兼容包完成：{OUT}")
    print(f"文件数：{count}，大小：{OUT.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
