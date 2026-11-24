# -*- coding: utf-8 -*-
"""订单与报工核心规则：三字段建单、产线推断、无计划量、上游校验。"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from server import service


def user(conn, employee_id):
    return conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()


def create(conn, unit, order_no, remark="", meters=0):
    job, _ = service.create_job(
        conn,
        user(conn, "E007"),
        {"unit": unit, "orderNo": order_no, "remark": remark, "meters": meters},
    )
    return job


def report(conn, job_id, step, qty, unit, key):
    return service.create_record(
        conn,
        user(conn, "E007"),
        {
            "jobId": job_id,
            "stepNo": step,
            "qty": qty,
            "unit": unit,
            "idempotencyKey": key,
        },
    )[0]


def test_create_job_only_three_fields_and_line_inference(app_db):
    m2 = create(app_db, "m²", "TEST-M2", "写真面积单")
    pieces = create(app_db, "件", "TEST-PCS", "亚克力件数单")

    assert m2["line"] == "写真"
    assert m2["plannedQty"] == 0
    assert m2["remark"] == "写真面积单"
    assert pieces["line"] == "亚克力"
    assert pieces["unit"] == "件"


def test_meters_are_saved_and_returned(app_db):
    job = create(app_db, "m²", "TEST-METERS", "米数单", meters=120.5)
    assert job["meters"] == 120.5
    row = app_db.execute("SELECT meters FROM production_jobs WHERE id=?", (job["id"],)).fetchone()
    assert row["meters"] == 120.5


def test_duplicate_order_number_rejected(app_db):
    create(app_db, "件", "TEST-DUP")
    with pytest.raises(HTTPException) as exc:
        create(app_db, "件", "TEST-DUP")
    assert exc.value.status_code == 409


def test_no_plan_step_allows_multiple_batches(app_db):
    job = create(app_db, "件", "TEST-BATCH")
    first = report(app_db, job["id"], 1, 3, "件", "batch-1")
    second = report(app_db, job["id"], 1, 2, "件", "batch-2")
    assert first["status"] == "valid"
    assert second["status"] == "valid"

    row = app_db.execute(
        "SELECT COALESCE(SUM(qty),0) AS n FROM piece_records "
        "WHERE job_id=? AND step_no=1 AND status='valid'",
        (job["id"],),
    ).fetchone()
    assert row["n"] == 5


def test_auto_report_uses_order_quantity_and_next_step(app_db):
    job = create(app_db, "m²", "TEST-AUTO", "自动报工", meters=10)
    first, _ = service.auto_report(app_db, user(app_db, "E007"), job["id"])
    assert first["stepNo"] == 1
    assert first["qty"] == 10
    assert first["unit"] == "m²"
    assert first["status"] == "valid"

    second, _ = service.auto_report(app_db, user(app_db, "E007"), job["id"])
    assert second["stepNo"] == 2
    assert second["qty"] == 10


def test_auto_report_rejects_order_without_quantity(app_db):
    job = create(app_db, "件", "TEST-AUTO-EMPTY", "无数量", meters=0)
    with pytest.raises(HTTPException) as exc:
        service.auto_report(app_db, user(app_db, "E007"), job["id"])
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "missing_quantity"


def test_auto_report_requires_employee_step_skill(app_db):
    job = create(app_db, "m²", "TEST-AUTO-SKILL", "技能", meters=10)
    with pytest.raises(HTTPException) as exc:
        service.auto_report(app_db, user(app_db, "E013"), job["id"])
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "no_step"


def test_upstream_must_report_first(app_db):
    job = create(app_db, "件", "TEST-UPSTREAM")
    with pytest.raises(HTTPException) as exc:
        report(app_db, job["id"], 2, 1, "件", "up-2-before")
    assert exc.value.status_code == 400

    report(app_db, job["id"], 1, 5, "件", "up-1")
    second = report(app_db, job["id"], 2, 2, "件", "up-2-after")
    assert second["status"] == "valid"
