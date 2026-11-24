# -*- coding: utf-8 -*-
"""备份 SQLite 数据库与现场照片，生成带时间戳的 zip。"""

from __future__ import annotations

import os
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("JITONG_DATA_DIR", str(ROOT / "data"))).resolve()
BACKUP_DIR = Path(os.environ.get("JITONG_BACKUP_DIR", str(ROOT / "backups"))).resolve()


def main() -> None:
    db_file = DATA_DIR / "jitong.db"
    if not db_file.exists():
        raise SystemExit(f"数据库不存在：{db_file}，请先启动生产版。")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    db_copy = BACKUP_DIR / f"jitong-{stamp}.db"
    zip_path = BACKUP_DIR / f"jitong-{stamp}.zip"

    source = sqlite3.connect(str(db_file))
    target = sqlite3.connect(str(db_copy))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_copy, arcname="jitong.db")
        photos = DATA_DIR / "photos"
        if photos.exists():
            for file in photos.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=f"photos/{file.relative_to(photos)}")

    db_copy.unlink(missing_ok=True)

    # 只保留最近 30 个备份
    backups = sorted(BACKUP_DIR.glob("jitong-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[30:]:
        old.unlink(missing_ok=True)

    print(f"备份完成：{zip_path}")
    print(f"大小：{zip_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
