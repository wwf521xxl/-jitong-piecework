# -*- coding: utf-8 -*-
"""2026-11-06 技能授权变更：写真裁切与全线多能工。"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("JITONG_DATA_DIR", str(ROOT / "data"))).resolve()
DB = DATA_DIR / "jitong.db"

SKILLS = {
    "E005": [("写真", s) for s in range(1, 6)] + [("亚克力", s) for s in range(1, 6)],
    "E006": [("写真", 4), ("亚克力", 4)],
    "E007": [("写真", s) for s in range(1, 6)] + [("亚克力", s) for s in range(1, 6)],
    "E017": [("写真", 4), ("亚克力", 4)],
}
ROLES = {
    "E005": "多能工（全线）",
    "E007": "多能工（全线）",
}


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"数据库不存在：{DB}")
    conn = sqlite3.connect(str(DB), timeout=10, isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    before = conn.execute(
        "SELECT employee_id, line, step_no FROM employee_skills WHERE employee_id IN ('E005','E006','E007','E017')"
    ).fetchall()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for employee_id, skills in SKILLS.items():
            for line, step in skills:
                conn.execute(
                    "INSERT OR IGNORE INTO employee_skills(employee_id, line, step_no) VALUES(?,?,?)",
                    (employee_id, line, step),
                )
        for employee_id, role in ROLES.items():
            conn.execute("UPDATE employees SET role=? WHERE id=?", (role, employee_id))
        conn.execute(
            "INSERT INTO audit_log(actor_id, action, entity_type, entity_id, detail, created_at)"
            " VALUES('system','update_skills','employee','E005,E006,E007,E017',?,?)",
            ("写真裁切：黄伟、刘浩；全线多能工：王坚、张知亮", now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        after = conn.execute(
            "SELECT employee_id, line, step_no FROM employee_skills WHERE employee_id IN ('E005','E006','E007','E017') ORDER BY employee_id, line, step_no"
        ).fetchall()
        conn.close()

    print(f"变更前 {len(before)} 条技能，变更后 {len(after)} 条技能")
    print("已更新：")
    print("  王坚 E005：写真 + 亚克力 全 10 道")
    print("  张知亮 E007：写真 + 亚克力 全 10 道")
    print("  刘浩 E006：写真裁切 + 亚克力裁切")
    print("  黄伟 E017：写真裁切 + 亚克力裁切")


if __name__ == "__main__":
    main()
