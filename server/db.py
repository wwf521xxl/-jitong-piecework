# -*- coding: utf-8 -*-
"""SQLite 数据层：账号、订单、工序、报工、审批、审计。"""

from __future__ import annotations

import csv
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data"


def data_dir() -> Path:
    path = Path(os.environ.get("JITONG_DATA_DIR", str(DEFAULT_DATA_DIR))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "jitong.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_after(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


LEGACY_PROCESS_MAP = {
    "写真": {
        1: ["排版"],
        2: ["写真打印"],
        3: ["写真过板"],
        4: ["裁切"],
        5: ["写真亚克力加工"],
    },
    "亚克力": {
        1: ["亚克力排版", "特殊亚克力排版"],
        2: ["打印"],
        3: ["过胶", "UV雪弗板覆膜", "覆膜"],
        4: ["激光切割", "UV雪弗板裁切", "雪弗板切割"],
        5: ["特殊亚克力加工", "写真亚克力加工"],
    },
}

PROCESS_SKILLS = {
    "排版": [5, 7, 16],
    "写真打印": [13, 16],
    "写真过板": [1, 2, 3, 9, 10],
    "写真覆膜": [9],
    "裁切": [4, 6, 5, 7, 9, 17],
    "写真亚克力加工": [1, 5, 7, 14, 15],
    "特殊亚克力排版": [5, 7, 11, 12],
    "亚克力排版": [5, 7, 11, 12],
    "打印": [8],
    "过胶": [9, 10],
    "UV雪弗板覆膜": [1, 5, 7, 9, 2, 3],
    "覆膜": [1, 5, 7, 9, 2, 3],
    "激光切割": [4, 6, 17],
    "UV雪弗板裁切": [5, 7, 9, 11, 12],
    "雪弗板切割": [5, 7, 9, 11, 12],
    "特殊亚克力加工": [1, 5, 7, 14, 15],
}


def seed_skill_catalog(conn: sqlite3.Connection) -> None:
    for index, name in enumerate(PROCESS_SKILLS.keys()):
        conn.execute(
            "INSERT OR IGNORE INTO skill_catalog(name, display_name, active, sort, created_at) VALUES(?,?,1,?,?)",
            (name, name, index, utc_now()),
        )


ROUTE_SEED = {
    "PHOTO": ("写真", "写真标准 6 道", ["排版", "写真打印", "写真过板", "写真覆膜", "裁切", "写真亚克力加工"]),
    "A": ("亚克力", "亚克力 A", ["特殊亚克力排版", "过胶", "激光切割", "特殊亚克力加工"]),
    "B": ("亚克力", "亚克力 B", ["特殊亚克力排版", "激光切割", "特殊亚克力加工"]),
    "C": ("亚克力", "亚克力 C", ["特殊亚克力排版", "打印", "过胶", "激光切割", "特殊亚克力加工"]),
    "D": ("亚克力", "亚克力 D", ["亚克力排版", "打印", "过胶", "激光切割"]),
    "E": ("亚克力", "亚克力 E", ["亚克力排版", "打印", "雪弗板切割"]),
    "F": ("亚克力", "亚克力 F", ["亚克力排版", "打印", "覆膜", "雪弗板切割", "写真亚克力加工"]),
}


def seed_routes(conn: sqlite3.Connection) -> None:
    for index, (key, (line, name, steps)) in enumerate(ROUTE_SEED.items()):
        route_id = "RT-" + key
        conn.execute(
            "INSERT OR IGNORE INTO routes(id, route_key, line, name, active, sort, created_at) VALUES(?,?,?,?,1,?,?)",
            (route_id, key, line, name, index, utc_now()),
        )
        for step_no, process_name in enumerate(steps, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO route_steps(route_id, step_no, process_name) VALUES(?,?,?)",
                (route_id, step_no, process_name),
            )


def seed_process_skills(conn: sqlite3.Connection) -> None:
    for row in conn.execute(
        "SELECT s.employee_id, s.line, s.step_no FROM employee_skills s "
        "JOIN employees e ON e.id=s.employee_id WHERE e.is_admin=0"
    ).fetchall():
        for process_name in LEGACY_PROCESS_MAP.get(row["line"], {}).get(int(row["step_no"]), []):
            conn.execute(
                "INSERT OR IGNORE INTO employee_process_skills(employee_id, process_name) VALUES(?,?)",
                (row["employee_id"], process_name),
            )
    for process_name, employee_nos in PROCESS_SKILLS.items():
        for no in employee_nos:
            conn.execute(
                "INSERT OR IGNORE INTO employee_process_skills(employee_id, process_name) "
                "SELECT id, ? FROM employees WHERE employee_no=? AND is_admin=0",
                (process_name, no),
            )
    conn.commit()


SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    employee_no INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    avatar TEXT,
    is_admin INTEGER NOT NULL DEFAULT 0,
    can_create_job INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    pin_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_skills (
    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    line TEXT NOT NULL,
    step_no INTEGER NOT NULL,
    PRIMARY KEY (employee_id, line, step_no)
);

CREATE TABLE IF NOT EXISTS employee_process_skills (
    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    process_name TEXT NOT NULL,
    PRIMARY KEY (employee_id, process_name)
);

CREATE TABLE IF NOT EXISTS skill_catalog (
    name TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    id TEXT PRIMARY KEY,
    route_key TEXT NOT NULL UNIQUE,
    line TEXT NOT NULL,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS route_steps (
    route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    PRIMARY KEY (route_id, step_no)
);

CREATE TABLE IF NOT EXISTS job_step_groups (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES production_jobs(id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    total_qty REAL NOT NULL DEFAULT 0,
    unit TEXT,
    created_by TEXT,
    created_at TEXT,
    closed_by TEXT,
    closed_at TEXT,
    close_reason TEXT,
    UNIQUE (job_id, step_no)
);

CREATE TABLE IF NOT EXISTS job_step_group_members (
    group_id TEXT NOT NULL REFERENCES job_step_groups(id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    joined_at TEXT,
    record_id TEXT,
    PRIMARY KEY (group_id, employee_id)
);

CREATE TABLE IF NOT EXISTS production_jobs (
    id TEXT PRIMARY KEY,
    order_no TEXT UNIQUE NOT NULL,
    line TEXT NOT NULL,
    product TEXT NOT NULL,
    spec TEXT,
    customer TEXT,
    planned_qty REAL NOT NULL,
    meters REAL,
    unit TEXT NOT NULL,
    due_date TEXT,
    priority TEXT NOT NULL DEFAULT '正常',
    remark TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    qr_token TEXT UNIQUE NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_steps (
    job_id TEXT NOT NULL REFERENCES production_jobs(id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    planned_qty REAL NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (job_id, step_no)
);

CREATE TABLE IF NOT EXISTS piece_records (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES production_jobs(id),
    step_no INTEGER NOT NULL,
    line TEXT NOT NULL,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    qty REAL NOT NULL,
    unit TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'valid',
    note TEXT,
    idempotency_key TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL DEFAULT 'scan',
    photo_path TEXT,
    device_id TEXT,
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corrections (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL REFERENCES piece_records(id),
    reason TEXT NOT NULL,
    note TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by TEXT NOT NULL REFERENCES employees(id),
    approved_by TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_piece_job_step ON piece_records(job_id, step_no, status);
CREATE INDEX IF NOT EXISTS idx_piece_employee_time ON piece_records(employee_id, created_at);
CREATE INDEX IF NOT EXISTS idx_piece_line_time ON piece_records(line, created_at);
CREATE INDEX IF NOT EXISTS idx_corrections_status ON corrections(status);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
"""

EMPLOYEE_SEED = [
    ("E001", 1, "员工01", "综合岗位", [("写真", 5), ("亚克力", 5)]),
    ("E002", 2, "员工02", "综合岗位", [("写真", 5), ("亚克力", 5)]),
    ("E003", 3, "员工03", "综合岗位", [("写真", 5), ("亚克力", 5)]),
    ("E004", 4, "员工04", "裁切（激光切割）", [("亚克力", 4)]),
    ("E005", 5, "员工05", "多能工（全线）", [("写真", 1), ("写真", 2), ("写真", 3), ("写真", 4), ("写真", 5), ("亚克力", 1), ("亚克力", 2), ("亚克力", 3), ("亚克力", 4), ("亚克力", 5)]),
    ("E006", 6, "员工06", "裁切（激光切割）", [("写真", 4), ("亚克力", 4)]),
    ("E007", 7, "员工07", "多能工（全线）", [("写真", 1), ("写真", 2), ("写真", 3), ("写真", 4), ("写真", 5), ("亚克力", 1), ("亚克力", 2), ("亚克力", 3), ("亚克力", 4), ("亚克力", 5)]),
    ("E008", 8, "员工08", "UV打印", [("亚克力", 2)]),
    ("E009", 9, "员工09", "过膜过板", [("写真", 3), ("亚克力", 3)]),
    ("E010", 10, "员工10", "过膜过板", [("写真", 3), ("亚克力", 3)]),
    ("E011", 11, "员工11", "亚克力排图", [("亚克力", 1)]),
    ("E012", 12, "员工12", "亚克力排图", [("亚克力", 1)]),
    ("E013", 13, "员工13", "写真/异型（打印）", [("写真", 2)]),
    ("E014", 14, "员工14", "综合岗位", [("写真", 5), ("亚克力", 5)]),
    ("E015", 15, "员工15", "综合岗位", [("写真", 5), ("亚克力", 5)]),
    ("E016", 16, "员工16", "写真/异型（排版）", [("写真", 1)]),
    ("E017", 17, "员工17", "裁切（激光切割）", [("写真", 4), ("亚克力", 4)]),
]


def _write_initial_accounts(credentials: list[tuple[int, str, str, str]]) -> None:
    path = data_dir() / "员工初始账号.csv"
    if path.exists():
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["工号", "姓名", "岗位", "初始PIN"])
        for no, name, role, pin in credentials:
            writer.writerow([no, name, role, pin])


def _write_admin_password(password: str) -> None:
    path = data_dir() / "管理员初始密码.txt"
    if path.exists():
        return
    path.write_text(
        "计件通管理员初始账号\n"
        "账号：admin\n"
        f"密码：{password}\n\n"
        "首次登录后请立即修改密码，并删除本文件。\n",
        encoding="utf-8-sig",
    )


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        # 兼容旧库：补充“备注”字段
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(production_jobs)").fetchall()}
        if "remark" not in columns:
            conn.execute("ALTER TABLE production_jobs ADD COLUMN remark TEXT")
            conn.commit()
        if "meters" not in columns:
            conn.execute("ALTER TABLE production_jobs ADD COLUMN meters REAL")
            conn.commit()
        if "route_key" not in columns:
            conn.execute("ALTER TABLE production_jobs ADD COLUMN route_key TEXT")
            conn.commit()

        step_columns = {row["name"] for row in conn.execute("PRAGMA table_info(job_steps)").fetchall()}
        if "step_name" not in step_columns:
            conn.execute("ALTER TABLE job_steps ADD COLUMN step_name TEXT")
            conn.commit()

        # 兼容旧库：建单权限从代码常量迁移到员工表
        employee_columns = {row["name"] for row in conn.execute("PRAGMA table_info(employees)").fetchall()}
        if "can_create_job" not in employee_columns:
            conn.execute("ALTER TABLE employees ADD COLUMN can_create_job INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                "UPDATE employees SET can_create_job=1 "
                "WHERE is_admin=0 AND (id IN ('E007','E011','E012','E016') "
                "OR role LIKE '%排版%' OR role LIKE '%排图%')"
            )
            conn.commit()
        count = conn.execute("SELECT COUNT(*) AS n FROM employees").fetchone()["n"]
        if count:
            seed_process_skills(conn)
            seed_skill_catalog(conn)
            seed_routes(conn)
            return

        from .security import hash_secret  # 延迟导入，避免循环依赖

        admin_password = os.environ.get("JITONG_ADMIN_PASSWORD") or "123456"
        employee_pin = os.environ.get("JITONG_EMPLOYEE_PIN") or "123456"
        credentials: list[tuple[int, str, str, str]] = []
        now = utc_now()

        with transaction(conn):
            for emp_id, no, name, role, skills in EMPLOYEE_SEED:
                pin = employee_pin
                conn.execute(
                    "INSERT INTO employees(id, employee_no, name, role, avatar, is_admin, active, pin_hash, created_at)"
                    " VALUES(?,?,?,?,?,0,1,?,?)",
                    (emp_id, no, name, role, name[:1], hash_secret(pin), now),
                )
                for line, step in skills:
                    conn.execute(
                        "INSERT INTO employee_skills(employee_id, line, step_no) VALUES(?,?,?)",
                        (emp_id, line, step),
                    )
                credentials.append((no, name, role, pin))

            # 初始建单权限：只给排版/排图人员；之后由管理员在数据库里调整
            for emp_id in ("E005", "E007", "E011", "E012", "E016"):
                conn.execute("UPDATE employees SET can_create_job=1 WHERE id=?", (emp_id,))

            conn.execute(
                "INSERT INTO employees(id, employee_no, name, role, avatar, is_admin, can_create_job, active, pin_hash, created_at)"
                " VALUES(?,?,?,?,?,1,0,1,?,?)",
                ("A001", 0, "厂长", "厂长 · 管理员", "李", hash_secret(admin_password), now),
            )
            for line in ("写真", "亚克力"):
                for step in range(1, 6):
                    conn.execute(
                        "INSERT OR IGNORE INTO employee_skills(employee_id, line, step_no) VALUES('A001',?,?)",
                        (line, step),
                    )
            conn.execute("INSERT INTO settings(key, value) VALUES('duplicate_minutes', '10')")
            conn.execute("INSERT INTO settings(key, value) VALUES('tolerance', '0.05')")
            conn.execute(
                "INSERT INTO audit_log(actor_id, action, entity_type, entity_id, detail, created_at)"
                " VALUES('system','seed','system','init','初始化员工与管理账号',?)",
                (now,),
            )

        _write_initial_accounts(credentials)
        _write_admin_password(admin_password)
        seed_process_skills(conn)
        seed_skill_catalog(conn)
        seed_routes(conn)
    finally:
        conn.close()


def get_setting(conn: sqlite3.Connection, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def audit(
    conn: sqlite3.Connection,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: str = "",
) -> None:
    conn.execute(
        "INSERT INTO audit_log(actor_id, action, entity_type, entity_id, detail, created_at)"
        " VALUES(?,?,?,?,?,?)",
        (actor_id, action, entity_type, entity_id, detail, utc_now()),
    )
