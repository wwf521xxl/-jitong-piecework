# -*- coding: utf-8 -*-
"""打包生产版交付 zip（不含任何 data、密码和测试数据）。"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(r"D:\工厂个人计件软件")
DIST = ROOT / "dist"
OUT = DIST / "计件通-生产版-交付包.zip"

FILES = [
    "README.md",
    "生产版使用说明.txt",
    "启动生产版.bat",
    "启动生产版.ps1",
    "启动生产版-HTTPS.bat",
    "设置密码.bat",
    "requirements-dev.txt",
    "pytest.ini",
    "Dockerfile",
    "docker-compose.yml",
    "Caddyfile",
    ".env.example",
    "docs/生产版上线部署说明.md",
    "docs/本地HTTPS扫码部署说明.md",
    "docs/客户现场交付清单.md",
    "docs/手机证书下载二维码.png",
    "docs/手机扫码报工二维码.png",
    "docs/工厂个人计件软件_手机端设计方案.docx",
    "docs/工厂个人计件软件_手机端设计方案.pdf",
]

DIRS = [
    "app",
    "server",
    "tools",
    "tests",
]

EXCLUDE_PARTS = {"__pycache__", "data", "backups", "test_data", ".git", ".vscode", "dist"}
EXCLUDE_SUFFIX = {".pyc", ".log"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIX:
        return False
    return True


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()

    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in FILES:
            path = ROOT / name
            if path.exists():
                zf.write(path, arcname=name)
                count += 1
        for dirname in DIRS:
            base = ROOT / dirname
            for path in base.rglob("*"):
                if path.is_file() and should_include(path.relative_to(ROOT)):
                    zf.write(path, arcname=str(path.relative_to(ROOT)).replace("\\", "/"))
                    count += 1

    print(f"打包完成：{OUT}")
    print(f"文件数：{count}，大小：{OUT.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
