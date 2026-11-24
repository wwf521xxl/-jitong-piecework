# -*- coding: utf-8 -*-
"""HTTP API 权限回归：管理员不能建单，排版人员可以，授权后普通员工可以。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server import db, security
from server.main import app


def session_cookie(employee_id):
    conn = db.connect()
    try:
        return security.create_session(conn, employee_id)
    finally:
        conn.close()


def client_with(employee_id):
    client = TestClient(app)
    client.cookies.set("jitong_session", session_cookie(employee_id))
    return client


def test_admin_login_but_cannot_create_job(app_db):
    with TestClient(app) as client:
        login = client.post("/api/login", json={"account": "admin", "pin": "AdminTest123"})
        assert login.status_code == 200
        created = client.post(
            "/api/jobs",
            json={"unit": "件", "orderNo": "TEST-ADMIN-API", "remark": "管理员不能建单"},
        )
        assert created.status_code == 403


def test_typesetter_can_create_job(app_db):
    client = client_with("E007")
    try:
        response = client.post(
            "/api/jobs",
            json={"unit": "件", "orderNo": "TEST-TYPE-API", "remark": "排版建单"},
        )
        assert response.status_code == 200
        job = response.json()["job"]
        assert job["line"] == "亚克力"
        assert job["plannedQty"] == 0
        assert job["remark"] == "排版建单"
    finally:
        client.close()


def test_normal_employee_cannot_create_job(app_db):
    client = client_with("E004")
    try:
        response = client.post(
            "/api/jobs",
            json={"unit": "件", "orderNo": "TEST-NORMAL-API", "remark": "普通员工"},
        )
        assert response.status_code == 403
    finally:
        client.close()


def test_admin_can_grant_create_permission(app_db):
    admin = client_with("A001")
    try:
        before = admin.post(
            "/api/jobs",
            json={"unit": "件", "orderNo": "TEST-GRANT-BEFORE", "remark": ""},
        )
        assert before.status_code == 403

        granted = admin.post(
            "/api/admin/employees/E004/create-permission",
            json={"canCreateJob": True},
        )
        assert granted.status_code == 200
        employees = {e["id"]: e for e in granted.json()["employees"]}
        assert employees["E004"]["canCreateJob"] is True
    finally:
        admin.close()

    employee = client_with("E004")
    try:
        allowed = employee.post(
            "/api/jobs",
            json={"unit": "件", "orderNo": "TEST-GRANT-AFTER", "remark": ""},
        )
        assert allowed.status_code == 200
    finally:
        employee.close()


def test_auto_report_endpoint(app_db):
    client = client_with("E007")
    try:
        created = client.post(
            "/api/jobs",
            json={"unit": "m²", "orderNo": "TEST-AUTO-API", "remark": "", "meters": 8.5},
        )
        assert created.status_code == 200
        job_id = created.json()["job"]["id"]
        report = client.post(f"/api/jobs/{job_id}/auto-report")
        assert report.status_code == 200
        record = report.json()["record"]
        assert record["stepNo"] == 1
        assert record["qty"] == 8.5
    finally:
        client.close()


def test_only_admin_can_change_create_permission(app_db):
    typesetter = client_with("E007")
    try:
        response = typesetter.post(
            "/api/admin/employees/E004/create-permission",
            json={"canCreateJob": True},
        )
        assert response.status_code == 403
    finally:
        typesetter.close()
