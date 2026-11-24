# -*- coding: utf-8 -*-
"""建单权限：数据库字段、管理员限制、最后一个建单人保护。"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from server import service


def get_user(conn, employee_id):
    return conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()


def test_seed_permissions_are_in_database(app_db):
    assert service.can_create_job(get_user(app_db, "E005")) is True
    assert service.can_create_job(get_user(app_db, "E007")) is True
    assert service.can_create_job(get_user(app_db, "E011")) is True
    assert service.can_create_job(get_user(app_db, "E004")) is False
    assert service.can_create_job(get_user(app_db, "A001")) is False


def test_admin_cannot_be_granted_create_permission(app_db):
    admin = get_user(app_db, "A001")
    with pytest.raises(HTTPException) as exc:
        service.set_create_permission(app_db, admin, "A001", True)
    assert exc.value.status_code == 400
    assert service.can_create_job(get_user(app_db, "A001")) is False


def test_grant_and_revoke_permission_persists(app_db):
    admin = get_user(app_db, "A001")
    service.set_create_permission(app_db, admin, "E004", True)
    assert service.can_create_job(get_user(app_db, "E004")) is True

    service.set_create_permission(app_db, admin, "E004", False)
    assert service.can_create_job(get_user(app_db, "E004")) is False


def test_cannot_remove_last_creator(app_db):
    admin = get_user(app_db, "A001")
    for employee_id in ("E005", "E011", "E012", "E016"):
        service.set_create_permission(app_db, admin, employee_id, False)

    creators = app_db.execute(
        "SELECT id FROM employees WHERE active=1 AND is_admin=0 AND can_create_job=1"
    ).fetchall()
    assert [row["id"] for row in creators] == ["E007"]

    with pytest.raises(HTTPException) as exc:
        service.set_create_permission(app_db, admin, "E007", False)
    assert exc.value.status_code == 400
    assert "至少保留" in exc.value.detail["message"]
    assert service.can_create_job(get_user(app_db, "E007")) is True
