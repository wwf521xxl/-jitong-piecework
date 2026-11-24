# -*- coding: utf-8 -*-
"""为厂内局域网生成一套本地 HTTPS 证书（不依赖公网/域名）。

生成：
  certs/jitong-local-ca.crt     分发给手机的根证书
  certs/jitong-local-ca.cer     iOS/Android 更容易安装的 DER 格式
  certs/server.crt              服务端证书（含 CA 链）
  certs/server.key              服务端私钥（不要外发）
"""

from __future__ import annotations

import argparse
import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "certs"


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


def write_key(path: Path, key) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def write_cert(path: Path, cert) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", action="append", default=[], help="额外的服务器局域网 IP")
    parser.add_argument("--force", action="store_true", help="覆盖已有证书")
    args = parser.parse_args()

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    ca_crt = CERT_DIR / "jitong-local-ca.crt"
    server_crt = CERT_DIR / "server.crt"
    if ca_crt.exists() and server_crt.exists() and not args.force:
        print("证书已存在，跳过生成。需要重新生成请加 --force")
        return

    ips = set(local_ips()) | set(args.ip)
    ip_objects = []
    for value in sorted(ips):
        try:
            ip_objects.append(ipaddress.ip_address(value))
        except ValueError:
            pass

    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Jitong Local CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Jitong Factory"),
    ])
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

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    san = [x509.DNSName("localhost"), x509.DNSName("jitong.local")]
    san.extend(x509.IPAddress(ip) for ip in ip_objects)
    server_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "jitong-local-server"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Jitong Factory"),
    ])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    write_key(CERT_DIR / "jitong-local-ca.key", ca_key)
    write_cert(ca_crt, ca_cert)
    (CERT_DIR / "jitong-local-ca.cer").write_bytes(ca_cert.public_bytes(serialization.Encoding.DER))
    write_key(CERT_DIR / "server.key", server_key)
    # 服务端证书文件包含叶子证书 + CA，方便手机建立完整链
    server_crt.write_bytes(
        server_cert.public_bytes(serialization.Encoding.PEM)
        + ca_cert.public_bytes(serialization.Encoding.PEM)
    )

    ip_text = "、".join(sorted(str(ip) for ip in ip_objects))
    primary_ip = next((str(ip) for ip in ip_objects if str(ip).startswith("192.168.")), None)
    if primary_ip is None:
        primary_ip = next((str(ip) for ip in ip_objects if not ip.is_loopback), "127.0.0.1")
    guide = f"""计件通 · 本地 HTTPS 证书
============================================================
服务器 IP：{ip_text}
HTTPS 端口：8443
访问地址：https://{primary_ip}:8443

给手机安装：
1. 把 jitong-local-ca.cer（iPhone 也可用 jitong-local-ca.crt）发到手机。
2. iPhone：Safari 打开证书 → 允许下载描述文件 → 设置 → 通用 → VPN与设备管理 → 安装 → 
   设置 → 通用 → 关于本机 → 证书信任设置 → 打开对 Jitong Local CA 的完全信任。
3. Android：设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书 → 选择 .cer/.crt 安装。
4. 安装后手机浏览器打开 https://服务器IP:8443，地址栏应有锁。
5. 如果 IP 变了，重新运行：python tools\\make_local_cert.py --force

注意：
- jitong-local-ca.key 和 server.key 是私钥，只留在服务器，不要发给员工。
- 每台手机只需安装一次根证书；之后即使厂里断网，只要连厂内 Wi-Fi，即可扫码报工。
"""
    (CERT_DIR / "手机安装证书说明.txt").write_text(guide, encoding="utf-8-sig")

    # 只公开根证书和说明，绝不把 server.key / ca.key 放进 public
    public = CERT_DIR / "public"
    public.mkdir(parents=True, exist_ok=True)
    (public / "jitong-local-ca.cer").write_bytes((CERT_DIR / "jitong-local-ca.cer").read_bytes())
    (public / "jitong-local-ca.crt").write_bytes((CERT_DIR / "jitong-local-ca.crt").read_bytes())
    (public / "手机安装证书说明.txt").write_text(guide, encoding="utf-8-sig")
    public_html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>计件通 · 手机证书安装</title>
<style>body{margin:0;padding:22px;background:#f4f6f9;font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#10233c;line-height:1.75}.card{max-width:520px;margin:0 auto;background:#fff;border-radius:18px;padding:22px;box-shadow:0 10px 30px rgba(16,35,60,.08)}h1{font-size:21px;margin:0 0 4px}.sub{color:#718096;font-size:12px;margin-bottom:14px}h2{font-size:15px;color:#1467e8;margin:18px 0 6px}li,p{font-size:13px}.btn{display:block;text-align:center;background:#1467e8;color:#fff;text-decoration:none;padding:13px;border-radius:11px;font-weight:700;margin:14px 0 8px}.alt{display:block;text-align:center;font-size:12px;color:#1467e8}.warn{background:#fff8ec;border:1px solid #ffe2b8;color:#8a4b00;padding:10px;border-radius:9px;font-size:12px}code{background:#f2f6fb;padding:1px 5px;border-radius:4px}</style>
</head><body><div class="card">
<h1>手机安装计件通证书</h1><div class="sub">只需安装一次；之后连厂内 Wi-Fi 即可扫码。</div>
<div class="warn">请先安装证书，再打开 HTTPS 地址。不要用微信内置浏览器安装，建议 iPhone Safari 或 Android Chrome。</div>
<a class="btn" href="./jitong-local-ca.cer">下载根证书（.cer）</a>
<a class="alt" href="./jitong-local-ca.crt">备用下载（.crt）</a>
<h2>iPhone / iPad</h2><ol><li>Safari 打开本页，下载证书。</li><li>设置 → 通用 → VPN 与设备管理 → 安装描述文件。</li><li>设置 → 通用 → 关于本机 → 证书信任设置 → 打开“Jitong Local CA”完全信任。</li></ol>
<h2>Android</h2><ol><li>Chrome 打开本页，下载证书。</li><li>设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书。</li><li>选择 jitong-local-ca.cer 安装。</li></ol>
<h2>安装后打开</h2><p><code>https://__IP__:8443</code></p>
<p>手机和服务器电脑必须连同一个 Wi-Fi。</p>
</div></body></html>"""
    (public / "index.html").write_text(public_html.replace("__IP__", primary_ip), encoding="utf-8")
    print(f"证书已生成：{CERT_DIR}")
    print(f"服务器 IP：{ip_text}")
    print(f"访问：https://{primary_ip}:8443")
    print("请安装 certs/jitong-local-ca.cer 到手机，并信任它。")


if __name__ == "__main__":
    main()
