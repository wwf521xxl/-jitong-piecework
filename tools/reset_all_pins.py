# -*- coding: utf-8 -*-
"""一键把所有员工（含管理员）的密码/PIN 重置为 123456。"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

TARGET_PIN = "123456"
ITERATIONS = 160_000


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_db() -> Path | None:
    bases = [base_dir(), Path.cwd()]
    for base in bases:
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
    print("  计件通 · 重置所有员工 PIN")
    print("=" * 60)
    print()
    print("本工具会把所有员工（含管理员）的密码/PIN 改成：")
    print()
    print("    123456")
    print()
    print("管理员 admin 也会改成同一个密码。")
    print()

    db = find_db()
    if db is None:
        raw = input("没有自动找到 jitong.db，请把 data\\jitong.db 或 data 文件夹拖到这里：").strip().strip('"')
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

    print(f"数据库：{db}")
    print()
    confirm = input("确认修改请输入 YES：").strip()
    if confirm != "YES":
        print("已取消，没有修改。")
        input("按回车退出...")
        return

    backup_dir = db.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"jitong-before-all-pin-{stamp}.db"
    shutil.copy2(db, backup)
    print(f"已备份：{backup}")

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, employee_no, name, is_admin FROM employees WHERE active=1 ORDER BY is_admin DESC, employee_no"
        ).fetchall()
        if not rows:
            print("没有找到非管理员员工，未修改。")
            input("按回车退出...")
            return

        with conn:
            for row in rows:
                conn.execute(
                    "UPDATE employees SET pin_hash=? WHERE id=?",
                    (hash_secret(TARGET_PIN), row["id"]),
                )
            # 让旧登录会话失效，所有账号必须用新密码重新登录
            conn.execute("DELETE FROM sessions")
            try:
                conn.execute(
                    "INSERT INTO audit_log(id, actor_id, action, target_type, target_id, detail, created_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        "AUD" + secrets.token_hex(8).upper(),
                        "A001",
                        "reset_all_pins",
                        "employee",
                        "ALL",
                        "所有员工及管理员密码重置为 123456",
                        datetime.now().astimezone().isoformat(timespec="seconds"),
                    ),
                )
            except Exception:
                pass

        print()
        print(f"完成：{len(rows)} 个账号的密码/PIN 已改为 {TARGET_PIN}")
        for row in rows:
            if row["is_admin"]:
                print(f"  管理员 admin  {row['name']}")
            else:
                print(f"  工号 {row['employee_no']:>2}  {row['name']}")
        print()
        print("旧登录已失效，所有账号需要用 123456 重新登录。")
    finally:
        conn.close()

    input("按回车退出...")


if __name__ == "__main__":
    main()
