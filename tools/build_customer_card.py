# -*- coding: utf-8 -*-
"""生成客户手机扫码操作卡 DOCX。"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(r"D:\工厂个人计件软件\dist\客户手机操作卡.docx")
FONT = "Microsoft YaHei"
INK = RGBColor(0x10, 0x23, 0x3C)
MUTED = RGBColor(0x5B, 0x6B, 0x7C)
BLUE = RGBColor(0x14, 0x67, 0xE8)
GREEN = RGBColor(0x06, 0x76, 0x47)
RED = RGBColor(0xB4, 0x23, 0x18)


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
    p.paragraph_format.line_spacing = 1.35
    r = p.add_run(text)
    set_run_font(r, size, False, INK)


def bullet(doc, text, color=INK):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    set_run_font(r, 10.2, False, color)


def main():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.4)
    section.left_margin = Cm(1.7)
    section.right_margin = Cm(1.7)
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)

    # 标题条
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    cell = table.cell(0, 0)
    shade(cell, "10233C")
    cell_text(cell, "计件通 · 客户手机操作卡", 20, True, RGBColor(0xFF, 0xFF, 0xFF))
    p = cell.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("手机扫码报工 · 一看就会")
    set_run_font(r, 10, False, RGBColor(0xC9, 0xD6, 0xE6))

    body(doc, "请先填写服务器信息（由交付人员填写）：")
    info = doc.add_table(rows=3, cols=2)
    info.style = "Table Grid"
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows = [
        ("服务器 IP", "____________________________"),
        ("管理端地址", "https://________________:8443"),
        ("手机证书地址", "http://________________:8788/"),
    ]
    for i, (k, v) in enumerate(rows):
        cell_text(info.cell(i, 0), k, 10.5, True, INK)
        shade(info.cell(i, 0), "EEF4FF")
        cell_text(info.cell(i, 1), v, 10.5, False, MUTED)

    heading(doc, "第一次使用：先装证书", "01")
    body(doc, "手机必须和服务器电脑连接同一个 Wi-Fi。每台手机只安装一次证书。")
    cert = doc.add_table(rows=1, cols=2)
    cert.style = "Table Grid"
    cert.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_text(cert.cell(0, 0), "iPhone / iPad", 11, True, BLUE)
    cell_text(cert.cell(0, 1), "Android", 11, True, BLUE)
    shade(cert.cell(0, 0), "EAF2FF")
    shade(cert.cell(0, 1), "FFF4E5")

    iphone = cert.cell(1, 0) if len(cert.rows) > 1 else None
    # 追加一行步骤
    row = cert.add_row()
    cell_text(row.cells[0], "1. Safari 打开证书地址\n2. 下载根证书\n3. 设置 → 通用 → VPN 与设备管理 → 安装\n4. 设置 → 通用 → 关于本机 → 证书信任设置 → 完全信任", 9.5)
    cell_text(row.cells[1], "1. Chrome 打开证书地址\n2. 下载根证书\n3. 设置 → 安全 → 加密与凭据\n4. 安装证书 → CA 证书", 9.5)

    heading(doc, "每天使用：扫码自动报工", "02")
    body(doc, "打开手机上的计件通报工地址，用工号 + PIN 登录。")
    steps = [
        "点首页「扫码报工」。",
        "把流转卡二维码放进扫描框。",
        "系统自动判断你的工序，按订单米数/数量直接报工。",
        "看到「报工成功」即可，不需要输入数量，也不需要点确认。",
    ]
    for idx, text in enumerate(steps, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"{idx}. ")
        set_run_font(r, 11, True, BLUE)
        r = p.add_run(text)
        set_run_font(r, 10.3)

    # 口诀框
    tip = doc.add_table(rows=1, cols=1)
    tip.style = "Table Grid"
    tip.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = tip.cell(0, 0)
    shade(c, "E8F8F0")
    cell_text(c, "操作口诀：先装证书 → 登录 → 点扫码 → 对准二维码 → 看到报工成功", 11, True, GREEN)

    heading(doc, "地址千万不要写错", "03")
    body(doc, "正确格式：")
    bullet(doc, "证书页：http://服务器IP:8788/   （http，端口 8788）")
    bullet(doc, "报工页：https://服务器IP:8443/  （https，端口 8443）")
    body(doc, "常见错误：", 10.5)
    bullet(doc, "不要在百度搜索框里输入网址，要在 Safari/Chrome 顶部地址栏输入。", RED)
    bullet(doc, "不要写“服务器IP”四个字，要换成真实数字 IP。", RED)
    bullet(doc, "端口是 8443，不是 8433。", RED)
    bullet(doc, "不要漏掉 https:// 里的冒号。", RED)

    doc.add_page_break()
    heading(doc, "常见提示", "04")
    issues = [
        ("Safari 打不开网页 / 找不到服务器", "检查手机和服务器是否同一个 Wi-Fi；服务器黑色窗口是否还开着；IP 是否写对。"),
        ("提示证书不安全", "证书没有安装或没有完全信任，重新安装根证书。"),
        ("没有可自动报工的工序", "你的技能不包含当前工序，或上一道工序还没报，或订单已经全部报完。"),
        ("二维码扫不出来", "用计件通首页的「扫码报工」，不要用微信扫一扫；也可以手动输入订单号。"),
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
        cell_text(row.cells[0], symptom, 9.3, True, INK)
        cell_text(row.cells[1], fix, 9.3, False, INK)

    heading(doc, "建单说明", "05")
    body(doc, "建单由排版人员在手机端完成：王坚、张知亮、胡汝奇、喻宏伟、朱宗耀。")
    body(doc, "新建订单填写：单位、米数、订单号、备注。米数会作为员工扫码后的自动报工数量。")
    body(doc, "管理员不能建单，只能管理订单、审批和查看报表。")

    heading(doc, "交付确认", "06")
    check = doc.add_table(rows=2, cols=2)
    check.style = "Table Grid"
    check.alignment = WD_TABLE_ALIGNMENT.CENTER
    items = [
        "□ 服务器已启动，黑色窗口保持开启",
        "□ 管理员账号已登录并修改密码",
        "□ 手机证书已安装并信任",
        "□ 已扫码成功报工一笔",
    ]
    for i, text in enumerate(items):
        cell_text(check.cell(i // 2, i % 2), text, 9.5)

    sign = doc.add_table(rows=1, cols=2)
    sign.style = "Table Grid"
    sign.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_text(sign.cell(0, 0), "客户签字：________________", 10.5, False, INK)
    cell_text(sign.cell(0, 1), "日期：______年__月__日", 10.5, False, INK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(14)
    r = p.add_run("服务端要求：黑色窗口不能关 · 电脑不休眠 · 每天备份 data 文件夹")
    set_run_font(r, 9, False, MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("技术支持：____________________")
    set_run_font(r, 9, False, MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
