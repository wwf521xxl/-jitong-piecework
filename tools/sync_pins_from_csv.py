# -*- coding: utf-8 -*-
"""把 data/员工初始账号.csv 和 管理员初始密码.txt 同步为真实登录密码。

警告：会覆盖数据库中现有 PIN/密码。运行前自动备份数据库。
用法：
  python tools\\sync_pins_from_csv.py
  python tools\\sync_pins_from_csv.py --yes
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "jitong.db"
CSV_PATH = DATA / "员工初始账号.csv"
ADMIN_PATH = DATA / "管理员初始密码.txt"
BACKUP_DIR = ROOT / "backups"
sys.path.insert(0, str(ROOT))

from server import db, security  # noqa: E402


def read_admin() -> str | None:
    if not ADMIN_PATH.exists():
        return None
    for line in ADMIN_PATH.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("密码："):
            return line.split("：", 1)[1].strip()
    return None


def read_employees() -> list[tuple[int, str, str]]:
    if not CSV_PATH.exists():
        raise SystemExit(f"找不到文件：{CSV_PATH}")
    rows: list[tuple[int, str, str]] = []
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                no = int(str(row.get("工号", "")).strip())
            except ValueError:
                continue
            name = str(row.get("姓名", "")).strip()
            pin = str(row.get("初始PIN", "")).strip()
            rows.append((no, name, pin))
    return rows


def backup_db() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = BACKUP_DIR / f"jitong-before-pin-sync-{stamp}.db"
    src = sqlite3.connect(str(DB))
    dst = sqlite3.connect(str(path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    args = parser.parse_args()

    if not DB.exists():
        raise SystemExit(f"数据库不存在：{DB}")

    employees = read_employees()
    admin_pin = read_admin()
    invalid = [(no, name, pin) for no, name, pin in employees if len(pin) != 6]
    usable = [(no, name, pin) for no, name, pin in employees if len(pin) == 6]

    print(f"CSV 员工数：{len(employees)}，有效 PIN：{len(usable)}，无效：{len(invalid)}")
    for no, name, pin in invalid:
        print(f"  跳过无效：{no} {name}（PIN 不是 6 位）")
    if admin_pin:
        print(f"管理员密码：{'有效' if len(admin_pin) >= 6 else '无效'}（{len(admin_pin)} 位）")
    else:
        print("管理员密码：未找到，跳过")

    if not args.yes:
        answer = input("这会覆盖数据库中的现有 PIN/密码，输入 YES 继续：").strip()
        if answer != "YES":
            print("已取消。")
            return

    backup = backup_db()
    print(f"已备份：{backup}")

    conn = db.connect()
    try:
        updated = 0
        with db.transaction(conn):
            for no, name, pin in usable:
                row = conn.execute(
                    "SELECT id FROM employees WHERE employee_no=? AND is_admin=0",
                    (no,),
                ).fetchone()
                if row is None:
                    print(f"  跳过：工号 {no} {name} 不存在")
                    continue
                conn.execute(
                    "UPDATE employees SET pin_hash=? WHERE id=?",
                    (security.hash_secret(pin), row["id"]),
                )
                updated += 1
            if admin_pin and len(admin_pin) >= 6:
                conn.execute(
                    "UPDATE employees SET pin_hash=? WHERE id='A001'",
                    (security.hash_secret(admin_pin),),
                )
            db.audit(
                conn, "system", "sync_pins_from_csv", "employees", "all",
                f"同步员工 PIN {updated} 人；管理员 {'是' if admin_pin else '否'}",
            )
        print(f"已同步员工 PIN：{updated} 人")
        if admin_pin and len(admin_pin) >= 6:
            print("已同步管理员密码。")
        print("新密码立即生效；旧密码对新登录失效。")
        print("注意：data 下的文本文件只是初始记录，以后请用 设置密码.bat 修改。")
        non_numeric = [(no, name) for no, name, pin in usable if not pin.isdigit()]
        if non_numeric:
            print("警告：以下员工的 PIN 含字母，手机数字键盘可能无法输入：")
            print("  " + "、".join(f"{no} {name}" for no, name in non_numeric))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
