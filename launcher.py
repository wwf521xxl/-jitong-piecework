# -*- coding: utf-8 -*-
"""计件通免安装 EXE 启动器。

客户电脑不需要安装 Python。双击本 EXE 后：
- 在 EXE 同目录生成 data 和 certs；
- 启动 8443 HTTPS 和 8788 证书下载；
- 自动打开浏览器。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", base_dir())).resolve()
    return base_dir()


class CertHandler(BaseHTTPRequestHandler):
    public_dir: Path = Path(".")

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        mapping = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/jitong-local-ca.cer": ("jitong-local-ca.cer", "application/x-x509-ca-cert"),
            "/jitong-local-ca.crt": ("jitong-local-ca.crt", "application/x-x509-ca-cert"),
            "/手机安装证书说明.txt": ("手机安装证书说明.txt", "text/plain; charset=utf-8"),
            "/jitong-worker.apk": ("jitong-worker.apk", "application/vnd.android.package-archive"),
        }
        item = mapping.get(path)
        if item is None:
            self.send_error(404, "Not Found")
            return
        file_name, content_type = item
        target = self.public_dir / file_name
        if not target.exists():
            self.send_error(404, "Not Found")
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        return


def start_cert_server(public_dir: Path, port: int) -> None:
    if not public_dir.exists():
        return
    CertHandler.public_dir = public_dir
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), CertHandler)
    except OSError:
        return  # 端口已被占用，不影响主服务
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()


def trust_ca(ca_path: Path) -> None:
    if os.name != "nt" or not ca_path.exists():
        return
    try:
        subprocess.run(
            ["certutil", "-user", "-addstore", "-f", "Root", str(ca_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def main() -> None:
    base = base_dir()
    app_dir = bundle_dir() / "app"
    data_dir = Path(os.environ.get("JITONG_DATA_DIR", str(base / "data"))).resolve()
    cert_dir = Path(os.environ.get("JITONG_CERT_DIR", str(base / "certs"))).resolve()
    port = int(os.environ.get("JITONG_PORT", "8443"))
    cert_port = int(os.environ.get("JITONG_CERT_HTTP_PORT", "8788"))

    data_dir.mkdir(parents=True, exist_ok=True)
    cert_dir.mkdir(parents=True, exist_ok=True)

    from server.local_cert import ensure_certs

    certs = ensure_certs(cert_dir, port=port)
    apk = base / "jitong-worker.apk"
    if apk.exists():
        shutil.copy2(apk, certs["public"] / "jitong-worker.apk")
    trust_ca(certs["ca"])
    start_cert_server(certs["public"], cert_port)

    os.environ["JITONG_DATA_DIR"] = str(data_dir)
    os.environ["JITONG_APP_DIR"] = str(app_dir)
    os.environ["JITONG_HOST"] = "0.0.0.0"
    os.environ["JITONG_PORT"] = str(port)
    os.environ["JITONG_SSL_CERT"] = str(certs["cert"])
    os.environ["JITONG_SSL_KEY"] = str(certs["key"])
    os.environ["JITONG_COOKIE_SECURE"] = "1"
    os.environ["JITONG_OPEN_BROWSER"] = "0"
    os.environ.setdefault("JITONG_SHOW_ACCOUNTS", "1")

    print()
    print("=" * 60)
    print("  计件通 · 免安装生产版")
    print("=" * 60)
    print(f"  厂长电脑 : https://127.0.0.1:{port}")
    print(f"  员工手机 : https://{certs['primary_ip']}:{port}")
    print(f"  手机证书 : http://{certs['primary_ip']}:{cert_port}/")
    print(f"  数据目录 : {data_dir}")
    print("=" * 60)
    print("  请保持本窗口开启；关闭窗口即停止服务。")
    print("=" * 60)

    def open_browser() -> None:
        time.sleep(1.5)
        try:
            webbrowser.open(f"https://127.0.0.1:{port}/?v={int(time.time())}")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn

    from server.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        ssl_certfile=str(certs["cert"]),
        ssl_keyfile=str(certs["key"]),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        try:
            input("启动失败，按回车退出...")
        except Exception:
            pass
