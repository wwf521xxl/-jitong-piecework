# -*- coding: utf-8 -*-
"""生成/复用本地 HTTPS 证书，供 EXE 启动器和命令行工具共用。"""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def local_ips() -> list[str]:
    ips = {"127.0.0.1"}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ips.add(sock.getsockname()[0])
        sock.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ips)


def _write_key(path: Path, key) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _write_cert(path: Path, cert) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _existing_ips(cert_path: Path) -> set[str]:
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        return {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
    except Exception:
        return set()


def _guide(primary_ip: str, ips: list[str], port: int) -> str:
    ip_text = "、".join(ips)
    return f"""计件通 · 本地 HTTPS 证书
============================================================
服务器 IP：{ip_text}
HTTPS 端口：{port}
访问地址：https://{primary_ip}:{port}

给手机安装：
1. 把 jitong-local-ca.cer（iPhone 也可用 jitong-local-ca.crt）发到手机。
2. iPhone：Safari 打开证书 → 允许下载描述文件 → 设置 → 通用 → VPN与设备管理 → 安装 →
   设置 → 通用 → 关于本机 → 证书信任设置 → 打开对 Jitong Local CA 的完全信任。
3. Android：设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书 → 选择 .cer/.crt 安装。
4. 安装后手机浏览器打开 https://{primary_ip}:{port}，地址栏应有锁。

注意：
- jitong-local-ca.key 和 server.key 是私钥，只留在服务器，不要发给员工。
- 每台手机只需安装一次根证书；之后即使厂里断网，只要连厂内 Wi-Fi，即可扫码报工。
"""


def ensure_certs(cert_dir: Path, port: int = 8443) -> dict:
    """确保证书存在；如果局域网 IP 变了，用原 CA 重签服务端证书。

    这样手机只需安装一次 CA；以后 IP 变化时服务端证书更新，手机不用重装 CA。
    """
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    ca_crt_path = cert_dir / "jitong-local-ca.crt"
    ca_key_path = cert_dir / "jitong-local-ca.key"
    server_crt = cert_dir / "server.crt"
    server_key = cert_dir / "server.key"

    ips = set(local_ips())
    ip_objects = []
    for value in sorted(ips):
        try:
            ip_objects.append(ipaddress.ip_address(value))
        except ValueError:
            pass
    primary_ip = next((str(ip) for ip in ip_objects if str(ip).startswith("192.168.")), None)
    if primary_ip is None:
        primary_ip = next((str(ip) for ip in ip_objects if not ip.is_loopback), "127.0.0.1")

    public = cert_dir / "public"
    public.mkdir(parents=True, exist_ok=True)
    guide = _guide(primary_ip, sorted(str(ip) for ip in ip_objects), port)

    # 已有证书且包含当前 IP：直接复用
    if (
        ca_crt_path.exists()
        and ca_key_path.exists()
        and server_crt.exists()
        and server_key.exists()
        and all(str(ip) in _existing_ips(server_crt) for ip in ip_objects)
    ):
        _write_public(public, ca_crt_path, cert_dir, guide, primary_ip, port)
        return {"primary_ip": primary_ip, "cert": server_crt, "key": server_key, "ca": ca_crt_path, "public": public}

    # 复用 CA，重新签发服务端证书（手机不用重装 CA）
    if ca_crt_path.exists() and ca_key_path.exists():
        ca_cert = x509.load_pem_x509_certificate(ca_crt_path.read_bytes())
        ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Jitong Local CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Jitong Factory"),
        ])
        now = datetime.now(timezone.utc)
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(ca_name)
            .issuer_name(ca_name)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, content_commitment=False, key_encipherment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=True,
                    crl_sign=True, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        _write_key(ca_key_path, ca_key)
        _write_cert(ca_crt_path, ca_cert)
        (cert_dir / "jitong-local-ca.cer").write_bytes(ca_cert.public_bytes(serialization.Encoding.DER))

    now = datetime.now(timezone.utc)
    server_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    san = [x509.DNSName("localhost"), x509.DNSName("jitong.local")]
    san.extend(x509.IPAddress(ip) for ip in ip_objects)
    server_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "jitong-local-server"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Jitong Factory"),
    ])
    server_cert_obj = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_cert.subject)
        .public_key(server_key_obj.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key_obj.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    _write_key(server_key, server_key_obj)
    server_crt.write_bytes(
        server_cert_obj.public_bytes(serialization.Encoding.PEM)
        + ca_cert.public_bytes(serialization.Encoding.PEM)
    )
    _write_public(public, ca_crt_path, cert_dir, guide, primary_ip, port)
    return {"primary_ip": primary_ip, "cert": server_crt, "key": server_key, "ca": ca_crt_path, "public": public}


def _write_public(public: Path, ca_crt_path: Path, cert_dir: Path, guide: str, primary_ip: str, port: int) -> None:
    public.mkdir(parents=True, exist_ok=True)
    (public / "jitong-local-ca.cer").write_bytes((cert_dir / "jitong-local-ca.cer").read_bytes())
    (public / "jitong-local-ca.crt").write_bytes(ca_crt_path.read_bytes())
    (public / "手机安装证书说明.txt").write_text(guide, encoding="utf-8-sig")
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>计件通 · 手机证书安装</title>
<style>body{margin:0;padding:22px;background:#f4f6f9;font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#10233c;line-height:1.75}.card{max-width:520px;margin:0 auto;background:#fff;border-radius:18px;padding:22px;box-shadow:0 10px 30px rgba(16,35,60,.08)}h1{font-size:21px;margin:0 0 4px}.sub{color:#718096;font-size:12px;margin-bottom:14px}h2{font-size:15px;color:#1467e8;margin:18px 0 6px}li,p{font-size:13px}.btn{display:block;text-align:center;background:#1467e8;color:#fff;text-decoration:none;padding:13px;border-radius:11px;font-weight:700;margin:14px 0 8px}.alt{display:block;text-align:center;font-size:12px;color:#1467e8}.warn{background:#fff8ec;border:1px solid #ffe2b8;color:#8a4b00;padding:10px;border-radius:9px;font-size:12px}code{background:#f2f6fb;padding:1px 5px;border-radius:4px}</style>
</head><body><div class="card">
<h1>手机安装计件通证书</h1><div class="sub">只需安装一次；之后连厂内 Wi-Fi 即可扫码。</div>
<div class="warn">请先安装证书，再打开 HTTPS 地址。不要用微信内置浏览器安装，建议 iPhone Safari 或 Android Chrome。</div>
<a class="btn" href="./jitong-local-ca.cer">下载根证书（.cer）</a>
<a class="alt" href="./jitong-local-ca.crt">备用下载（.crt）</a>
<h2>安卓员工版 App（可选）</h2>
<p>如果不想用浏览器，可以下载安卓 APK；安装后只需设置一次服务器 IP。</p>
<a class="btn" href="./jitong-worker.apk">下载安卓 APK</a>
<h2>iPhone / iPad</h2><ol><li>Safari 打开本页，下载证书。</li><li>设置 → 通用 → VPN 与设备管理 → 安装描述文件。</li><li>设置 → 通用 → 关于本机 → 证书信任设置 → 打开“Jitong Local CA”完全信任。</li></ol>
<h2>Android</h2><ol><li>Chrome 打开本页，下载证书。</li><li>设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书。</li><li>选择 jitong-local-ca.cer 安装。</li></ol>
<h2>安装后打开</h2><p><code>https://__IP__:__PORT__</code></p>
<p>手机和服务器电脑必须连同一个 Wi-Fi。</p>
</div></body></html>"""
    (public / "index.html").write_text(html.replace("__IP__", primary_ip).replace("__PORT__", str(port)), encoding="utf-8")
