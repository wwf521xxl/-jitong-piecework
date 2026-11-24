# -*- coding: utf-8 -*-
"""计件通本地预览服务器（零第三方依赖）。

双击 启动计件通.bat，或在项目目录执行：
    python start.py

默认监听 0.0.0.0:8787：
  - 电脑访问 http://127.0.0.1:8787
  - 手机与电脑连同一 Wi-Fi 后，访问启动时打印的局域网地址
"""

from __future__ import annotations

import http.server
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
PORT = 8787


def get_lan_ip() -> str:
    """获取本机局域网 IPv4；失败时回退到 127.0.0.1。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def is_jitong_running(url: str) -> bool:
    """端口被占用时，判断是否已经是本应用，避免重复启动报错。"""
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            body = response.read(4096).decode("utf-8", errors="ignore")
        return "计件通" in body
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        # 控制台只保留关键信息，避免手机刷新时刷屏
        if args and str(args[0]).startswith(("4", "5")):
            sys.stderr.write("[HTTP] " + (fmt % args) + "\n")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    # Windows 下开启 SO_REUSEADDR 会允许两个进程同时监听同一端口，
    # 这里必须关闭，确保重复启动能被检测到。
    allow_reuse_address = False
    daemon_threads = True


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if not (APP_DIR / "index.html").exists():
        raise SystemExit(f"未找到应用入口：{APP_DIR / 'index.html'}")

    lan_ip = get_lan_ip()
    url_local = f"http://127.0.0.1:{PORT}"
    url_lan = f"http://{lan_ip}:{PORT}"

    print()
    print("=" * 58)
    print("  计件通 · 工厂个人计件统计（手机端 MVP）")
    print("=" * 58)
    print(f"  电脑访问 : {url_local}")
    print(f"  手机访问 : {url_lan}")
    print("  提示     : 手机需与电脑连接同一 Wi-Fi")
    print("  停止服务 : 在此窗口按 Ctrl + C")
    print("=" * 58)
    print()

    try:
        server = ReusableThreadingHTTPServer(("0.0.0.0", PORT), QuietHandler)
    except OSError as exc:
        if is_jitong_running(url_local):
            print(f"检测到计件通已在运行，直接打开 {url_local}")
            webbrowser.open(f"{url_local}/?v={int(time.time())}")
            return
        raise SystemExit(
            f"端口 {PORT} 启动失败：{exc}\n"
            f"可能已有其他程序占用该端口，请关闭后重试。"
        ) from exc

    threading.Timer(1.0, lambda: webbrowser.open(f"{url_local}/?v={int(time.time())}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
