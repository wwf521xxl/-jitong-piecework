# -*- coding: utf-8 -*-
"""测试夹具：每个测试使用独立临时数据库，绝不碰生产 data。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def app_db(tmp_path, monkeypatch):
    monkeypatch.setenv("JITONG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("JITONG_ADMIN_PASSWORD", "AdminTest123")
    monkeypatch.setenv("JITONG_COOKIE_SECURE", "0")
    from server import db

    db.init_db()
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()
