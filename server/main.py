# -*- coding: utf-8 -*-
"""计件通生产版 API 与静态前端服务。"""

from __future__ import annotations

import csv
import ipaddress
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, security, service

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = Path(os.environ.get("JITONG_APP_DIR", str(ROOT / "app"))).resolve()
COOKIE_SECURE = os.environ.get("JITONG_COOKIE_SECURE", "0") in ("1", "true", "yes")
SHOW_INITIAL_ACCOUNTS = os.environ.get("JITONG_SHOW_ACCOUNTS", "1") in ("1", "true", "yes")
SSL_CERT = os.environ.get("JITONG_SSL_CERT", "").strip()
SSL_KEY = os.environ.get("JITONG_SSL_KEY", "").strip()
SCHEME = "https" if SSL_CERT else "http"
HOST = os.environ.get("JITONG_HOST", "0.0.0.0")
PORT = int(os.environ.get("JITONG_PORT", "8787"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="计件通生产版",
    version="2.7.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


def get_db():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def _token(request: Request) -> str:
    token = request.cookies.get(security.COOKIE_NAME) or ""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    return token


def current_user(request: Request, conn=Depends(get_db)):
    token = _token(request)
    row = security.session_user(conn, token)
    if row is None:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "请先登录"})
    return row


def require_admin(user=Depends(current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "需要厂长权限"})
    return user


class LoginBody(BaseModel):
    account: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=1, max_length=128)


class RecordBody(BaseModel):
    jobId: str
    stepNo: int
    qty: float
    unit: str | None = None
    note: str | None = None
    idempotencyKey: str | None = None
    source: str | None = "scan"
    deviceId: str | None = None
    photo: str | None = None
    forceDuplicate: bool = False


class CorrectionBody(BaseModel):
    reason: str = "其他"
    note: str | None = None


class RejectBody(BaseModel):
    reason: str = "厂长驳回"


class JobBody(BaseModel):
    unit: str
    line: str = ""
    orderNo: str = ""
    remark: str = ""
    meters: float = 0
    routeKey: str = ""


class EditJobBody(BaseModel):
    orderNo: str = ""
    remark: str = ""
    meters: float | None = None


class AutoReportBody(BaseModel):
    stepNo: int | None = None


class GroupCloseBody(BaseModel):
    reason: str = "手动结束合报"


class VoidJobBody(BaseModel):
    reason: str = "厂长作废"


class ClearDataBody(BaseModel):
    password: str
    confirm: str


class PasswordBody(BaseModel):
    old: str
    new: str


class CreatePermissionBody(BaseModel):
    canCreateJob: bool


class ProcessSkillsBody(BaseModel):
    processes: list[str] = []


class NewEmployeeBody(BaseModel):
    name: str
    employeeNo: int
    pin: str
    role: str = "员工"
    canCreateJob: bool = False
    processSkills: list[str] = []


class EditEmployeeBody(BaseModel):
    name: str
    role: str | None = None


class SkillBody(BaseModel):
    name: str
    displayName: str | None = None


class RouteBody(BaseModel):
    line: str
    name: str
    steps: list[str] = []


@app.get("/api/health")
def health():
    return {"ok": True, "service": "jitong", "version": "2.7.0"}


@app.post("/api/login")
def login(body: LoginBody, response: Response, conn=Depends(get_db)):
    user = security.authenticate(conn, body.account, body.pin)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "bad_credentials", "message": "工号或密码不正确"})
    token = security.create_session(conn, user["id"])
    response.set_cookie(
        security.COOKIE_NAME,
        token,
        max_age=security.SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )
    data = service.bootstrap(conn, user)
    data["token"] = token
    return data


@app.post("/api/logout")
def logout(request: Request, response: Response, conn=Depends(get_db)):
    security.destroy_session(conn, _token(request))
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/bootstrap")
def bootstrap(conn=Depends(get_db), user=Depends(current_user)):
    return service.bootstrap(conn, user)


@app.get("/api/me")
def me(conn=Depends(get_db), user=Depends(current_user)):
    return service.user_payload(conn, user)


@app.post("/api/records")
def create_record(body: RecordBody, conn=Depends(get_db), user=Depends(current_user)):
    record, data = service.create_record(conn, user, body.model_dump())
    data["record"] = record
    return data


@app.get("/api/jobs/{job_id}/auto-report/options")
def auto_report_options(job_id: str, conn=Depends(get_db), user=Depends(current_user)):
    return service.auto_report_options(conn, user, job_id)


@app.post("/api/admin/jobs/{job_id}/groups/{step_no}/close")
def close_group(
    job_id: str,
    step_no: int,
    body: GroupCloseBody,
    conn=Depends(get_db),
    user=Depends(current_user),
):
    job, data = service.close_group(conn, user, job_id, step_no, body.reason)
    data["job"] = job
    return data


@app.post("/api/admin/jobs/{job_id}/complete")
def complete_job(job_id: str, conn=Depends(get_db), user=Depends(current_user)):
    job, data = service.complete_job(conn, user, job_id)
    data["job"] = job
    return data


@app.post("/api/admin/jobs/{job_id}/groups/{step_no}/members/{employee_id}/remove")
def remove_group_member(
    job_id: str,
    step_no: int,
    employee_id: str,
    conn=Depends(get_db),
    user=Depends(current_user),
):
    return service.remove_group_member(conn, user, job_id, step_no, employee_id)


@app.post("/api/jobs/{job_id}/auto-report")
def auto_report(
    job_id: str,
    body: AutoReportBody | None = None,
    conn=Depends(get_db),
    user=Depends(current_user),
):
    step_no = body.stepNo if body is not None else None
    record, data = service.auto_report(conn, user, job_id, step_no)
    data["record"] = record
    return data


@app.post("/api/records/{record_id}/corrections")
def request_correction(record_id: str, body: CorrectionBody, conn=Depends(get_db), user=Depends(current_user)):
    return service.request_correction(conn, user, record_id, body.reason, body.note or "")


@app.post("/api/admin/records/{record_id}/approve")
def approve_record(record_id: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.approve_record(conn, admin, record_id)


@app.post("/api/admin/records/{record_id}/reject")
def reject_record(record_id: str, body: RejectBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.reject_record(conn, admin, record_id, body.reason)


@app.post("/api/admin/corrections/{correction_id}/approve")
def approve_correction(correction_id: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.decide_correction(conn, admin, correction_id, True)


@app.post("/api/admin/corrections/{correction_id}/reject")
def reject_correction(correction_id: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.decide_correction(conn, admin, correction_id, False)


def require_job_creator(user=Depends(current_user)):
    if not service.can_create_job(user):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "只有排版人员可以新建订单"})
    return user


@app.post("/api/jobs")
@app.post("/api/admin/jobs")
def create_job(body: JobBody, conn=Depends(get_db), user=Depends(require_job_creator)):
    job, data = service.create_job(conn, user, body.model_dump())
    data["job"] = job
    return data


@app.patch("/api/admin/jobs/{job_id}")
def edit_job(job_id: str, body: EditJobBody, conn=Depends(get_db), admin=Depends(require_admin)):
    job, data = service.edit_job(conn, admin, job_id, body.model_dump())
    data["job"] = job
    return data


@app.post("/api/admin/jobs/{job_id}/void")
def void_job(job_id: str, body: VoidJobBody, conn=Depends(get_db), admin=Depends(require_admin)):
    job, data = service.void_job(conn, admin, job_id, body.reason)
    data["job"] = job
    return data


@app.post("/api/admin/clear-data")
def clear_data(body: ClearDataBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.clear_production_data(conn, admin, body.password, body.confirm)


@app.post("/api/admin/skills")
def add_skill(body: SkillBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.add_skill(conn, admin, body.name)


@app.patch("/api/admin/skills/{name}")
def rename_skill(name: str, body: SkillBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.rename_skill(conn, admin, name, body.displayName or body.name)


@app.delete("/api/admin/skills/{name}")
def delete_skill(name: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.delete_skill(conn, admin, name)


@app.post("/api/admin/routes")
def add_route(body: RouteBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.save_route(conn, admin, None, body.model_dump())


@app.patch("/api/admin/routes/{route_key}")
def edit_route(route_key: str, body: RouteBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.save_route(conn, admin, route_key, body.model_dump())


@app.delete("/api/admin/routes/{route_key}")
def delete_route(route_key: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.delete_route(conn, admin, route_key)


@app.post("/api/admin/employees")
def add_employee(body: NewEmployeeBody, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.add_employee(conn, admin, body.model_dump())


@app.patch("/api/admin/employees/{employee_id}")
def update_employee(
    employee_id: str,
    body: EditEmployeeBody,
    conn=Depends(get_db),
    admin=Depends(require_admin),
):
    return service.update_employee(conn, admin, employee_id, body.model_dump())


@app.post("/api/admin/employees/{employee_id}/deactivate")
def deactivate_employee(employee_id: str, conn=Depends(get_db), admin=Depends(require_admin)):
    return service.deactivate_employee(conn, admin, employee_id)


@app.put("/api/admin/employees/{employee_id}/process-skills")
def set_process_skills(
    employee_id: str,
    body: ProcessSkillsBody,
    conn=Depends(get_db),
    admin=Depends(require_admin),
):
    return service.set_process_skills(conn, admin, employee_id, body.processes)


@app.post("/api/admin/employees/{employee_id}/reset-pin")
def reset_pin(employee_id: str, conn=Depends(get_db), admin=Depends(require_admin)):
    pin = service.reset_pin(conn, admin, employee_id)
    return {"employeeId": employee_id, "pin": pin}


@app.post("/api/admin/employees/{employee_id}/create-permission")
def set_create_permission(
    employee_id: str,
    body: CreatePermissionBody,
    conn=Depends(get_db),
    admin=Depends(require_admin),
):
    return service.set_create_permission(conn, admin, employee_id, body.canCreateJob)


@app.post("/api/change-password")
def change_password(body: PasswordBody, conn=Depends(get_db), user=Depends(current_user)):
    service.change_password(conn, user, body.old, body.new)
    return {"ok": True}


@app.get("/api/photos/{filename}")
def photo(filename: str, user=Depends(current_user)):
    safe = Path(filename).name
    if safe != filename:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "照片不存在"})
    path = db.data_dir() / "photos" / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "照片不存在"})
    return FileResponse(path)


@app.get("/api/initial-accounts")
def initial_accounts(request: Request):
    """仅内网首次部署使用：读取生成的初始账号文件。

    正式公网部署请设置 JITONG_SHOW_ACCOUNTS=0，或删除初始密码文件。
    """
    if not SHOW_INITIAL_ACCOUNTS:
        raise HTTPException(status_code=404, detail={"code": "disabled", "message": "账号显示未开启"})
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    host = forwarded or (request.client.host if request.client else "")
    try:
        ip = ipaddress.ip_address(host)
        if not (ip.is_private or ip.is_loopback):
            raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "仅限内网查看"})
    except ValueError:
        # 测试客户端或未知地址，放行由 SHOW_INITIAL_ACCOUNTS 控制
        pass

    employees = []
    csv_path = db.data_dir() / "员工初始账号.csv"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                employees.append({
                    "account": row.get("工号", ""),
                    "name": row.get("姓名", ""),
                    "role": row.get("岗位", ""),
                    "pin": row.get("初始PIN", ""),
                })

    admin = None
    admin_path = db.data_dir() / "管理员初始密码.txt"
    if admin_path.exists():
        text = admin_path.read_text(encoding="utf-8-sig")
        password = ""
        for line in text.splitlines():
            if line.startswith("密码："):
                password = line.split("：", 1)[1].strip()
                break
        admin = {"account": "admin", "name": "李厂长", "role": "厂长 · 管理员", "pin": password}

    return {"admin": admin, "employees": employees}


@app.get("/api/audit")
def audit_list(limit: int = 100, conn=Depends(get_db), admin=Depends(require_admin)):
    limit = max(1, min(limit, 500))
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def _index_html() -> str:
    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace(
        "<head>",
        "<head>\n  <script>window.JITONG_MODE = 'server';</script>",
        1,
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index():
    return HTMLResponse(_index_html(), headers={"Cache-Control": "no-store, max-age=0"})


# 静态资源必须放在 API 和首页路由之后
app.mount("/", StaticFiles(directory=str(APP_DIR), html=True), name="static")


def _already_running() -> bool:
    url = f"{SCHEME}://127.0.0.1:{PORT}/api/health"
    context = ssl._create_unverified_context() if SCHEME == "https" else None
    try:
        with urllib.request.urlopen(url, timeout=1.5, context=context) as response:
            body = response.read(1024).decode("utf-8", errors="ignore")
        return '"service": "jitong"' in body or '"service":"jitong"' in body
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main() -> None:
    print()
    print("=" * 58)
    print("  计件通 · 生产版")
    print("=" * 58)
    print(f"  管理端 / 员工端 : {SCHEME}://127.0.0.1:{PORT}")
    print(f"  数据目录        : {db.data_dir()}")
    print("  首次启动请查看 data\\员工初始账号.csv 和 管理员初始密码.txt")
    print("=" * 58)

    if _already_running():
        print(f"检测到生产版已在运行，直接打开 {SCHEME}://127.0.0.1:{PORT}")
        webbrowser.open(f"{SCHEME}://127.0.0.1:{PORT}/?v={int(time.time())}")
        return

    if SSL_CERT:
        if not Path(SSL_CERT).exists() or not Path(SSL_KEY).exists():
            raise SystemExit(f"HTTPS 证书不存在：{SSL_CERT} / {SSL_KEY}\n请先执行 python tools\\make_local_cert.py")

    if os.name == "nt" and os.environ.get("JITONG_OPEN_BROWSER", "1") != "0":
        threading.Timer(
            1.2,
            lambda: webbrowser.open(f"{SCHEME}://127.0.0.1:{PORT}/?v={int(time.time())}"),
        ).start()

    uvicorn.run(
        "server.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        ssl_certfile=SSL_CERT or None,
        ssl_keyfile=SSL_KEY or None,
    )


if __name__ == "__main__":
    main()
