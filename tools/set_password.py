# -*- coding: utf-8 -*-
"""安全地修改 admin 密码或员工 PIN。

用法：
  python tools\\set_password.py admin
  python tools\\set_password.py 7

会直接更新 data\\jitong.db 中的密码哈希；不会把新密码写进明文文件。
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import db, security  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("用法：python tools\\set_password.py admin")
        print("      python tools\\set_password.py 员工工号")
        raise SystemExit(1)

    account = sys.argv[1].strip()
    conn = db.connect()
    try:
        if account.lower() == "admin":
            row = conn.execute("SELECT * FROM employees WHERE id='A001'").fetchone()
            label = "管理员 admin"
            kind = "密码"
        else:
            if not account.isdigit():
                print("账号只能是 admin 或员工工号（1–17）")
                raise SystemExit(1)
            row = conn.execute(
                "SELECT * FROM employees WHERE employee_no=? AND is_admin=0",
                (int(account),),
            ).fetchone()
            label = f"员工 {account}"
            kind = "PIN"

        if row is None:
            print(f"找不到账号：{account}")
            raise SystemExit(1)

        print(f"正在修改：{label}")
        first = getpass.getpass(f"请输入新的{kind}：")
        second = getpass.getpass(f"请再输入一次：")
        if first != second:
            print("两次输入不一致，未修改。")
            raise SystemExit(1)
        if len(first) < 6:
            print(f"{kind}至少 6 位，未修改。")
            raise SystemExit(1)
        if row["is_admin"] == 0 and len(first) != 6:
            print("员工 PIN 必须是 6 位，未修改。")
            raise SystemExit(1)

        with db.transaction(conn):
            conn.execute(
                "UPDATE employees SET pin_hash=? WHERE id=?",
                (security.hash_secret(first), row["id"]),
            )
            db.audit(conn, row["id"], "set_password", "employee", row["id"], "命令行修改密码")
        print(f"{label} 的{kind}已修改。")
        print("所有手机/电脑下次登录都使用新密码；旧密码立即失效。")
        print("data 下的初始密码文件不会自动更新，请不要再用它们判断当前密码。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
