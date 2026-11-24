# -*- coding: utf-8 -*-
"""生成苹果手机客户操作卡。"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(r"D:\工厂个人计件软件\dist\客户苹果手机操作卡.docx")
FONT = "Microsoft YaHei"
INK = RGBColor(0x10, 0x23, 0x3C)
MUTED = RGBColor(0x5B, 0x6B, 0x7C)
BLUE = RGBColor(0x14, 0x67, 0xE8)
GREEN = RGBColor(0x06, 0x76, 0x47)
RED = RGBColor(0xB4, 0x23, 0x18)
SERVER_IP = "192.168.116.19"


def set_run_font(run, size=10.5, bold=False, color=INK):
    run.font.name = FONT
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color


def shade(cell, color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def cell_text(cell, text, size=10.5, bold=False, color=INK, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_run_font(run, size, bold, color)


def heading(doc, text, number=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    if number:
        r = p.add_run(number + "  ")
        set_run_font(r, 11, True, BLUE)
    r = p.add_run(text)
    set_run_font(r, 13, True, INK)


def body(doc, text, size=10.5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    r = p.add_run(text)
    set_run_font(r, size, False, INK)


def bullet(doc, text, color=INK):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    set_run_font(r, 10.0, False, color)


def main():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.4)
    section.left_margin = Cm(1.7)
    section.right_margin = Cm(1.7)

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade(cell, "10233C")
    cell_text(cell, "计件通 · 苹果手机操作卡", 19, True, RGBColor(0xFF, 0xFF, 0xFF))
    p = cell.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Safari 网页版 · 不需要安装 APK")
    set_run_font(r, 10, False, RGBColor(0xC9, 0xD6, 0xE6))

    body(doc, "本卡适用于 iPhone / iPad。安卓手机请使用安卓操作卡。")

    info = doc.add_table(rows=3, cols=2)
    info.style = "Table Grid"
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows = [
        ("服务器 IP", SERVER_IP),
        ("证书地址", f"http://{SERVER_IP}:8788/"),
        ("报工地址", f"https://{SERVER_IP}:8443/"),
    ]
    for i, (k, v) in enumerate(rows):
        cell_text(info.cell(i, 0), k, 10.5, True, INK)
        shade(info.cell(i, 0), "EEF4FF")
        cell_text(info.cell(i, 1), v, 10.5, False, INK)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    r = p.add_run("如果服务器启动窗口显示的 IP 不是这个，以启动窗口为准；手机 IP 应在 192.168.116.x 网段。")
    set_run_font(r, 8.5, False, MUTED)

    heading(doc, "连接厂内 Wi-Fi", "01")
    body(doc, "打开：设置 → 无线局域网，连接：")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run("TP-LINK_B9B4车间")
    set_run_font(r, 14, True, BLUE)

    body(doc, "连接后，点该 Wi-Fi 右侧的“i”，确认：")
    bullet(doc, "IP 地址是 192.168.116.x（当前手机示例：192.168.116.59）")
    bullet(doc, "关闭“无线局域网助理 / 连接助理”")
    bullet(doc, "如果打不开地址，关闭“限制 IP 地址跟踪 / 私人中继”后重试")

    heading(doc, "安装证书（只装一次）", "02")
    body(doc, "必须用 Safari，不要用微信或 Chrome。")
    steps = [
        "Safari 打开证书地址。",
        "点“下载根证书”。",
        "提示“此网站正尝试下载配置描述文件”时，点“允许”。",
        "打开：设置 → 通用 → VPN 与设备管理。",
        "点 Jitong Local CA → 安装 → 输入手机密码 → 安装。",
        "打开：设置 → 通用 → 关于本机 → 证书信任设置。",
        "打开 Jitong Local CA 的完全信任。",
    ]
    for idx, text in enumerate(steps, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(f"{idx}. ")
        set_run_font(r, 10.5, True, BLUE)
        r = p.add_run(text)
        set_run_font(r, 10.2)

    heading(doc, "打开报工地址", "03")
    p = doc.add_paragraph()
    r = p.add_run(f"https://{SERVER_IP}:8443/")
    set_run_font(r, 16, True, BLUE)
    body(doc, "Safari 地址栏出现锁，说明证书成功。")
    body(doc, "输入工号和 PIN 登录，允许 Safari 使用相机。")

    heading(doc, "添加到桌面，老人只需点图标", "04")
    body(doc, "Safari 底部点“分享”按钮 → 添加到主屏幕 → 名称写“计件通” → 添加。")
    body(doc, "以后老人只需要：点桌面“计件通” → 点“扫码报工” → 对准二维码 → 报工成功。")

    tip = doc.add_table(rows=1, cols=1)
    tip.style = "Table Grid"
    tip.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = tip.cell(0, 0)
    shade(c, "E8F8F0")
    cell_text(c, "苹果口诀：连 Wi-Fi → Safari 装证书 → 开 HTTPS → 登录 → 添加到桌面 → 扫码", 10.5, True, GREEN)

    heading(doc, "常见问题", "05")
    issues = [
        ("Safari 打不开网页", "检查同一 Wi-Fi、服务器窗口、服务器 IP；关闭“连接助理”和私人中继。"),
        ("提示“不安全”", "证书没安装或没有完全信任，重新做第 02 步。"),
        ("相机打不开", "必须用 https://；证书完全信任；设置 → Safari → 相机 → 允许。"),
        ("没有“添加到主屏幕”", "必须用 Safari 打开，微信/Chrome 没有这个菜单。"),
        ("扫码没反应", "用首页“扫码报工”，不要用微信扫一扫；也可以手动输入订单号。"),
        ("没有可报工序", "技能不包含当前工序、上一道没报，或订单已全部报完。"),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_text(table.cell(0, 0), "现象", 10, True, RGBColor(0xFF, 0xFF, 0xFF))
    cell_text(table.cell(0, 1), "处理", 10, True, RGBColor(0xFF, 0xFF, 0xFF))
    shade(table.cell(0, 0), "10233C")
    shade(table.cell(0, 1), "10233C")
    for symptom, fix in issues:
        row = table.add_row()
        cell_text(row.cells[0], symptom, 9.2, True, INK)
        cell_text(row.cells[1], fix, 9.2, False, INK)

    heading(doc, "重要说明", "06")
    body(doc, "苹果手机不能安装安卓 APK，也不需要使用 App Store。")
    body(doc, "服务器端仍然运行 Windows 的“计件通服务器.exe”，手机只通过 Safari 访问。")
    body(doc, "证书只安装一次；以后每天直接点桌面图标。")
    body(doc, "如果服务器 IP 变了，需要重新安装一次证书并重新添加到桌面。")

    heading(doc, "交付确认", "07")
    check = doc.add_table(rows=2, cols=2)
    check.style = "Table Grid"
    check.alignment = WD_TABLE_ALIGNMENT.CENTER
    items = [
        "□ 已连接厂内 Wi-Fi",
        "□ 已关闭连接助理",
        "□ 证书已安装并完全信任",
        "□ 已添加到主屏幕并扫码成功",
    ]
    for i, text in enumerate(items):
        cell_text(check.cell(i // 2, i % 2), text, 9.5)

    sign = doc.add_table(rows=1, cols=2)
    sign.style = "Table Grid"
    sign.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_text(sign.cell(0, 0), "客户签字：________________", 10.5)
    cell_text(sign.cell(0, 1), "日期：______年__月__日", 10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(14)
    r = p.add_run("技术支持：____________________")
    set_run_font(r, 9, False, MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
