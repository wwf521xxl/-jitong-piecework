# -*- coding: utf-8 -*-
"""修改管理员（厂长）的显示姓名。"""

from __future__ import annotations

import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_db() -> Path | None:
    for base in (base_dir(), Path.cwd()):
        for candidate in (base / "data" / "jitong.db", base / "jitong.db"):
            if candidate.exists():
                return candidate
    return None


def main() -> None:
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print("  计件通 · 修改厂长显示姓名")
    print("=" * 60)
    print()

    db = find_db()
    if db is None:
        raw = input("没有自动找到 jitong.db，请把 data 文件夹拖到这里：").strip().strip('"')
        if not raw:
            print("没有输入路径，已取消。")
            input("按回车退出...")
            return
        p = Path(raw)
        db = p / "jitong.db" if p.is_dir() else p

    if not db.exists():
        print(f"找不到数据库：{db}")
        input("按回车退出...")
        return

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT id, name FROM employees WHERE id='A001'").fetchone()
        if row is None:
            print("找不到管理员账号 A001。")
            input("按回车退出...")
            return
        print(f"数据库：{db}")
        print(f"当前厂长姓名：{row['name']}")
        print()
        new_name = input("请输入新的厂长姓名：").strip()
        if not new_name:
            print("没有输入姓名，已取消。")
            input("按回车退出...")
            return
        if len(new_name) > 20:
            print("姓名太长，最多 20 个字。")
            input("按回车退出...")
            return
        confirm = input(f"确认改成“{new_name}”请输入 YES：").strip()
        if confirm != "YES":
            print("已取消，没有修改。")
            input("按回车退出...")
            return

        backup_dir = db.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"jitong-before-rename-admin-{datetime.now():%Y%m%d-%H%M%S}.db"
        shutil.copy2(db, backup)
        print(f"已备份：{backup}")

        with conn:
            conn.execute("UPDATE employees SET name=? WHERE id='A001'", (new_name,))
            try:
                conn.execute(
                    "INSERT INTO audit_log(id, actor_id, action, target_type, target_id, detail, created_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        "AUD" + secrets.token_hex(8).upper(),
                        "A001",
                        "rename_admin",
                        "employee",
                        "A001",
                        f"{row['name']} -> {new_name}",
                        datetime.now().astimezone().isoformat(timespec="seconds"),
                    ),
                )
            except Exception:
                pass
        print()
        print(f"完成：厂长姓名已改为 {new_name}")
        print("登录账号仍然是 admin，密码不变。")
    finally:
        conn.close()
    input("按回车退出...")


if __name__ == "__main__":
    main()
