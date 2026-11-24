# -*- coding: utf-8 -*-
"""业务规则：报工校验、订单、审批与共享数据快照。"""

from __future__ import annotations

import base64
import os
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from . import db
from .security import hash_secret, verify_secret

BOOTSTRAP_DAYS = int(os.environ.get("JITONG_BOOTSTRAP_DAYS", "45"))
TOLERANCE = 0.05

LINE_STEPS = {
    "写真": ["排版", "写真打印", "写真过板", "写真覆膜", "裁切", "写真亚克力加工"],
    "亚克力": ["特殊亚克力排版", "UV打印", "UV雪弗板覆膜", "UV雪弗板裁切", "特殊亚克力加工"],
}

PHOTO_ROUTE = ["排版", "写真打印", "写真过板", "写真覆膜", "裁切", "写真亚克力加工"]
ACRYLIC_ROUTES = {
    "A": ["特殊亚克力排版", "过胶", "激光切割", "特殊亚克力加工"],
    "B": ["特殊亚克力排版", "激光切割", "特殊亚克力加工"],
    "C": ["特殊亚克力排版", "打印", "过胶", "激光切割", "特殊亚克力加工"],
    "D": ["亚克力排版", "打印", "过胶", "激光切割"],
    "E": ["亚克力排版", "打印", "雪弗板切割"],
    "F": ["亚克力排版", "打印", "覆膜", "雪弗板切割", "写真亚克力加工"],
}
ROUTE_NAMES = {
    "PHOTO": "写真固定 6 道",
    "A": "亚克力 A：特殊排版→过胶→激光切割→特殊加工",
    "B": "亚克力 B：特殊排版→激光切割→特殊加工",
    "C": "亚克力 C：特殊排版→打印→过胶→激光切割→特殊加工",
    "D": "亚克力 D：排版→打印→过胶→激光切割",
    "E": "亚克力 E：排版→打印→雪弗板切割",
    "F": "亚克力 F：排版→打印→覆膜→雪弗板切割→写真加工",
}

GROUP_PROCESS_NAMES = {"写真过板", "写真亚克力加工", "激光切割"}


def bad(message: str, code: str = "bad_request", status: int = 400):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def _skills(conn: sqlite3.Connection, employee_id: str):
    rows = conn.execute(
        "SELECT line, step_no FROM employee_skills WHERE employee_id=? ORDER BY line, step_no",
        (employee_id,),
    ).fetchall()
    grouped: dict[str, list[int]] = {}
    for row in rows:
        grouped.setdefault(row["line"], []).append(int(row["step_no"]))
    return [{"line": line, "steps": steps} for line, steps in grouped.items()]


def can_create_job(row) -> bool:
    """厂长始终可以建单；其他人员按数据库权限。"""
    if bool(row["is_admin"]):
        return True
    return bool(row["can_create_job"])


def serialize_employee(conn: sqlite3.Connection, row) -> dict:
    process_rows = conn.execute(
        "SELECT process_name FROM employee_process_skills WHERE employee_id=? ORDER BY process_name",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "employeeNo": row["employee_no"],
        "name": row["name"],
        "role": row["role"],
        "avatar": row["avatar"] or row["name"][:1],
        "isAdmin": bool(row["is_admin"]),
        "canCreateJob": can_create_job(row),
        "skills": _skills(conn, row["id"]),
        "processSkills": [r["process_name"] for r in process_rows],
    }


def user_payload(conn: sqlite3.Connection, row) -> dict:
    return serialize_employee(conn, row)


def serialize_step_group(conn: sqlite3.Connection, job_id: str, step_no: int) -> dict | None:
    group = conn.execute(
        "SELECT * FROM job_step_groups WHERE job_id=? AND step_no=?", (job_id, step_no)
    ).fetchone()
    if group is None:
        return None
    members = conn.execute(
        "SELECT m.employee_id, e.name, m.joined_at FROM job_step_group_members m "
        "JOIN employees e ON e.id=m.employee_id WHERE m.group_id=? ORDER BY m.joined_at",
        (group["id"],),
    ).fetchall()
    total = float(group["total_qty"] or 0)
    count = len(members)
    per = round(total / count, 3) if count else 0
    return {
        "id": group["id"],
        "stepNo": group["step_no"],
        "status": group["status"],
        "totalQty": total,
        "unit": group["unit"] or "",
        "memberCount": count,
        "perQty": per,
        "members": [{"id": m["employee_id"], "name": m["name"]} for m in members],
    }


def _skill_display(conn: sqlite3.Connection, name: str | None) -> str:
    if not name:
        return ""
    row = conn.execute("SELECT display_name FROM skill_catalog WHERE name=?", (name,)).fetchone()
    return row["display_name"] if row else name


def serialize_job(conn: sqlite3.Connection, row) -> dict:
    steps = conn.execute(
        "SELECT step_no, step_name, planned_qty, unit FROM job_steps WHERE job_id=? ORDER BY step_no",
        (row["id"],),
    ).fetchall()
    route_key = row["route_key"] if "route_key" in row.keys() else None
    route_row = conn.execute("SELECT name FROM routes WHERE route_key=?", (route_key,)).fetchone()
    route_name = route_row["name"] if route_row else ROUTE_NAMES.get(route_key, "旧订单流程" if not route_key else str(route_key))
    fallback_names = LINE_STEPS.get(row["line"], [])
    return {
        "id": row["id"],
        "orderNo": row["order_no"],
        "line": row["line"],
        "product": row["product"],
        "spec": row["spec"] or "",
        "customer": row["customer"] or "",
        "plannedQty": row["planned_qty"],
        "meters": row["meters"] or 0,
        "unit": row["unit"],
        "due": row["due_date"] or "",
        "priority": row["priority"] or "正常",
        "remark": row["remark"] or "",
        "routeKey": route_key or ("PHOTO" if row["line"] == "写真" else ""),
        "routeName": route_name,
        "createdBy": row["created_by"] or "",
        "status": row["status"],
        "qr": row["qr_token"],
        "steps": [
            {
                "no": s["step_no"],
                "name": _skill_display(conn, s["step_name"]) or (
                    fallback_names[s["step_no"] - 1]
                    if 0 < s["step_no"] <= len(fallback_names) else f"第{s['step_no']}道"
                ),
                "processName": s["step_name"] or "",
                "planned": s["planned_qty"],
                "unit": s["unit"],
                "group": serialize_step_group(conn, row["id"], int(s["step_no"])),
            }
            for s in steps
        ],
    }


def serialize_record(row) -> dict:
    return {
        "id": row["id"],
        "jobId": row["job_id"],
        "stepNo": row["step_no"],
        "employeeId": row["employee_id"],
        "qty": row["qty"],
        "unit": row["unit"],
        "at": row["created_at"],
        "status": row["status"],
        "note": row["note"] or "",
        "source": row["source"] or "scan",
        "synced": True,
        "photo": f"/api/photos/{row['photo_path']}" if row["photo_path"] else None,
        "approvedBy": row["approved_by"],
        "approvedAt": row["approved_at"],
    }


def serialize_correction(row) -> dict:
    return {
        "id": row["id"],
        "recordId": row["record_id"],
        "employeeId": row["requested_by"],
        "reason": row["reason"],
        "note": row["note"] or "",
        "status": row["status"],
        "approvedBy": row["approved_by"],
        "at": row["created_at"],
    }


def bootstrap(conn: sqlite3.Connection, user_row) -> dict:
    employees = conn.execute("SELECT * FROM employees WHERE active=1 ORDER BY employee_no").fetchall()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=BOOTSTRAP_DAYS)).isoformat(timespec="seconds")
    jobs = conn.execute(
        "SELECT * FROM production_jobs WHERE created_at >= ? OR status='active' ORDER BY created_at DESC",
        (cutoff,),
    ).fetchall()
    records = conn.execute(
        "SELECT * FROM piece_records WHERE created_at >= ? OR job_id IN "
        "(SELECT id FROM production_jobs WHERE status='active') ORDER BY created_at DESC LIMIT 20000",
        (cutoff,),
    ).fetchall()
    corrections = conn.execute(
        "SELECT * FROM corrections WHERE created_at >= ? ORDER BY created_at DESC LIMIT 1000",
        (cutoff,),
    ).fetchall()
    return {
        "user": user_payload(conn, user_row),
        "employees": [serialize_employee(conn, row) for row in employees],
        "skills": [
            {"name": r["name"], "displayName": r["display_name"], "active": bool(r["active"])}
            for r in conn.execute("SELECT * FROM skill_catalog ORDER BY sort, name")
        ],
        "routes": [
            {
                "key": r["route_key"], "line": r["line"], "name": r["name"],
                "steps": [
                    {"name": s["process_name"], "displayName": _skill_display(conn, s["process_name"])}
                    for s in conn.execute(
                        "SELECT process_name FROM route_steps WHERE route_id=? ORDER BY step_no", (r["id"],)
                    )
                ],
            }
            for r in conn.execute("SELECT * FROM routes WHERE active=1 ORDER BY sort, route_key")
        ],
        "jobs": [serialize_job(conn, row) for row in jobs],
        "records": [serialize_record(row) for row in records],
        "corrections": [serialize_correction(row) for row in corrections],
        "settings": {
            "duplicateMinutes": int(db.get_setting(conn, "duplicate_minutes", "10")),
            "tolerance": float(db.get_setting(conn, "tolerance", "0.05")),
        },
    }


def can_report(conn: sqlite3.Connection, employee_id: str, line: str, step_no: int,
               process_name: str | None = None) -> bool:
    row = conn.execute(
        "SELECT 1 FROM employees WHERE id=? AND is_admin=1",
        (employee_id,),
    ).fetchone()
    if row:
        return True
    if process_name:
        return conn.execute(
            "SELECT 1 FROM employee_process_skills WHERE employee_id=? AND process_name=?",
            (employee_id, process_name),
        ).fetchone() is not None
    return conn.execute(
        "SELECT 1 FROM employee_skills WHERE employee_id=? AND line=? AND step_no=?",
        (employee_id, line, step_no),
    ).fetchone() is not None


def step_done(conn: sqlite3.Connection, job_id: str, step_no: int, unit: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(qty), 0) AS q FROM piece_records "
        "WHERE job_id=? AND step_no=? AND status='valid' AND unit=?",
        (job_id, step_no, unit),
    ).fetchone()
    return float(row["q"] or 0)


def max_reportable(conn: sqlite3.Connection, job, step):
    """返回当前最多可报数量；None 表示没有计划量上限。"""
    done = step_done(conn, job["id"], step["step_no"], step["unit"])
    planned = float(step["planned_qty"])
    planned_left = max(0.0, planned - done) if planned > 0 else None
    if step["step_no"] == 1:
        return round(planned_left, 3) if planned_left is not None else None
    upstream = conn.execute(
        "SELECT * FROM job_steps WHERE job_id=? AND step_no=?",
        (job["id"], step["step_no"] - 1),
    ).fetchone()
    if upstream is None:
        return round(planned_left, 3) if planned_left is not None else None
    up_done = step_done(conn, job["id"], upstream["step_no"], upstream["unit"])
    if upstream["unit"] != step["unit"]:
        return round(planned_left, 3) if planned_left is not None else None
    available = max(0.0, up_done - done)
    if planned_left is not None:
        available = min(available, planned_left)
    return round(available, 3)


def _save_photo(record_id: str, data_url: str | None) -> str | None:
    if not data_url or not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        return None
    try:
        header, b64 = data_url.split(",", 1)
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        bad("现场照片格式不正确")
    if len(raw) > 2_000_000:
        bad("现场照片太大，请压缩后重试")
    ext = "png" if "png" in header.lower() else "jpg"
    folder = db.data_dir() / "photos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{record_id}.{ext}"
    (folder / filename).write_bytes(raw)
    return filename


def create_record(conn: sqlite3.Connection, user_row, payload: dict, skip_upstream: bool = False) -> tuple[dict, dict]:
    job_id = str(payload.get("jobId") or "").strip()
    try:
        step_no = int(payload.get("stepNo"))
        qty = round(float(payload.get("qty")), 3)
    except (TypeError, ValueError):
        bad("数量或工序格式不正确")
    if not job_id:
        bad("请选择订单")
    if qty <= 0 or qty > 9999:
        bad("数量必须在 0 到 9999 之间")

    job = conn.execute("SELECT * FROM production_jobs WHERE id=? AND status='active'", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在或已完成", "job_not_found", 404)
    step = conn.execute(
        "SELECT * FROM job_steps WHERE job_id=? AND step_no=?", (job_id, step_no)
    ).fetchone()
    if step is None:
        bad("工序不存在", "step_not_found", 404)
    if not can_report(conn, user_row["id"], job["line"], step_no, step["step_name"]):
        bad("你的技能不包含该工序，请联系厂长授权", "no_skill", 403)
    if step["unit"] != (payload.get("unit") or step["unit"]):
        bad("计量单位与工序配置不一致", "wrong_unit", 400)

    idem = str(payload.get("idempotencyKey") or "").strip()
    if not idem:
        idem = secrets.token_urlsafe(24)
    existing = conn.execute("SELECT * FROM piece_records WHERE idempotency_key=?", (idem,)).fetchone()
    if existing:
        return serialize_record(existing), bootstrap(conn, user_row)

    minutes = int(db.get_setting(conn, "duplicate_minutes", "10"))
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    duplicate = conn.execute(
        "SELECT * FROM piece_records WHERE employee_id=? AND job_id=? AND step_no=? "
        "AND qty=? AND status!='void' AND created_at>=? LIMIT 1",
        (user_row["id"], job_id, step_no, qty, cutoff),
    ).fetchone()
    if duplicate and not payload.get("forceDuplicate"):
        bad("疑似重复报工：刚提交过相同数量，请确认后再试", "duplicate", 409)

    max_qty = None if skip_upstream else max_reportable(conn, job, step)
    if max_qty is not None and max_qty <= 0:
        bad("上游尚未完成，暂时不能报工", "upstream_empty", 400)
    over = max_qty is not None and qty > max_qty + 0.0001
    note = str(payload.get("note") or "").strip()[:500]
    if over:
        prefix = f"超出可报数量（可报 {max_qty:g} {step['unit']}）"
        note = (prefix + ("；" + note if note else ""))[:500]

    record_id = "R" + secrets.token_hex(8).upper()
    photo_path = _save_photo(record_id, payload.get("photo"))
    now = db.utc_now()
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO piece_records(id, job_id, step_no, line, employee_id, qty, unit, status, note,"
            " idempotency_key, source, device_id, created_at, photo_path)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record_id, job_id, step_no, job["line"], user_row["id"], qty, step["unit"],
                "pending" if over else "valid", note or None, idem,
                str(payload.get("source") or "scan"), str(payload.get("deviceId") or "")[:64], now,
                photo_path,
            ),
        )
        db.audit(conn, user_row["id"], "create_record", "record", record_id, f"{job_id}/{step_no}/{qty}")
    record = conn.execute("SELECT * FROM piece_records WHERE id=?", (record_id,)).fetchone()
    return serialize_record(record), bootstrap(conn, user_row)


def _auto_step_options(conn: sqlite3.Connection, user_row, job) -> list[int]:
    """当前员工在该订单上还能报的工序，不检查上游是否完成。"""
    rows = conn.execute(
        "SELECT step_no, step_name FROM job_steps WHERE job_id=? ORDER BY step_no", (job["id"],)
    ).fetchall()
    result = []
    for row in rows:
        no = int(row["step_no"])
        if not can_report(conn, user_row["id"], job["line"], no, row["step_name"]):
            continue
        existing = conn.execute(
            "SELECT 1 FROM piece_records WHERE job_id=? AND step_no=? AND status!='void' LIMIT 1",
            (job["id"], no),
        ).fetchone()
        if existing:
            continue
        result.append(no)
    return result


def auto_report_options(conn: sqlite3.Connection, user_row, job_id: str) -> dict:
    job = conn.execute(
        "SELECT * FROM production_jobs WHERE id=? AND status='active'", (job_id,)
    ).fetchone()
    if job is None:
        bad("订单不存在或已完成", "job_not_found", 404)
    qty = float(job["meters"] or job["planned_qty"] or 0)
    if qty <= 0:
        bad("订单没有填写米数/数量，不能自动报工", "missing_quantity", 400)
    return {
        "jobId": job["id"],
        "orderNo": job["order_no"],
        "line": job["line"],
        "qty": qty,
        "unit": job["unit"],
        "stepNos": _auto_step_options(conn, user_row, job),
        "steps": [
            {
                "no": row["step_no"],
                "name": _skill_display(conn, row["step_name"]) or f"第{row['step_no']}道",
            }
            for row in conn.execute(
                "SELECT step_no, step_name FROM job_steps WHERE job_id=? ORDER BY step_no",
                (job["id"],),
            ).fetchall()
            if int(row["step_no"]) in _auto_step_options(conn, user_row, job)
        ],
    }


def _close_open_groups_before(conn: sqlite3.Connection, job, step_no: int, actor_id: str) -> None:
    rows = conn.execute(
        "SELECT * FROM job_step_groups WHERE job_id=? AND step_no<? AND status='open' ORDER BY step_no",
        (job["id"], step_no),
    ).fetchall()
    for group in rows:
        _close_group_internal(conn, job, group, actor_id, "下一道工序开始，自动结束")


def _close_group_internal(conn: sqlite3.Connection, job, group, actor_id: str, reason: str) -> None:
    if group["status"] != "open":
        return
    members = conn.execute(
        "SELECT employee_id FROM job_step_group_members WHERE group_id=? ORDER BY joined_at",
        (group["id"],),
    ).fetchall()
    if not members:
        with db.transaction(conn):
            conn.execute("UPDATE job_step_groups SET status='closed', closed_by=?, closed_at=?, close_reason=? WHERE id=?",
                         (actor_id, db.utc_now(), reason, group["id"]))
        return
    total = float(job["meters"] or job["planned_qty"] or 0)
    count = len(members)
    per = round(total / count, 3)
    with db.transaction(conn):
        for index, member in enumerate(members):
            qty = round(total - per * (count - 1), 3) if index == count - 1 else per
            record_id = "R" + secrets.token_hex(8).upper()
            conn.execute(
                "INSERT INTO piece_records(id, job_id, step_no, line, employee_id, qty, unit, status, note,"
                " idempotency_key, source, device_id, created_at, photo_path)"
                " VALUES(?,?,?,?,?,?,?,'valid',?,?, 'group', '', ?, NULL)",
                (record_id, job["id"], group["step_no"], job["line"], member["employee_id"], qty, group["unit"],
                 f"合报平分：{reason}", "GROUP-" + group["id"] + "-" + member["employee_id"], db.utc_now()),
            )
            conn.execute("UPDATE job_step_group_members SET record_id=? WHERE group_id=? AND employee_id=?",
                         (record_id, group["id"], member["employee_id"]))
            db.audit(conn, actor_id, "group_split", "record", record_id, f"{group['id']}/{qty}")
        conn.execute(
            "UPDATE job_step_groups SET status='closed', closed_by=?, closed_at=?, close_reason=? WHERE id=?",
            (actor_id, db.utc_now(), reason, group["id"]),
        )


def _can_manage_job(actor, job) -> bool:
    return bool(actor["is_admin"]) or job["created_by"] == actor["id"]


def close_group(conn: sqlite3.Connection, actor, job_id: str, step_no: int, reason: str) -> tuple[dict, dict]:
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在", "not_found", 404)
    if not _can_manage_job(actor, job):
        bad("只有厂长或建单人才能结束合报", "forbidden", 403)
    group = conn.execute("SELECT * FROM job_step_groups WHERE job_id=? AND step_no=?", (job_id, step_no)).fetchone()
    if group is None:
        bad("该工序没有合报组", "group_not_found", 404)
    _close_group_internal(conn, job, group, actor["id"], reason or "手动结束合报")
    return serialize_job(conn, job), bootstrap(conn, actor)


def remove_group_member(conn: sqlite3.Connection, actor, job_id: str, step_no: int, employee_id: str) -> dict:
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在", "not_found", 404)
    if not _can_manage_job(actor, job):
        bad("只有厂长或建单人才能移除参与人", "forbidden", 403)
    group = conn.execute("SELECT * FROM job_step_groups WHERE job_id=? AND step_no=?", (job_id, step_no)).fetchone()
    if group is None or group["status"] != "open":
        bad("合报组不存在或已结束", "group_closed", 400)
    with db.transaction(conn):
        conn.execute("DELETE FROM job_step_group_members WHERE group_id=? AND employee_id=?", (group["id"], employee_id))
        db.audit(conn, actor["id"], "group_remove_member", "employee", employee_id, group["id"])
    return bootstrap(conn, actor)


def complete_job(conn: sqlite3.Connection, actor, job_id: str) -> tuple[dict, dict]:
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在", "not_found", 404)
    if not _can_manage_job(actor, job):
        bad("只有厂长或建单人才能完成订单", "forbidden", 403)
    if job["status"] != "active":
        bad("订单不是进行中", "not_active", 400)
    for group in conn.execute(
        "SELECT * FROM job_step_groups WHERE job_id=? AND status='open' ORDER BY step_no", (job_id,)
    ).fetchall():
        _close_group_internal(conn, job, group, actor["id"], "完成订单，自动结束合报")
    rows = conn.execute(
        "SELECT s.step_no, (SELECT COUNT(*) FROM piece_records r WHERE r.job_id=s.job_id AND r.step_no=s.step_no "
        "AND r.status='valid') AS n FROM job_steps s WHERE s.job_id=? ORDER BY s.step_no", (job_id,)
    ).fetchall()
    missing = [str(r["step_no"]) for r in rows if not r["n"]]
    if missing:
        bad("还有工序未完成：" + "、".join(missing), "steps_incomplete", 400)
    with db.transaction(conn):
        conn.execute("UPDATE production_jobs SET status='completed' WHERE id=?", (job_id,))
        db.audit(conn, actor["id"], "complete_job", "job", job_id, "完成订单")
    row = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    return serialize_job(conn, row), bootstrap(conn, actor)


def auto_report(conn: sqlite3.Connection, user_row, job_id: str, step_no: int | None = None) -> tuple[dict, dict]:
    """扫码自动报工：员工可自选工序，不要求上一道工序已经报工。"""
    job = conn.execute(
        "SELECT * FROM production_jobs WHERE id=? AND status='active'", (job_id,)
    ).fetchone()
    if job is None:
        bad("订单不存在或已完成", "job_not_found", 404)

    qty = float(job["meters"] or job["planned_qty"] or 0)
    if qty <= 0:
        bad("订单没有填写米数/数量，不能自动报工", "missing_quantity", 400)

    if step_no is not None:
        step = conn.execute(
            "SELECT * FROM job_steps WHERE job_id=? AND step_no=?", (job["id"], step_no)
        ).fetchone()
        if step is None:
            bad("工序不存在", "step_not_found", 404)
        if not can_report(conn, user_row["id"], job["line"], step_no, step["step_name"]):
            bad("你的技能不包含该工序，请联系厂长授权", "no_skill", 403)
        existing = conn.execute(
            "SELECT 1 FROM piece_records WHERE job_id=? AND step_no=? AND status!='void' LIMIT 1",
            (job["id"], step_no),
        ).fetchone()
        if existing:
            bad("该工序已经报工，不能重复报", "step_done", 409)
        chosen = step_no
    else:
        options = _auto_step_options(conn, user_row, job)
        if not options:
            if conn.execute(
                "SELECT 1 FROM piece_records WHERE job_id=? AND status!='void' LIMIT 1", (job["id"],)
            ).fetchone():
                bad("订单已全部报工或等待确认", "job_done", 409)
            bad("当前没有你可以自动报工的工序", "no_step", 403)
        chosen = options[0]

    step = conn.execute(
        "SELECT * FROM job_steps WHERE job_id=? AND step_no=?", (job["id"], chosen)
    ).fetchone()
    if step is None:
        bad("工序不存在", "step_not_found", 404)
    process_name = step["step_name"] or ""
    _close_open_groups_before(conn, job, chosen, user_row["id"])

    if process_name in GROUP_PROCESS_NAMES:
        group = conn.execute(
            "SELECT * FROM job_step_groups WHERE job_id=? AND step_no=?", (job["id"], chosen)
        ).fetchone()
        if group is not None and group["status"] != "open":
            bad("该工序合报已经结束，不能重复报", "step_done", 409)
        if group is None:
            group_id = "G" + secrets.token_hex(8).upper()
            with db.transaction(conn):
                conn.execute(
                    "INSERT INTO job_step_groups(id, job_id, step_no, status, total_qty, unit, created_by, created_at)"
                    " VALUES(?,?,?, 'open', ?,?,?,?)",
                    (group_id, job["id"], chosen, qty, job["unit"], user_row["id"], db.utc_now()),
                )
                db.audit(conn, user_row["id"], "group_open", "job", job["id"], f"step={chosen}")
            group = conn.execute("SELECT * FROM job_step_groups WHERE id=?", (group_id,)).fetchone()
        if conn.execute(
            "SELECT 1 FROM job_step_group_members WHERE group_id=? AND employee_id=?",
            (group["id"], user_row["id"]),
        ).fetchone() is None:
            with db.transaction(conn):
                conn.execute(
                    "INSERT INTO job_step_group_members(group_id, employee_id, joined_at) VALUES(?,?,?)",
                    (group["id"], user_row["id"], db.utc_now()),
                )
                db.audit(conn, user_row["id"], "group_join", "job", job["id"], f"step={chosen}")
        data = bootstrap(conn, user_row)
        data["group"] = serialize_step_group(conn, job["id"], chosen)
        return None, data

    payload = {
        "jobId": job["id"],
        "stepNo": chosen,
        "qty": qty,
        "unit": job["unit"],
        "note": "扫码自动报工",
        "source": "auto",
        "idempotencyKey": "AUTO-" + secrets.token_urlsafe(24),
    }
    return create_record(conn, user_row, payload, skip_upstream=True)


def create_job(conn: sqlite3.Connection, user_row, payload: dict) -> tuple[dict, dict]:
    """排版人员建单：只收单位、订单号、备注。

    产线不再手工填写，按单位自动归类：
    m² 归写真线；件/套/块归亚克力线。
    """
    unit = str(payload.get("unit") or "").strip()
    if unit not in ("m²", "件", "套", "块"):
        bad("计量单位不支持")
    line = str(payload.get("line") or "").strip()
    if line not in ("写真", "亚克力"):
        line = "写真" if unit == "m²" else "亚克力"
    route_key = str(payload.get("routeKey") or ("PHOTO" if line == "写真" else "A")).strip().upper()
    route = conn.execute(
        "SELECT * FROM routes WHERE route_key=? AND active=1", (route_key,)
    ).fetchone()
    if route is None or route["line"] != line:
        bad("工艺路线不存在", "route_not_found", 400)
    route_steps = [
        r["process_name"] for r in conn.execute(
            "SELECT process_name FROM route_steps WHERE route_id=? ORDER BY step_no", (route["id"],)
        )
    ]
    if not route_steps:
        bad("该路线还没有工序", "route_empty", 400)
    order_no = str(payload.get("orderNo") or "").strip()[:64]
    remark = str(payload.get("remark") or "").strip()[:500]
    try:
        meters = round(float(payload.get("meters") or 0), 3)
    except (TypeError, ValueError):
        bad("米数格式不正确")
    if meters < 0 or meters > 999999:
        bad("米数必须在 0 到 999999 之间")
    stamp = datetime.now().strftime("%Y%m%d")
    if not order_no:
        order_no = f"TB{stamp}{secrets.randbelow(900) + 100}"
    if conn.execute("SELECT 1 FROM production_jobs WHERE order_no=?", (order_no,)).fetchone():
        bad("订单号已存在", "order_exists", 409)

    job_id = "J" + secrets.token_hex(6).upper()
    qr_token = "QJ-" + secrets.token_urlsafe(18)
    now = db.utc_now()
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO production_jobs(id, order_no, line, product, spec, customer, planned_qty,"
            " meters, unit, due_date, priority, remark, route_key, status, qr_token, created_by, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, 'active', ?,?,?)",
            (
                job_id, order_no, line, "", "", "", 0, meters, unit, None, "正常", remark or None,
                route_key, qr_token, user_row["id"], now,
            ),
        )
        for step, step_name in enumerate(route_steps, 1):
            conn.execute(
                "INSERT INTO job_steps(job_id, step_no, step_name, planned_qty, unit) VALUES(?,?,?,?,?)",
                (job_id, step, step_name, 0, unit),
            )
        db.audit(conn, user_row["id"], "create_job", "job", job_id, f"{order_no}/{unit}/{line}/{route_key}")
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    return serialize_job(conn, job), bootstrap(conn, user_row)


def edit_job(conn: sqlite3.Connection, admin_row, job_id: str, payload: dict) -> tuple[dict, dict]:
    """厂长修改订单：订单号、米数、备注；已报工的订单不能改米数。"""
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在", "not_found", 404)
    if job["status"] != "active":
        bad("只有进行中的订单可以修改", "job_not_active", 400)

    order_no = str(payload.get("orderNo") or job["order_no"]).strip()[:64]
    if not order_no:
        bad("订单号不能为空")
    exists = conn.execute(
        "SELECT 1 FROM production_jobs WHERE order_no=? AND id<>?", (order_no, job_id)
    ).fetchone()
    if exists:
        bad("订单号已存在", "order_exists", 409)

    try:
        meters = round(float(payload.get("meters", job["meters"]) or 0), 3)
    except (TypeError, ValueError):
        bad("米数格式不正确")
    if meters < 0 or meters > 999999:
        bad("米数必须在 0 到 999999 之间")

    reported = conn.execute(
        "SELECT COUNT(*) AS n FROM piece_records WHERE job_id=? AND status!='void'", (job_id,)
    ).fetchone()["n"]
    if reported and abs(meters - float(job["meters"] or 0)) > 0.0001:
        bad("订单已有报工记录，不能修改米数；只能改订单号或备注", "job_has_records", 409)

    remark = str(payload.get("remark") if payload.get("remark") is not None else job["remark"] or "").strip()[:500]
    with db.transaction(conn):
        conn.execute(
            "UPDATE production_jobs SET order_no=?, meters=?, remark=? WHERE id=?",
            (order_no, meters, remark or None, job_id),
        )
        db.audit(conn, admin_row["id"], "edit_job", "job", job_id, f"{order_no}/{meters}")
    row = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    return serialize_job(conn, row), bootstrap(conn, admin_row)


def void_job(conn: sqlite3.Connection, admin_row, job_id: str, reason: str) -> tuple[dict, dict]:
    """作废订单：不物理删除，订单和报工记录都标记为 void，保留审计。"""
    job = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    if job is None:
        bad("订单不存在", "not_found", 404)
    if job["status"] != "active":
        bad("只有进行中的订单可以作废", "job_not_active", 400)
    note = (reason or "厂长作废")[:200]
    with db.transaction(conn):
        conn.execute("UPDATE production_jobs SET status='void' WHERE id=?", (job_id,))
        conn.execute(
            "UPDATE piece_records SET status='void', note=COALESCE(note,'') || ? WHERE job_id=?",
            (" · 订单作废：" + note, job_id),
        )
        conn.execute(
            "UPDATE corrections SET status='rejected', note=COALESCE(note,'') || ? "
            "WHERE status='pending' AND record_id IN (SELECT id FROM piece_records WHERE job_id=?)",
            (" · 订单作废", job_id),
        )
        db.audit(conn, admin_row["id"], "void_job", "job", job_id, note)
    row = conn.execute("SELECT * FROM production_jobs WHERE id=?", (job_id,)).fetchone()
    return serialize_job(conn, row), bootstrap(conn, admin_row)


def clear_production_data(conn: sqlite3.Connection, admin_row, password: str, confirm: str) -> dict:
    """清空订单/报工/审批数据，保留员工、技能、设置；清空前自动备份。"""
    if not verify_secret(password or "", admin_row["pin_hash"]):
        bad("管理员密码不正确", "wrong_password", 403)
    if (confirm or "").strip() != "清空":
        bad("确认文字不对，请输入：清空", "confirm_required", 400)
    backup_dir = db.data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / ("jitong-before-clear-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")
    dest = sqlite3.connect(backup)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    with db.transaction(conn):
        conn.execute("DELETE FROM corrections")
        conn.execute("DELETE FROM piece_records")
        conn.execute("DELETE FROM job_steps")
        conn.execute("DELETE FROM production_jobs")
        conn.execute("DELETE FROM audit_log")
        db.audit(conn, admin_row["id"], "clear_production_data", "system", "", f"backup={backup.name}")
    return {"ok": True, "backup": backup.name, "data": bootstrap(conn, admin_row)}


def approve_record(conn: sqlite3.Connection, admin_row, record_id: str) -> dict:
    record = conn.execute("SELECT * FROM piece_records WHERE id=?", (record_id,)).fetchone()
    if record is None:
        bad("记录不存在", "not_found", 404)
    if record["status"] != "pending":
        bad("只有待确认记录可以确认", "not_pending", 400)
    with db.transaction(conn):
        conn.execute(
            "UPDATE piece_records SET status='valid', approved_by=?, approved_at=? WHERE id=?",
            (admin_row["id"], db.utc_now(), record_id),
        )
        db.audit(conn, admin_row["id"], "approve_record", "record", record_id, "")
    return bootstrap(conn, admin_row)


def reject_record(conn: sqlite3.Connection, admin_row, record_id: str, reason: str) -> dict:
    record = conn.execute("SELECT * FROM piece_records WHERE id=?", (record_id,)).fetchone()
    if record is None:
        bad("记录不存在", "not_found", 404)
    if record["status"] != "pending":
        bad("只有待确认记录可以驳回", "not_pending", 400)
    note = ((record["note"] or "") + " · 驳回：" + (reason or "厂长驳回"))[:500]
    with db.transaction(conn):
        conn.execute(
            "UPDATE piece_records SET status='void', note=?, approved_by=?, approved_at=? WHERE id=?",
            (note, admin_row["id"], db.utc_now(), record_id),
        )
        db.audit(conn, admin_row["id"], "reject_record", "record", record_id, reason or "")
    return bootstrap(conn, admin_row)


def request_correction(conn: sqlite3.Connection, user_row, record_id: str, reason: str, note: str) -> dict:
    record = conn.execute("SELECT * FROM piece_records WHERE id=?", (record_id,)).fetchone()
    if record is None:
        bad("记录不存在", "not_found", 404)
    if record["employee_id"] != user_row["id"]:
        bad("只能申请更正自己的记录", "forbidden", 403)
    if record["status"] != "valid":
        bad("只有已计入记录可以申请冲销", "not_valid", 400)
    pending = conn.execute(
        "SELECT 1 FROM corrections WHERE record_id=? AND status='pending'", (record_id,)
    ).fetchone()
    if pending:
        bad("该记录已有待审批的冲销申请", "already_pending", 409)
    cid = "C" + secrets.token_hex(8).upper()
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO corrections(id, record_id, reason, note, status, requested_by, created_at)"
            " VALUES(?,?,?,?, 'pending', ?,?)",
            (cid, record_id, reason[:64], note[:500], user_row["id"], db.utc_now()),
        )
        db.audit(conn, user_row["id"], "request_correction", "correction", cid, record_id)
    return bootstrap(conn, user_row)


def decide_correction(conn: sqlite3.Connection, admin_row, correction_id: str, approve: bool) -> dict:
    correction = conn.execute("SELECT * FROM corrections WHERE id=?", (correction_id,)).fetchone()
    if correction is None:
        bad("冲销申请不存在", "not_found", 404)
    if correction["status"] != "pending":
        bad("该申请已处理", "already_decided", 400)
    with db.transaction(conn):
        conn.execute(
            "UPDATE corrections SET status=?, approved_by=?, decided_at=? WHERE id=?",
            ("approved" if approve else "rejected", admin_row["id"], db.utc_now(), correction_id),
        )
        if approve:
            conn.execute("UPDATE piece_records SET status='void' WHERE id=?", (correction["record_id"],))
        db.audit(
            conn, admin_row["id"],
            "approve_correction" if approve else "reject_correction",
            "correction", correction_id, correction["record_id"],
        )
    return bootstrap(conn, admin_row)


def set_create_permission(conn: sqlite3.Connection, admin_row, employee_id: str, allowed: bool) -> dict:
    employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if employee is None:
        bad("员工不存在", "not_found", 404)
    if employee["is_admin"]:
        bad("管理员不能建单，也不能被授予建单权限", "admin_cannot_create", 400)
    if not employee["active"]:
        bad("停用员工不能授予建单权限", "inactive", 400)

    if not allowed and employee["can_create_job"]:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM employees "
            "WHERE active=1 AND is_admin=0 AND can_create_job=1"
        ).fetchone()["n"]
        if count <= 1:
            bad("至少保留一名可建单人员", "last_creator", 400)

    with db.transaction(conn):
        conn.execute(
            "UPDATE employees SET can_create_job=? WHERE id=?",
            (1 if allowed else 0, employee_id),
        )
        db.audit(
            conn, admin_row["id"], "set_create_permission", "employee", employee_id,
            "允许建单" if allowed else "取消建单",
        )
    return bootstrap(conn, admin_row)


def add_skill(conn: sqlite3.Connection, admin_row, name: str) -> dict:
    name = str(name or "").strip()[:40]
    if not name:
        bad("技能名称不能为空", "name_required", 400)
    if conn.execute("SELECT 1 FROM skill_catalog WHERE name=?", (name,)).fetchone():
        bad("技能名称已存在", "skill_exists", 409)
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO skill_catalog(name, display_name, active, sort, created_at) VALUES(?,?,1,999,?)",
            (name, name, db.utc_now()),
        )
        db.audit(conn, admin_row["id"], "add_skill", "skill", name, name)
    return bootstrap(conn, admin_row)


def rename_skill(conn: sqlite3.Connection, admin_row, name: str, display_name: str) -> dict:
    name = str(name or "").strip()
    display_name = str(display_name or "").strip()[:40]
    if not display_name:
        bad("显示名称不能为空", "name_required", 400)
    if conn.execute("SELECT 1 FROM skill_catalog WHERE name=?", (name,)).fetchone() is None:
        bad("技能不存在", "not_found", 404)
    with db.transaction(conn):
        conn.execute("UPDATE skill_catalog SET display_name=? WHERE name=?", (display_name, name))
        db.audit(conn, admin_row["id"], "rename_skill", "skill", name, display_name)
    return bootstrap(conn, admin_row)


def delete_skill(conn: sqlite3.Connection, admin_row, name: str) -> dict:
    name = str(name or "").strip()
    assigned = conn.execute("SELECT COUNT(*) AS n FROM employee_process_skills WHERE process_name=?", (name,)).fetchone()["n"]
    used = conn.execute("SELECT COUNT(*) AS n FROM job_steps WHERE step_name=?", (name,)).fetchone()["n"]
    if assigned or used:
        bad("该技能已被员工或订单使用，只能停用，不能删除", "skill_in_use", 400)
    with db.transaction(conn):
        conn.execute("DELETE FROM skill_catalog WHERE name=?", (name,))
        db.audit(conn, admin_row["id"], "delete_skill", "skill", name, name)
    return bootstrap(conn, admin_row)


def save_route(conn: sqlite3.Connection, admin_row, route_key: str | None, payload: dict) -> dict:
    line = str(payload.get("line") or "").strip()
    name = str(payload.get("name") or "").strip()[:60]
    steps = [str(s or "").strip() for s in (payload.get("steps") or []) if str(s or "").strip()]
    if line not in ("写真", "亚克力") or not name or not steps:
        bad("路线名称、产线和工序不能为空", "bad_route", 400)
    allowed = {r["name"] for r in conn.execute("SELECT name FROM skill_catalog WHERE active=1")}
    if any(s not in allowed for s in steps):
        bad("路线中有未知工序", "unknown_process", 400)
    with db.transaction(conn):
        if route_key:
            route = conn.execute("SELECT * FROM routes WHERE route_key=?", (route_key,)).fetchone()
            if route is None:
                bad("路线不存在", "not_found", 404)
            conn.execute("UPDATE routes SET line=?, name=? WHERE id=?", (line, name, route["id"]))
            route_id = route["id"]
            conn.execute("DELETE FROM route_steps WHERE route_id=?", (route_id,))
        else:
            route_key = "R" + secrets.token_hex(4).upper()
            route_id = "RT-" + route_key
            conn.execute(
                "INSERT INTO routes(id, route_key, line, name, active, sort, created_at) VALUES(?,?,?,?,1,999,?)",
                (route_id, route_key, line, name, db.utc_now()),
            )
        for step_no, process_name in enumerate(steps, start=1):
            conn.execute(
                "INSERT INTO route_steps(route_id, step_no, process_name) VALUES(?,?,?)",
                (route_id, step_no, process_name),
            )
        db.audit(conn, admin_row["id"], "save_route", "route", route_key, f"{line}/{name}/{len(steps)}")
    return bootstrap(conn, admin_row)


def delete_route(conn: sqlite3.Connection, admin_row, route_key: str) -> dict:
    used = conn.execute("SELECT COUNT(*) AS n FROM production_jobs WHERE route_key=?", (route_key,)).fetchone()["n"]
    if used:
        bad("该路线已被订单使用，不能删除", "route_in_use", 400)
    route = conn.execute("SELECT * FROM routes WHERE route_key=?", (route_key,)).fetchone()
    if route is None:
        bad("路线不存在", "not_found", 404)
    with db.transaction(conn):
        conn.execute("DELETE FROM routes WHERE id=?", (route["id"],))
        db.audit(conn, admin_row["id"], "delete_route", "route", route_key, route["name"])
    return bootstrap(conn, admin_row)


def update_employee(conn: sqlite3.Connection, admin_row, employee_id: str, payload: dict) -> dict:
    employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if employee is None:
        bad("员工不存在", "not_found", 404)
    if employee["is_admin"]:
        bad("管理员姓名请使用厂长改名工具", "admin_rename", 400)
    name = str(payload.get("name") or "").strip()[:40]
    role = str(payload.get("role") if payload.get("role") is not None else employee["role"]).strip()[:60]
    if not name:
        bad("员工姓名不能为空", "name_required", 400)
    with db.transaction(conn):
        conn.execute(
            "UPDATE employees SET name=?, role=?, avatar=? WHERE id=?",
            (name, role or employee["role"], name[:1], employee_id),
        )
        db.audit(conn, admin_row["id"], "update_employee", "employee", employee_id, f"{employee['name']} -> {name}")
    return bootstrap(conn, admin_row)


def add_employee(conn: sqlite3.Connection, admin_row, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()[:40]
    role = str(payload.get("role") or "员工").strip()[:60]
    try:
        employee_no = int(payload.get("employeeNo"))
    except (TypeError, ValueError):
        bad("工号必须是数字", "bad_employee_no", 400)
    pin = str(payload.get("pin") or "").strip()
    if not name:
        bad("请输入员工姓名", "name_required", 400)
    if employee_no <= 0 or employee_no > 9999:
        bad("工号必须在 1 到 9999 之间", "bad_employee_no", 400)
    if len(pin) != 6:
        bad("员工 PIN 必须是 6 位", "bad_pin", 400)
    if conn.execute("SELECT 1 FROM employees WHERE employee_no=?", (employee_no,)).fetchone():
        bad("工号已存在", "employee_no_exists", 409)
    allowed = {r["name"] for r in conn.execute("SELECT name FROM skill_catalog WHERE active=1")}
    process_skills = []
    for item in payload.get("processSkills") or []:
        item = str(item or "").strip()
        if item and item not in allowed:
            bad(f"未知工序：{item}", "unknown_process", 400)
        if item and item not in process_skills:
            process_skills.append(item)
    employee_id = "E" + secrets.token_hex(3).upper()
    now = db.utc_now()
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO employees(id, employee_no, name, role, avatar, is_admin, can_create_job, active, pin_hash, created_at)"
            " VALUES(?,?,?,?,?,0,?,1,?,?)",
            (
                employee_id, employee_no, name, role, name[:1],
                1 if payload.get("canCreateJob") else 0, hash_secret(pin), now,
            ),
        )
        for process_name in process_skills:
            conn.execute(
                "INSERT INTO employee_process_skills(employee_id, process_name) VALUES(?,?)",
                (employee_id, process_name),
            )
        db.audit(conn, admin_row["id"], "add_employee", "employee", employee_id,
                 f"{employee_no}/{name}/{','.join(process_skills)}")
    return bootstrap(conn, admin_row)


def deactivate_employee(conn: sqlite3.Connection, admin_row, employee_id: str) -> dict:
    employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if employee is None:
        bad("员工不存在", "not_found", 404)
    if employee["is_admin"]:
        bad("不能停用管理员账号", "admin_cannot_deactivate", 400)
    if not employee["active"]:
        return bootstrap(conn, admin_row)
    with db.transaction(conn):
        conn.execute("UPDATE employees SET active=0 WHERE id=?", (employee_id,))
        conn.execute("DELETE FROM sessions WHERE employee_id=?", (employee_id,))
        db.audit(conn, admin_row["id"], "deactivate_employee", "employee", employee_id, employee["name"])
    return bootstrap(conn, admin_row)


def set_process_skills(conn: sqlite3.Connection, admin_row, employee_id: str, processes: list[str]) -> dict:
    employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if employee is None:
        bad("员工不存在", "not_found", 404)
    if employee["is_admin"]:
        bad("管理员不能设置工序技能", "admin_skill", 400)
    allowed = {r["name"] for r in conn.execute("SELECT name FROM skill_catalog WHERE active=1")}
    cleaned = []
    for name in processes or []:
        name = str(name or "").strip()
        if not name:
            continue
        if name not in allowed:
            bad(f"未知工序：{name}", "unknown_process", 400)
        if name not in cleaned:
            cleaned.append(name)
    with db.transaction(conn):
        conn.execute("DELETE FROM employee_process_skills WHERE employee_id=?", (employee_id,))
        for name in cleaned:
            conn.execute(
                "INSERT INTO employee_process_skills(employee_id, process_name) VALUES(?,?)",
                (employee_id, name),
            )
        db.audit(conn, admin_row["id"], "set_process_skills", "employee", employee_id, "、".join(cleaned))
    return bootstrap(conn, admin_row)


def reset_pin(conn: sqlite3.Connection, admin_row, employee_id: str) -> str:
    employee = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if employee is None:
        bad("员工不存在", "not_found", 404)
    if employee["is_admin"]:
        bad("管理员密码请使用修改密码功能", "admin_pin", 400)
    pin = f"{secrets.randbelow(900000) + 100000}"
    with db.transaction(conn):
        conn.execute("UPDATE employees SET pin_hash=? WHERE id=?", (hash_secret(pin), employee_id))
        db.audit(conn, admin_row["id"], "reset_pin", "employee", employee_id, "")
    return pin


def change_password(conn: sqlite3.Connection, user_row, old: str, new: str) -> None:
    if not verify_secret(old or "", user_row["pin_hash"]):
        bad("原密码不正确", "wrong_password", 403)
    if len(new or "") < 6:
        bad("新密码至少 6 位", "weak_password", 400)
    with db.transaction(conn):
        conn.execute("UPDATE employees SET pin_hash=? WHERE id=?", (hash_secret(new), user_row["id"]))
        db.audit(conn, user_row["id"], "change_password", "employee", user_row["id"], "")
