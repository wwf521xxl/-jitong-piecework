# -*- coding: utf-8 -*-
"""生成《工厂个人计件软件_手机端设计方案.docx》。"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(r"D:\工厂个人计件软件")
DOCS = ROOT / "docs"
DIAG = DOCS / "diagrams"
OUT = DOCS / "工厂个人计件软件_手机端设计方案.docx"

NAVY = "0B1F33"
INK = "10233C"
BLUE = "1467E8"
AMBER = "B25A00"
GREEN = "067647"
RED = "B42318"
MUTED = "718096"
LINE = "E2E9F1"
SOFT_BLUE = "EAF2FF"
SOFT_GREEN = "E8F8F0"
SOFT_AMBER = "FFF4E5"
SOFT_RED = "FFF0F0"
SOFT_GRAY = "F4F6F9"
FONT_CN = "微软雅黑"
FONT_BODY = "宋体"


# ------------------------------------------------------------------
# 基础工具
# ------------------------------------------------------------------
def set_run_font(run, name=FONT_CN, size=None, bold=None, color=None, italic=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return run


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_margins(cell, top=80, start=110, bottom=80, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=LINE, size=4):
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
        borders.append(element)
    tbl_pr.append(borders)


def remove_table_borders(table):
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "nil")
        element.set(qn("w:sz"), "0")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "auto")
        borders.append(element)
    tbl_pr.append(borders)


def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("start", "top", "end", "bottom", "left", "right"):
        if edge in kwargs:
            edge_data = kwargs.get(edge)
            tag = f"w:{edge}"
            element = tc_borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tc_borders.append(element)
            for key in ["sz", "val", "color", "space"]:
                if key in edge_data:
                    element.set(qn(f"w:{key}"), str(edge_data[key]))


def set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(text)
    run._r.append(fld_end)
    set_run_font(run, FONT_CN, 8.5, color=MUTED)


def add_total_pages(paragraph):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "NUMPAGES"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(text)
    run._r.append(fld_end)
    set_run_font(run, FONT_CN, 8.5, color=MUTED)


def add_bottom_border(paragraph, color=BLUE, size=10, space=4):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


# ------------------------------------------------------------------
# 文档级样式
# ------------------------------------------------------------------
def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONT_BODY
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.55
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.space_before = Pt(0)

    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT_CN
    h1._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h1.font.size = Pt(18)
    h1.font.bold = True
    h1.font.color.rgb = RGBColor.from_string(INK)
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(8)
    h1.paragraph_format.keep_with_next = True

    h2 = doc.styles["Heading 2"]
    h2.font.name = FONT_CN
    h2._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h2.font.size = Pt(13.5)
    h2.font.bold = True
    h2.font.color.rgb = RGBColor.from_string(BLUE)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)
    h2.paragraph_format.keep_with_next = True

    h3 = doc.styles["Heading 3"]
    h3.font.name = FONT_CN
    h3._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h3.font.size = Pt(11.5)
    h3.font.bold = True
    h3.font.color.rgb = RGBColor.from_string(INK)
    h3.paragraph_format.space_before = Pt(9)
    h3.paragraph_format.space_after = Pt(3)
    h3.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number"):
        style = doc.styles[name]
        style.font.name = FONT_BODY
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
        style.font.size = Pt(10.5)
        style.paragraph_format.line_spacing = 1.45
        style.paragraph_format.space_after = Pt(2)


def setup_page(doc):
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(0.9)
    section.different_first_page_header_footer = True

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r1 = hp.add_run("计件通 · 工厂个人计件统计    |    产品与系统设计方案 · v1.0")
    set_run_font(r1, FONT_CN, 8, color=MUTED)
    add_bottom_border(hp, LINE, 4, 3)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("第 ")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)
    add_page_number(fp)
    r = fp.add_run(" 页 / 共 ")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)
    add_total_pages(fp)
    r = fp.add_run(" 页")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)


# ------------------------------------------------------------------
# 组件
# ------------------------------------------------------------------
def h1(doc, text, page_break=False):
    p = doc.add_heading(text, level=1)
    if page_break:
        p.paragraph_format.page_break_before = True
    add_bottom_border(p, BLUE, 8, 6)
    return p


def h2(doc, text):
    return doc.add_heading(text, level=2)


def h3(doc, text):
    return doc.add_heading(text, level=3)


def para(doc, text="", bold_lead=None, size=10.5, color=INK, align=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if bold_lead:
        r = p.add_run(bold_lead)
        set_run_font(r, FONT_BODY, size, bold=True, color=color)
    r = p.add_run(text)
    set_run_font(r, FONT_BODY, size, color=color)
    return p


def bullet(doc, text, bold_lead=None, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    if bold_lead:
        r = p.add_run(bold_lead)
        set_run_font(r, FONT_BODY, 10.5, bold=True, color=INK)
    r = p.add_run(text)
    set_run_font(r, FONT_BODY, 10.5, color=INK)
    p.paragraph_format.space_after = Pt(2)
    return p


def numbered(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Number")
    if bold_lead:
        r = p.add_run(bold_lead)
        set_run_font(r, FONT_BODY, 10.5, bold=True, color=INK)
    r = p.add_run(text)
    set_run_font(r, FONT_BODY, 10.5, color=INK)
    p.paragraph_format.space_after = Pt(2)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(9)
    r = p.add_run(text)
    set_run_font(r, FONT_CN, 8.5, color=MUTED)
    return p


def add_image(doc, path, width_cm, cap=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    if cap:
        caption(doc, cap)


def add_table(doc, headers, rows, widths, font_size=8.3, header_fill=NAVY,
              zebra=True, first_col_bold=False, cap=None, align_center=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    hdr = table.rows[0]
    set_repeat_header(hdr)
    for idx, text in enumerate(headers):
        cell = hdr.cells[idx]
        cell.width = Cm(widths[idx])
        shade_cell(cell, header_fill)
        set_cell_margins(cell, 85, 90, 85, 90)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(str(text))
        set_run_font(r, FONT_CN, font_size, bold=True, color="FFFFFF")

    for ridx, row_data in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for cidx, value in enumerate(row_data):
            cell = row.cells[cidx]
            cell.width = Cm(widths[cidx])
            set_cell_margins(cell, 70, 90, 70, 90)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if zebra and ridx % 2 == 1:
                shade_cell(cell, "F8FAFC")
            p = cell.paragraphs[0]
            if align_center and cidx in align_center:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(value))
            set_run_font(r, FONT_CN, font_size, bold=(first_col_bold and cidx == 0), color=INK)

    # 固定表格布局，真正按给定列宽渲染
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for idx, width in enumerate(widths):
        table.columns[idx].width = Cm(width)
        for cell in table.columns[idx].cells:
            cell.width = Cm(width)

    if cap:
        caption(doc, cap)
    return table


def callout(doc, title, body, tone="blue"):
    fills = {"blue": "F2F7FF", "amber": "FFF9EF", "red": "FFF5F5", "green": "F2FBF6"}
    bars = {"blue": BLUE, "amber": "F79009", "red": RED, "green": GREEN}
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.cell(0, 0)
    cell.width = Cm(16.5)
    shade_cell(cell, fills[tone])
    set_cell_margins(cell, 170, 240, 170, 220)
    set_cell_border(cell, start={"sz": 24, "val": "single", "color": bars[tone]})
    for edge in ("top", "bottom", "end"):
        set_cell_border(cell, **{edge: {"sz": 2, "val": "single", "color": fills[tone]}})
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title)
    set_run_font(r, FONT_CN, 10, bold=True, color=bars[tone])
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    r = p2.add_run(body)
    set_run_font(r, FONT_BODY, 9.5, color=INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_side_by_side(doc, left_path, left_cap, right_path, right_cap, width_cm=7.25):
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for idx, (path, cap) in enumerate(((left_path, left_cap), (right_path, right_cap))):
        cell = table.cell(0, idx)
        cell.width = Cm(8.2)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=Cm(width_cm))
        cp = cell.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(cap)
        set_run_font(r, FONT_CN, 8, color=MUTED)


# ------------------------------------------------------------------
# 文档内容
# ------------------------------------------------------------------
def cover(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(34)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("PRODUCT DESIGN  /  MOBILE FIRST")
    set_run_font(r, FONT_CN, 8.5, bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("工厂个人计件统计软件")
    set_run_font(r, FONT_CN, 27, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("手机端产品与系统设计方案")
    set_run_font(r, FONT_CN, 19, bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("双线五工序 · 扫码报工 · 数据可追溯")
    set_run_font(r, FONT_CN, 10.5, color=MUTED)
    add_bottom_border(p, LINE, 6, 8)

    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    remove_table_borders(table)
    left, right = table.rows[0].cells
    left.width = Cm(10.2)
    right.width = Cm(6.1)
    table.columns[0].width = Cm(10.2)
    table.columns[1].width = Cm(6.1)

    p = left.paragraphs[0]
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("方案包含")
    set_run_font(r, FONT_CN, 9, bold=True, color=BLUE)

    lines = [
        "双线五工序流程与角色权限",
        "手机端 3 步报工与异常处理",
        "数据模型、技术架构与接口",
        "实施计划、验收标准与风险清单",
    ]
    for line in lines:
        lp = left.add_paragraph()
        lp.paragraph_format.space_after = Pt(5)
        r = lp.add_run("•  ")
        set_run_font(r, FONT_CN, 9, bold=True, color=BLUE)
        r = lp.add_run(line)
        set_run_font(r, FONT_BODY, 9.8, color=INK)

    lp = left.add_paragraph()
    lp.paragraph_format.space_before = Pt(16)
    lp.paragraph_format.space_after = Pt(7)
    r = lp.add_run("文档信息")
    set_run_font(r, FONT_CN, 9, bold=True, color=BLUE)

    meta = [
        ("版本", "v1.0"),
        ("日期", "2026 年 11 月"),
        ("适用", "写真线 / 亚克力线 · 双线五工序"),
        ("读者", "厂长、生产主管、班组长、产品与研发"),
    ]
    for k, v in meta:
        mp = left.add_paragraph()
        mp.paragraph_format.space_after = Pt(4)
        r = mp.add_run(f"{k}  ")
        set_run_font(r, FONT_CN, 8.2, color=MUTED)
        r = mp.add_run(v)
        set_run_font(r, FONT_CN, 8.6, color=INK)

    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rp.add_run().add_picture(str(DOCS / "preview-home.png"), width=Cm(5.5))
    cp = right.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cp.add_run("员工端首页 · 真机比例")
    set_run_font(r, FONT_CN, 7.5, color=MUTED)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("本方案配套可运行演示：D:\\工厂个人计件软件")
    set_run_font(r, FONT_CN, 8, color=MUTED)
    doc.add_page_break()

def document_info(doc):
    h1(doc, "文档信息与阅读说明", page_break=True)
    add_table(
        doc,
        ["项目", "内容"],
        [
            ["文档名称", "工厂个人计件统计软件 · 手机端产品与系统设计方案"],
            ["版本", "v1.0（对应可运行 MVP v1.0.3）"],
            ["日期", "2026 年 11 月"],
            ["适用业务", "写真线、亚克力线，各自五道工序的个人计件统计"],
            ["不包含", "工资核算、成本分摊、排产、库存、绩效考核"],
            ["配套交付", "可运行手机端演示、管理端、二维码流转卡、CSV 导出、本方案"],
            ["状态", "可用于内部评审、现场试用与研发排期"],
        ],
        widths=[3.3, 13.2],
        font_size=9,
        first_col_bold=True,
        cap="表 1 文档基本信息",
    )

    h2(doc, "修订记录")
    add_table(
        doc,
        ["版本", "日期", "修订内容", "编制"],
        [
            ["v0.1", "2026-11-06", "梳理双线五工序、17 人岗位与管理端需求", "产品"],
            ["v0.9", "2026-11-06", "完成可运行手机端 MVP 与管理端演示", "研发"],
            ["v1.0", "2026-11-06", "补齐数据模型、技术架构、实施计划与验收标准", "产品 / 研发"],
        ],
        widths=[2.0, 3.0, 9.2, 2.3],
        font_size=8.5,
        cap="表 2 修订记录",
    )

    h2(doc, "阅读说明")
    bullet(doc, "厂长 / 生产主管：先读「一页结论」「2 现场与需求分析」「10 实施计划」，重点确认岗位与计量口径。", bold_lead="管理者：")
    bullet(doc, "产品 / 交互：重点读「5 手机端体验设计」，可直接用配套演示做现场测试。", bold_lead="产品：")
    bullet(doc, "研发：重点读「6 防错规则」「7 数据模型」「8 技术架构与接口」，可作为排期与建库依据。", bold_lead="研发：")
    callout(
        doc,
        "先确认这 3 件事，再进入开发",
        "① 写真裁切已明确由黄伟、刘浩负责；② 王坚、张知亮已授权为双线全线多能工；③ 现在只需确认亚克力过胶兼岗和排版/裁切的计量单位。",
        "amber",
    )

    h2(doc, "目录")
    toc = [
        ("00", "一页结论"),
        ("01", "项目背景与目标"),
        ("02", "现场与需求分析"),
        ("03", "产品定位与总体方案"),
        ("04", "核心业务流程"),
        ("05", "手机端体验设计"),
        ("06", "防错、权限与数据可信"),
        ("07", "数据模型"),
        ("08", "技术架构与接口"),
        ("09", "报表与统计口径"),
        ("10", "实施计划与验收"),
        ("11", "风险、假设与待确认事项"),
        ("A", "附录 A 演示账号与运行"),
        ("B", "附录 B 17 人岗位矩阵"),
        ("C", "附录 C 术语表"),
    ]
    for num, title in toc:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(1.3), WD_TAB_ALIGNMENT.LEFT)
        r = p.add_run(f"{num}\t{title}")
        set_run_font(r, FONT_CN, 10, color=INK if num not in ("00", "A", "B", "C") else MUTED)
    para(doc, "提示：Word 打开后可使用「视图 → 导航窗格」按标题快速跳转；页脚显示当前页码。", size=8.5, color=MUTED)


def executive_summary(doc):
    h1(doc, "00 一页结论", page_break=True)
    para(
        doc,
        "计件通是一套面向工厂一线员工的手机计件工具。它不计算工资，只回答三个问题：谁、在哪个订单的哪道工序、完成了多少。",
        bold_lead="一句话：",
        size=11,
    )

    h2(doc, "产品方案")
    add_table(
        doc,
        ["维度", "结论"],
        [
            ["产品形态", "微信小程序（工人端）+ 响应式 Web 管理后台；本期交付可运行 H5/PWA 演示"],
            ["核心动作", "扫码 → 输入数量 → 确认提交，目标 15 秒内完成一笔报工"],
            ["业务模型", "订单 → 按产线拆生产任务 → 一张流转卡 → 五道工序 → 多条报工记录"],
            ["数据底线", "每条记录保存独立单位；已计入记录不可删除；超报转厂长确认；全程留痕"],
            ["统计范围", "个人日/周/月产量、工序产出、订单进度、双线汇总、CSV 导出"],
            ["明确不做", "工资、提成、成本、排产、库存、绩效排名"],
        ],
        widths=[3.2, 13.3],
        font_size=9,
        first_col_bold=True,
        cap="表 3 方案结论",
    )

    h2(doc, "为什么现在做")
    bullet(doc, "生产已从四道工序升级为双线五工序，原有的口头/纸质记录无法支撑双线独立统计。", bold_lead="流程变了：")
    bullet(doc, "同一批货可能跨两条线；排版按平方米、裁切按件、综合按个，单位混在一起就一定会算错。", bold_lead="口径复杂：")
    bullet(doc, "工人最关心“我今天做了多少”，厂长最关心“订单卡在哪”，这两件事目前都不透明。", bold_lead="双方都缺数据：")
    bullet(doc, "17 人规模不大，正是用轻量工具把流程跑顺、把口径定死的窗口期。", bold_lead="规模合适：")

    h2(doc, "三个关键设计决策")
    add_table(
        doc,
        ["决策", "做法", "原因"],
        [
            ["订单拆任务", "一个订单可以拆成写真任务、亚克力任务，各自独立流转", "避免一张订单跨线时数据互相污染"],
            ["单位随记录", "每条报工记录保存自己的单位，不做自动换算", "平方米和件没有天然换算关系，强行换算会造假"],
            ["超报不硬拦", "超出可报数量转为待确认，厂长确认后才计入", "现场有补印、返工、分批交付，硬拦截会逼员工改数"],
            ["记录不可删", "只能申请冲销，原记录和审批痕迹保留", "计件数据要经得起月底复核和员工质疑"],
        ],
        widths=[3.1, 8.0, 5.4],
        font_size=8.7,
        first_col_bold=True,
        cap="表 4 关键设计决策",
    )

    h2(doc, "落地节奏")
    para(doc, "建议按「先试点、再双轨、后推广」推进：第 1 周确认口径与岗位；第 2–3 周完成小程序与后端核心；第 4 周管理端与报表；第 5 周单班组试点；第 6 周开始 1 个月双轨运行。")
    callout(
        doc,
        "给厂长的建议",
        "先不要追求“全功能”。把扫码报工、上游校验、个人今日产量、厂长异常确认这四件事做扎实，比做十个报表更能建立信任。",
        "blue",
    )


def section_background(doc):
    h1(doc, "01 项目背景与目标", page_break=True)
    h2(doc, "1.1 背景")
    para(
        doc,
        "现有方案把生产从原来的四道工序升级为「写真线 + 亚克力线」两条独立生产线，每条线五道工序。写真线处理海报、展架、背胶等柔性材料，核心后道是过版覆膜；亚克力线处理亚克力字、导视牌、展示架等硬质材料，核心后道是过胶。两条线在排版、打印环节可能共用设备和人员，但从工序 3 开始独立流转、独立统计。",
    )
    para(
        doc,
        "这次软件改版的核心不是“多一个报表”，而是把生产现场的真实流转变成可核对的数据。系统只统计各工序完成数量，不涉及薪资、成本分摊等复杂逻辑。",
    )

    h2(doc, "1.2 现在的问题")
    add_table(
        doc,
        ["问题", "现场表现", "带来的影响"],
        [
            ["记录分散", "微信群、纸质流转单、个人小本子、月底 Excel 各记一套", "漏记、重复记，月底对不上"],
            ["双线混淆", "同一张订单可能同时有写真和亚克力，统计时靠人回忆", "产量归属不清，无法按线核算"],
            ["单位不统一", "排版按平方米、裁切按件、综合按个，表格里直接相加", "总数看似有，实际不可用"],
            ["进度不透明", "厂长要问“做到哪了”，只能打电话或去车间", "交期风险发现晚"],
            ["工人无感知", "员工不知道自己今天做了多少，月底才知道", "对数据不信任，抵触使用"],
            ["纠错靠改表", "发现错了直接改 Excel，没有痕迹", "无法追溯，容易引发争议"],
        ],
        widths=[3.0, 8.2, 5.3],
        font_size=8.5,
        first_col_bold=True,
        cap="表 5 现状问题",
    )

    h2(doc, "1.3 设计目标")
    add_table(
        doc,
        ["目标", "可衡量标准"],
        [
            ["报工足够快", "熟练员工 15 秒内完成一笔；新员工 30 秒内完成"],
            ["数据足够准", "同人/同订单/同工序重复率 < 1%；月底账实差异 < 2%"],
            ["双线足够清", "每条记录都有 line_type；写真与亚克力可独立汇总"],
            ["异常可处理", "超报、补录、冲销都有明确状态和审批人"],
            ["员工愿意用", "试点班组 2 周内日活 ≥ 90%；员工能随时看到自己的今日产量"],
            ["厂长看得懂", "一屏看到今日产出、进行中订单、待处理异常"],
            ["数据可带走", "日报/月报/订单进度可导出 CSV，Excel 直接打开"],
        ],
        widths=[4.2, 12.3],
        font_size=8.8,
        first_col_bold=True,
        cap="表 6 设计目标与衡量标准",
    )

    h2(doc, "1.4 产品边界")
    add_table(
        doc,
        ["本期做", "本期不做"],
        [
            ["工序计件数量采集与校验", "工资、提成、计件单价计算"],
            ["订单/生产任务/流转卡管理", "自动排产、设备联网、MES 集成"],
            ["个人产量、订单进度、双线汇总", "成本分摊、利润分析"],
            ["异常确认、冲销、审计", "绩效评分、排名、奖惩"],
            ["CSV / Excel 导出", "完整财务系统、进销存"],
        ],
        widths=[8.2, 8.3],
        font_size=9,
        cap="表 7 产品边界",
    )
    callout(
        doc,
        "边界很重要",
        "一旦系统里出现“单价”“工资”“绩效分”，员工就会用薪资视角审视每一个数字，项目的信任成本会成倍上升。本期先把“件数”做准，后续再把计件结果作为绩效或薪资系统的输入。",
        "red",
    )


def section_field(doc):
    h1(doc, "02 现场与需求分析", page_break=True)
    h2(doc, "2.1 双线五工序总览")
    para(doc, "两条线各自拥有完整的五道工序。工序 1–2 可能共用设备和人员，从工序 3 开始独立流转、独立统计。")
    add_image(doc, DIAG / "flow.png", 16.2, "图 1 双线五工序与数据主线")

    add_table(
        doc,
        ["产线", "工序 1", "工序 2", "工序 3", "工序 4", "工序 5"],
        [
            ["写真线", "写真排版", "写真打印", "过版覆膜", "写真裁切", "综合岗位"],
            ["亚克力线", "亚克力排图", "UV 打印", "亚克力过胶", "亚克力裁切", "综合岗位"],
        ],
        widths=[2.5, 2.8, 2.8, 2.8, 2.8, 2.8],
        font_size=8.5,
        first_col_bold=True,
        cap="表 8 双线五工序",
    )

    h2p = h2(doc, "2.2 17 人岗位盘点")
    h2p.paragraph_format.page_break_before = True
    para(doc, "以下映射来自你提供的花名册。它是演示版的默认权限，不等同于正式授权；试点前需要厂长逐人确认。")
    rows = [
        ["1", "肖尾珍", "综合岗位", "双线", "5", "可跨线，报工时必须选产线"],
        ["2", "余道京", "综合岗位", "双线", "5", "可跨线"],
        ["3", "陈根华", "综合岗位", "双线", "5", "可跨线"],
        ["4", "王坤", "裁切（激光切割）", "亚克力", "4", "激光裁切"],
        ["5", "王坚", "裁切（激光切割）· 多能工", "双线", "1–5", "所有工序"],
        ["6", "刘浩", "裁切（激光切割）", "双线", "4", "亚克力裁切 + 写真裁切"],
        ["7", "张知亮", "写真/异型（排版）· 多能工", "双线", "1–5", "所有工序"],
        ["8", "邓强", "UV 打印", "亚克力", "2", "UV 打印"],
        ["9", "梁建华", "过膜过板", "双线", "3", "写真覆膜 + 亚克力过胶（暂定兼岗）"],
        ["10", "刘绍珍", "过膜过板", "双线", "3", "同上"],
        ["11", "胡汝奇", "亚克力排图", "亚克力", "1", "排图"],
        ["12", "喻宏伟", "亚克力排图", "亚克力", "1", "排图"],
        ["13", "肖宏", "写真/异型（打印）", "写真", "2", "打印"],
        ["14", "周艳红", "综合岗位", "双线", "5", "可跨线"],
        ["15", "钟发兰", "综合岗位", "双线", "5", "可跨线"],
        ["16", "朱宗耀", "写真/异型（排版）", "写真", "1", "排版"],
        ["17", "黄伟", "裁切（激光切割）", "双线", "4", "亚克力裁切 + 写真裁切"],
    ]
    add_table(
        doc,
        ["#", "姓名", "花名册岗位", "映射产线", "工序", "说明"],
        rows,
        widths=[0.9, 2.1, 4.0, 2.3, 1.2, 6.0],
        font_size=8.0,
        align_center=[0, 3, 4],
        cap="表 9 17 人岗位映射（演示版默认，需现场确认）",
    )

    h2(doc, "2.3 五个关键发现")
    findings = [
        ("岗位和工序不是一一对应。", "17 人只有 7 类岗位标签，但系统需要覆盖 10 个“产线 × 工序”组合。必须用「技能矩阵」而不是单一岗位字段。"),
        ("综合岗位是共享资源。", "5 名综合岗位同时覆盖两条线。报工时必须明确选择产线，否则统计无法归属。"),
        ("多能工能补位，但授权要写清楚。", "王坚、张知亮负责全线所有工序，黄伟、刘浩兼写真/亚克力裁切。系统按技能矩阵放行，厂长仍需明确哪些是正式授权、哪些是临时顶岗，避免计件归属争议。"),
        ("亚克力过胶没有独立岗位。", "演示版暂按“过膜过板”兼岗。这是业务假设，不是花名册事实，必须确认。"),
        ("计量单位有冲突。", "方案文档表格里亚克力裁切写平方米，正文写件；排版可能按“单/件”而不是平方米。系统必须允许每条记录独立单位，不能写死。"),
    ]
    for idx, (title, body) in enumerate(findings, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run(f"{idx:02d}  ")
        set_run_font(r, FONT_CN, 11, bold=True, color=BLUE)
        r = p.add_run(title)
        set_run_font(r, FONT_CN, 10.5, bold=True, color=INK)
        r = p.add_run(" " + body)
        set_run_font(r, FONT_BODY, 10.2, color=INK)

    callout(
        doc,
        "授权已经落地，剩下的是口径",
        "王坚、张知亮已授权全线，黄伟、刘浩兼写真裁切。接下来只需确认亚克力过胶由谁兼岗，以及排版/裁切到底按平方米还是按件；这两项确认后，系统就能稳定运行。",
        "amber",
    )

    h2(doc, "2.4 现场约束与设计应对")
    add_table(
        doc,
        ["现场约束", "对设计的直接影响"],
        [
            ["工人戴手套、手指粗", "按钮高度 ≥ 48px，数字键盘要大；避免小图标和滑动操作"],
            ["车间光线复杂、屏幕反光", "高对比度；主按钮用实色；不只靠颜色区分状态"],
            ["部分员工年龄偏大", "少文字、多数字；关键结果用大字号；允许双指缩放"],
            ["Wi-Fi 有盲区", "报工先写本地队列，联网自动重试；界面明确显示“待同步”"],
            ["手机型号杂、以安卓为主", "不依赖高端机；首屏轻量；相机不可用时允许手工输入"],
            ["生产节奏快", "3 步完成；常用数量一键填；上次报工可复制"],
            ["员工怕“被监控”", "只统计产量，不做定位；明确告知数据用途；员工可看自己的全部记录"],
        ],
        widths=[5.5, 11.0],
        font_size=8.6,
        first_col_bold=True,
        cap="表 10 现场约束与设计应对",
    )

    h2(doc, "2.5 需求优先级")
    add_table(
        doc,
        ["优先级", "需求", "说明"],
        [
            ["Must", "扫码识别订单与工序", "没有它，系统不成立"],
            ["Must", "数量录入 + 上游校验", "保证数据基本准确"],
            ["Must", "员工查看自己的今日/本月产量", "建立信任的关键"],
            ["Must", "厂长异常确认", "处理超报、补录、冲销"],
            ["Must", "订单/工序/员工/时间四维明细", "月底复核的底稿"],
            ["Should", "离线队列与自动重试", "工厂网络不稳定"],
            ["Should", "二维码流转卡打印", "把系统落到现场"],
            ["Should", "CSV/Excel 导出", "管理层已有工作习惯"],
            ["Could", "现场拍照留证", "用于异常，不要求每笔都拍"],
            ["Won't", "工资/绩效/排名", "本期明确不做，避免范围蔓延"],
        ],
        widths=[2.2, 7.2, 7.1],
        font_size=8.5,
        first_col_bold=True,
        align_center=[0],
        cap="表 11 需求优先级（MoSCoW）",
    )


def section_product(doc):
    h1(doc, "03 产品定位与总体方案", page_break=True)
    h2(doc, "3.1 产品定位")
    para(doc, "计件通是一个「轻量、可信、手机优先」的工序计件工具。它不替代 ERP，也不做薪资，只把生产现场最原始、最容易丢失的“完成数量”记录下来，并让相关人当场看到。")
    add_table(
        doc,
        ["要素", "定义"],
        [
            ["用户", "一线员工（主要）、班组长、厂长、系统管理员"],
            ["场景", "车间、机器旁、裁切台、包装台；站立、单手、戴手套"],
            ["核心任务", "扫描流转卡 → 输入本次完成数量 → 提交"],
            ["核心价值", "员工看见自己的件数；厂长看见订单卡在哪；月底有可复核的底稿"],
            ["成功体验", "像扫码付款一样简单；错了能改；改过有痕迹"],
        ],
        widths=[3.2, 13.3],
        font_size=8.8,
        first_col_bold=True,
        cap="表 12 产品定位",
    )

    h2(doc, "3.2 产品结构")
    add_table(
        doc,
        ["端", "载体", "主要功能", "使用建议"],
        [
            ["工人端", "微信小程序（推荐）；H5/PWA 备用", "登录、扫码、报工、记录、统计、订单进度、消息", "车间手机；一人一号"],
            ["管理端", "响应式 Web（PC 优先，手机可用）", "概览、订单、异常、人员技能、报表", "厂长办公室 / 手机巡查"],
            ["打印端", "普通标签打印机 / A4 打印", "流转卡二维码、订单信息", "订单释放时打印，贴在流转卡上"],
        ],
        widths=[2.3, 4.2, 6.5, 3.5],
        font_size=8.5,
        first_col_bold=True,
        cap="表 13 三端结构",
    )
    para(doc, "为什么推荐微信小程序，而不是原生 App：工人已经安装微信，不需要应用商店；扫码、拍照、登录能力齐全；更新即时；开发成本低于 iOS/Android 双端。缺点是需要小程序主体、备案和 HTTPS 域名，这些要提前准备。")

    h2(doc, "3.3 核心对象模型")
    add_table(
        doc,
        ["对象", "定义", "关键字段", "为什么需要"],
        [
            ["订单 Order", "客户的一次需求", "订单号、客户、平台、交期", "对外的业务凭证"],
            ["生产任务 Job", "订单按产线拆分后的生产单元", "产线、产品、规格、计划量、单位、二维码", "双线独立统计的关键；一个订单可拆多个 Job"],
            ["工序步骤 JobStep", "任务下的五道工序配置", "工序号、单位、计划量、完成量", "支持不同工序不同单位"],
            ["流转卡", "贴在实物上的二维码载体", "二维码 token、订单号、产品、规格", "把线上记录和线下实物绑定"],
            ["报工记录 Record", "某人某任务某工序的一次完成", "人、数量、单位、时间、状态、幂等键", "唯一事实来源"],
            ["冲销记录 Correction", "对已计入记录的更正申请", "原因、证据、申请人、审批人", "保证可追溯，不物理删除"],
        ],
        widths=[2.7, 4.6, 5.5, 3.7],
        font_size=8.3,
        first_col_bold=True,
        cap="表 14 核心对象",
    )

    h2(doc, "3.4 角色与权限")
    add_table(
        doc,
        ["能力", "员工", "班组长", "厂长", "系统管理员"],
        [
            ["扫码报工（本人）", "✓", "✓", "✓", "—"],
            ["查看本人记录/统计", "✓", "✓", "✓", "—"],
            ["查看全厂订单进度", "—", "✓", "✓", "✓"],
            ["代报 / 补录", "—", "申请", "审批", "—"],
            ["超报确认 / 冲销审批", "—", "—", "✓", "—"],
            ["新建订单 / 打印流转卡", "—", "—", "✓", "✓"],
            ["人员技能授权", "—", "—", "✓", "✓"],
            ["导出报表", "本人", "本组", "全厂", "全厂"],
            ["系统配置 / 账号", "—", "—", "—", "✓"],
        ],
        widths=[5.2, 2.6, 2.6, 2.6, 3.0],
        font_size=8.6,
        align_center=[1, 2, 3, 4],
        cap="表 15 角色权限矩阵",
    )
    para(doc, "关键原则：一人一号，不共用账号；代报必须显式记录“代报人”和原因；厂长也不能删除已计入记录，只能走冲销。", size=9.5)

    h2(doc, "3.5 设计原则")
    principles = [
        ("3 步完成", "扫码 → 数量 → 确认。任何额外字段都不能阻塞主流程。"),
        ("默认正确", "根据员工技能和订单状态，自动带出可报工序与单位，减少选择。"),
        ("异常不硬拦", "超报、补录转确认，而不是逼员工改一个“系统能过”的数。"),
        ("数字要可见", "首页第一屏就是今天做了多少；员工不需要点三层菜单。"),
        ("记录不可变", "已计入记录不删除；冲销保留原记录、原因、审批人。"),
        ("弱网可用", "先写本机，再同步；断网不能成为停工理由。"),
    ]
    add_table(
        doc,
        ["原则", "落地做法"],
        [[a, b] for a, b in principles],
        widths=[3.2, 13.3],
        font_size=8.8,
        first_col_bold=True,
        cap="表 16 六条设计原则",
    )

    h2(doc, "3.6 与现有绩效系统的关系")
    para(doc, "如果后续要与「衡绩」员工绩效系统打通，计件数据可以作为“产量事实”输入，但应保持边界：计件通负责记录数量与工序，绩效系统负责指标、权重与评分。不要把绩效规则写进报工端，否则员工会把每一次报工当成“打分”，数据就会失真。")
    para(doc, "推荐接口：按统计期导出「员工 + 产线 + 工序 + 数量 + 单位 + 有效工时」的聚合表，由绩效系统消费；两边不做实时耦合，避免一改规则就影响生产。")


def section_flow(doc):
    h1(doc, "04 核心业务流程", page_break=True)
    h2(doc, "4.1 端到端流程")
    steps = [
        ("订单接入", "淘宝订单 / 线下订单录入或导入，填写客户、产品、规格、数量、交期。"),
        ("拆生产任务", "按产线拆成写真任务、亚克力任务；一个订单允许有多个任务。"),
        ("生成流转卡", "系统生成唯一二维码，打印后随实物流转；补印/重打不改变 token。"),
        ("扫码报工", "员工扫码，系统识别订单、当前可报工序、上游已转数量。"),
        ("数量校验", "技能、单位、重复、上游数量、日上限逐项校验；超报转确认。"),
        ("异常确认", "厂长在管理端确认或驳回；确认后才计入有效产量。"),
        ("统计与对账", "个人日/月统计、订单进度、双线汇总；每日与手工记录对账。"),
        ("归档导出", "月末导出 CSV/Excel，锁定统计期，进入复核。"),
    ]
    for idx, (title, body) in enumerate(steps, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(f"{idx:02d}")
        set_run_font(r, FONT_CN, 13, bold=True, color=BLUE)
        r = p.add_run(f"  {title}")
        set_run_font(r, FONT_CN, 10.8, bold=True, color=INK)
        r = p.add_run(f"    {body}")
        set_run_font(r, FONT_BODY, 10, color=INK)

    h2(doc, "4.2 员工报工：3 步、15 秒")
    add_table(
        doc,
        ["步骤", "员工动作", "系统反馈", "设计要点"],
        [
            ["1 扫码", "对准流转卡二维码", "震动 + 显示订单、产品、当前工序", "扫不出时允许输入订单号后 4 位"],
            ["2 填数", "大键盘输入本次数量", "实时显示上游已转、本工序已报、剩余可报", "常用数量一键填；单位自动带出"],
            ["3 确认", "点“确认提交”", "大号成功页 + 今日累计", "重复/超报二次确认；可继续扫下一单"],
        ],
        widths=[2.0, 4.7, 5.6, 4.2],
        font_size=8.6,
        first_col_bold=True,
        cap="表 17 三步报工",
    )
    callout(
        doc,
        "为什么不是“扫完直接提交”",
        "扫码只代表“我到了这张流转卡”，不代表“我完成了多少”。数量必须由员工确认，否则系统会变成“扫码即完工”，数据一定失真。",
        "blue",
    )

    h2(doc, "4.3 部分流转与拆单")
    para(doc, "真实生产不是“上一道 100% 完成后下一道才开始”。常见情况：打印完成 18/28.8 平方米，裁切可以先裁这 18 平方米；客户临时加印；一批货分两次交付。系统用「累计完成 + 上游已转」处理部分流转，不要求每道工序一次报满。")
    bullet(doc, "下游可报数量 = min(本工序计划剩余, 上游已转 − 本工序已报)；同单位才自动计算。", bold_lead="规则：")
    bullet(doc, "不同单位（如覆膜按平方米、综合按件）不做自动换算，只按本工序计划量兜底，由厂长确认合理性。", bold_lead="单位不同：")
    bullet(doc, "一张流转卡走完五道工序；如果客户拆单，建议生成新的生产任务和新的流转卡，不要把两个批次混在一张卡上。", bold_lead="拆单：")

    h2(doc, "4.4 异常流程")
    add_table(
        doc,
        ["场景", "系统行为", "员工看到什么", "厂长看到什么"],
        [
            ["超出可报数量", "生成 pending 记录，不计入产量", "“已提交，待厂长确认”", "异常列表：谁、多少、哪个订单"],
            ["疑似重复", "同人/同单/同工序/同数量 10 分钟内二次确认", "“可能重复，请确认”", "如确认，两笔都保留"],
            ["上游未完成", "阻止提交", "“上游尚未报工，请稍后”", "订单进度显示卡点"],
            ["非本工序技能", "阻止提交", "“你的技能不包含该工序”", "人员技能矩阵显示缺口"],
            ["数量录错", "员工发起冲销申请", "“已提交给厂长”", "更正/冲销列表，审批"],
            ["断网", "写本地队列，显示待同步", "“已保存，联网自动同步”", "同步后出现在列表；异常延迟可见"],
        ],
        widths=[3.2, 5.2, 4.2, 4.0],
        font_size=8.3,
        first_col_bold=True,
        cap="表 18 异常处理策略",
    )

    h2(doc, "4.5 状态机")
    add_table(
        doc,
        ["对象", "状态", "说明"],
        [
            ["报工记录", "pending", "待厂长确认；不计入任何统计"],
            ["报工记录", "valid", "已计入；参与个人/订单/双线统计"],
            ["报工记录", "void", "已冲销；保留原记录，不计入"],
            ["生产任务", "draft / active / done / cancelled", "草稿、进行中、已完成、已取消"],
            ["工序步骤", "not_started / in_progress / done", "未开始、进行中、已完成"],
            ["冲销申请", "pending / approved / rejected", "待审批、已同意、已驳回"],
        ],
        widths=[3.2, 6.2, 7.1],
        font_size=8.6,
        first_col_bold=True,
        cap="表 19 核心状态机",
    )

    h2(doc, "4.6 日结与对账")
    para(doc, "建议每天下班前 10 分钟做一次“日结”：系统按产线/工序汇总当日有效产量，班组长用手工流转单核对，差异超过 2% 的订单第二天优先排查。日结对账比月底一次总算更容易发现问题，也更容易让员工相信数据。")
    add_table(
        doc,
        ["时点", "动作", "输出"],
        [
            ["每笔报工", "员工确认 + 系统校验", "一条有效/待确认记录"],
            ["每日 17:30", "班组长日结，核对差异", "日结表 + 差异清单"],
            ["每周五", "厂长看异常趋势、岗位缺口", "周报 + 整改项"],
            ["每月 1 日", "锁定上月、导出、归档", "月度计件底稿 CSV/Excel"],
        ],
        widths=[3.0, 7.0, 6.5],
        font_size=8.6,
        first_col_bold=True,
        cap="表 20 对账节奏",
    )


def section_mobile(doc):
    h1(doc, "05 手机端体验设计", page_break=True)
    para(doc, "手机端的设计目标不是“把 PC 表格搬到手机上”，而是让员工在机器旁、站着、戴着手套也能在 15 秒内完成一次报工。", size=10.5)

    h2(doc, "5.1 信息架构")
    add_table(
        doc,
        ["层级", "页面", "核心内容"],
        [
            ["一级", "首页", "今日产量、扫码入口、进行中订单、最近报工、待确认提醒"],
            ["一级", "订单", "搜索、进行中/已完成、订单详情、五工序时间线、流转卡"],
            ["一级", "统计", "今日/本周/本月、按工序分布、日均、导出"],
            ["一级", "我的", "技能、本月数据、消息、同步、帮助、切换账号"],
            ["二级", "扫码", "相机取景、演示流转卡、手动输入订单号"],
            ["二级", "确认报工", "订单信息、五工序 stepper、可报数量、数字键盘、备注/拍照"],
            ["二级", "提交成功", "成功/待确认、票单详情、继续报工"],
            ["二级", "记录详情", "完整字段、状态、冲销申请"],
        ],
        widths=[1.8, 4.0, 10.7],
        font_size=8.5,
        first_col_bold=True,
        cap="表 21 员工端信息架构",
    )

    h2(doc, "5.2 首页：先给员工一个数字")
    add_image(doc, DOCS / "preview-home.png", 7.4, "图 2 员工端首页：今日产量 + 扫码入口 + 进行中订单")
    para(doc, "首页第一屏只做三件事：告诉员工今天做了多少、给他一个最大的扫码按钮、提醒他有几笔待确认。进行中订单和最近报工放在下面，作为辅助信息。")
    bullet(doc, "今日产量按单位分别展示，不做“总面积 + 总件数”的假合计。", bold_lead="大数字：")
    bullet(doc, "扫码卡片横跨整行，拇指自然落点；下方三个快捷入口只做辅助。", bold_lead="主按钮：")
    bullet(doc, "待确认记录用琥珀色提示，明确“暂未计入产量”，避免员工误以为系统漏记。", bold_lead="待确认：")

    h2(doc, "5.3 扫码：把线下流转卡接到线上")
    add_side_by_side(doc, DOCS / "preview-scan.png", "图 3 扫码页：相机取景 + 演示流转卡", DOCS / "preview-entry.png", "图 4 确认报工：数量、校验与数字键盘")
    para(doc, "扫码页保留“演示流转卡”和“手动输入订单号”两个兜底入口。车间网络、相机权限、二维码磨损都可能导致扫不出来，不能让员工因此停线。")
    bullet(doc, "二维码只承载不透明 token，不直接写客户名、电话等敏感信息。", bold_lead="安全：")
    bullet(doc, "同一张流转卡可在五道工序重复扫描；系统根据员工技能和订单状态决定可报工序。", bold_lead="复用：")
    bullet(doc, "扫不出时输入订单号后 4 位或完整订单号，仍可进入报工。", bold_lead="兜底：")

    h2(doc, "5.4 报工：把“可报多少”说清楚")
    add_image(doc, DOCS / "preview-entry.png", 7.6, "图 5 报工页：计划、上游已转、本工序已报、本次数量")
    para(doc, "报工页是整套系统最关键的一屏。它必须在同一屏回答四个问题：这是哪个订单、现在做第几道、上游转了多少、我这次能报多少。")
    add_table(
        doc,
        ["区域", "信息", "设计意图"],
        [
            ["顶部", "产品名、订单号、规格、交期、产线、第几道", "防止扫错单、做错工序"],
            ["工序条", "五道工序，已完成打勾，当前高亮", "让员工知道前后道关系"],
            ["数量卡", "计划 / 上游已转 / 本工序已报", "解释“为什么只能报这么多”"],
            ["输入区", "大号数字 + 单位 + 快捷比例", "减少输入，降低出错"],
            ["校验条", "绿色可报 / 琥珀超报 / 红色阻断", "状态一眼可见，不用读长句"],
            ["底部", "确认提交 + 今日累计", "固定可见，不因滚动丢失"],
        ],
        widths=[2.3, 8.2, 6.0],
        font_size=8.3,
        first_col_bold=True,
        cap="表 22 报工页信息层级",
    )
    callout(
        doc,
        "不要用“最多可报”四个字就结束",
        "员工需要知道这个数字是怎么来的。把“计划、上游已转、本工序已报”三个数摆出来，比一句“超出上限”更能减少争执。",
        "blue",
    )

    h2(doc, "5.5 提交成功：给一个确定的反馈")
    add_side_by_side(doc, DOCS / "preview-success.png", "图 6 提交成功：票单式反馈", DOCS / "preview-records.png", "图 7 我的记录：按日分组、状态可筛")
    para(doc, "成功页采用“票单”而不是“弹窗”。员工可以看到订单、工序、数量、时间、记录编号，必要时截图给班组长。待确认时，成功页会变成琥珀色，并明确“确认前不计入产量”。")

    h2(doc, "5.6 统计与订单进度")
    add_side_by_side(doc, DOCS / "preview-stats.png", "图 8 我的统计：按日/周/月与工序分布", DOCS / "preview-detail.png", "图 9 订单详情：五工序时间线 + 流转卡")
    para(doc, "统计页只统计“已计入”的记录，待确认和已冲销不参与；平方米、件、套分单位展示，不做跨单位相加。订单详情用纵向时间线展示五道工序，每个工序显示完成量/计划量、报工人和笔数。")

    h2(doc, "5.7 管理端：厂长的一屏")
    add_image(doc, DOCS / "preview-admin.png", 16.0, "图 10 管理端生产概览：今日产出、五工序、异常与进行中订单")
    para(doc, "管理端不是员工端的放大版。它围绕三个问题组织：今天做了多少、哪些订单卡住、哪些异常需要我处理。")
    add_table(
        doc,
        ["模块", "回答的问题", "关键交互"],
        [
            ["生产概览", "今天工厂发生了什么？", "KPI、双线产出、五工序在制进度、异常待办"],
            ["订单管理", "哪些单在进行？卡在哪？", "新建、打印流转卡、进度条、交期"],
            ["异常确认", "哪些数需要我拍板？", "确认计入、驳回冲销、更正审批"],
            ["人员技能", "谁会做哪道工序？哪里缺人？", "双线五工序矩阵、红色缺口"],
            ["报表导出", "月底拿什么对账？", "今日/本月明细、员工汇总、订单进度"],
        ],
        widths=[3.0, 6.5, 7.0],
        font_size=8.5,
        first_col_bold=True,
        cap="表 23 管理端模块",
    )

    h2(doc, "5.8 交互规范")
    add_table(
        doc,
        ["项目", "规范"],
        [
            ["触控目标", "主按钮 ≥ 52px；数字键 ≥ 44px；图标按钮 ≥ 40px"],
            ["一屏完成", "390×844 下报工主流程不滚动即可看到提交按钮"],
            ["输入", "数量使用自定义数字键盘；不允许负号；小数点后最多 2 位"],
            ["反馈", "提交成功震动 25ms；异常震动 2 次；Toast 不超过 2 行"],
            ["加载", "超过 300ms 显示骨架/加载；超过 3s 显示“网络较慢”"],
            ["错误文案", "说人话：告诉用户“发生了什么、该怎么办”，不显示错误码"],
            ["返回", "报工页返回保留已输入数量；成功页返回不重复提交"],
            ["离线", "顶部明确显示“离线模式”；记录标记“待同步”"],
        ],
        widths=[3.2, 13.3],
        font_size=8.6,
        first_col_bold=True,
        cap="表 24 交互规范",
    )

    h2(doc, "5.9 视觉规范")
    add_table(
        doc,
        ["角色", "色值", "用途"],
        [
            ["深海军蓝", "#0B1F33", "品牌、首页顶部、管理端侧栏"],
            ["行动蓝", "#1467E8", "主按钮、写真线、链接"],
            ["安全橙", "#F79009", "亚克力线、待确认、超报"],
            ["成功绿", "#12B76A", "已计入、完成、成功"],
            ["警示红", "#E5484D", "冲销、驳回、阻断"],
            ["纸白", "#F4F6F9", "页面背景"],
            ["墨色", "#10233C", "正文"],
            ["次级灰", "#718096", "说明文字"],
        ],
        widths=[3.2, 3.0, 10.3],
        font_size=8.6,
        first_col_bold=True,
        cap="表 25 色彩规范",
    )
    para(doc, "字号：页面标题 23–24px，卡片标题 16–17px，正文 14–15px，辅助说明不小于 11px；关键数字使用等宽数字字体，避免跳动。")

    h2(doc, "5.10 现场适配与无障碍")
    bullet(doc, "页面允许双指缩放；关键按钮和数字不因系统字号放大而截断。", bold_lead="大字：")
    bullet(doc, "状态不只靠颜色，同时有文字和图标（已计入/待确认/已冲销）。", bold_lead="色盲：")
    bullet(doc, "按钮间距 ≥ 8px，避免戴手套误触；危险操作二次确认。", bold_lead="误触：")
    bullet(doc, "不用细线图标表达关键信息；关键数字对比度 ≥ 4.5:1。", bold_lead="对比度：")
    bullet(doc, "相机不可用、二维码磨损时，始终保留手工输入。", bold_lead="兜底：")

    h2(doc, "5.11 离线与弱网")
    para(doc, "车间 Wi-Fi 经常有盲区，离线不是“加分项”，而是“基本要求”。前端把报工写入本地队列，联网后按顺序重放；每条记录带客户端 UUID，服务端用唯一键保证重复提交不会产生第二条记录。")
    add_table(
        doc,
        ["场景", "前端行为", "后端行为", "用户看到"],
        [
            ["无网络", "写入本地队列，标记待同步", "—", "“已保存，联网自动同步”"],
            ["恢复网络", "自动按时间顺序重放", "幂等键去重；返回已存在记录", "“已同步”"],
            ["提交超时", "不直接报错，先查记录是否存在", "按幂等键查询", "“正在确认，请稍候”"],
            ["服务端冲突", "拉取最新状态，提示人工处理", "返回冲突码与当前值", "“这笔记录需厂长确认”"],
        ],
        widths=[2.8, 6.2, 4.8, 4.0],
        font_size=8.4,
        first_col_bold=True,
        cap="表 26 离线同步策略",
    )


def section_trust(doc):
    h1(doc, "06 防错、权限与数据可信", page_break=True)
    para(doc, "计件数据直接关系到员工收入预期和工厂成本，必须做到“错得少、改得清、查得到”。")

    h2(doc, "6.1 校验规则")
    add_table(
        doc,
        ["编号", "规则", "触发条件", "处理"],
        [
            ["R1", "流转卡有效", "token 不存在/已作废", "阻断，提示联系厂长"],
            ["R2", "任务进行中", "任务已完成/取消", "阻断，显示任务状态"],
            ["R3", "员工具备技能", "技能矩阵无该产线/工序", "阻断，提示申请授权"],
            ["R4", "单位允许", "单位不在工序配置中", "阻断，提示选择正确单位"],
            ["R5", "数量合法", "≤0、非数字、超过 9999", "阻断，提示正确范围"],
            ["R6", "幂等", "同一客户端 UUID 重复提交", "返回原记录，不新增"],
            ["R7", "防重复", "同人/同单/同工序/同数量，10 分钟内", "二次确认，保留两笔"],
            ["R8", "上游数量", "同单位累计超过上游已转", "转待确认，不直接计入"],
            ["R9", "日上限", "单日异常高于历史 P99", "标记异常，厂长复核"],
            ["R10", "冲销审批", "已计入记录申请更正", "必须填写原因，厂长审批"],
        ],
        widths=[1.2, 4.0, 6.4, 5.0],
        font_size=8.2,
        first_col_bold=True,
        align_center=[0],
        cap="表 27 十道校验规则",
    )

    h2(doc, "6.2 防作弊设计")
    add_table(
        doc,
        ["风险", "手段", "强度"],
        [
            ["代扫/代人报工", "一人一号；设备绑定；异常频次；班组长抽查", "中"],
            ["二维码被拍照传播", "token 随机 + HMAC 签名；订单完成后失效；可补发/吊销", "中高"],
            ["虚报数量", "上游校验 + 日上限 + 照片抽检 + 月底对账", "中"],
            ["重复报工", "客户端幂等键 + 服务端唯一约束 + 10 分钟重复提示", "高"],
            ["事后改数", "记录不可删除；冲销审批；审计日志", "高"],
            ["共用账号", "微信 openid/手机号绑定；设备变更告警", "中高"],
            ["批量刷单", "同一设备短时间多账号、同一员工高频提交，触发风控", "中"],
        ],
        widths=[4.0, 9.8, 2.7],
        font_size=8.4,
        first_col_bold=True,
        align_center=[2],
        cap="表 28 防作弊设计",
    )
    para(doc, "防作弊的目标不是“抓住谁”，而是让作弊成本高于老老实实报工。过度监控会破坏信任，建议只对异常记录做照片/抽查，不要求每笔拍照。")

    h2(doc, "6.3 审计与不可变")
    bullet(doc, "报工记录一旦 valid，不允许 UPDATE qty 或 DELETE；更正通过冲销 + 新记录实现。", bold_lead="记录：")
    bullet(doc, "每次创建、确认、驳回、冲销、改价（如有）都写 audit_log，包含操作人、时间、IP、设备、前后值。", bold_lead="审计：")
    bullet(doc, "审计日志只追加，不允许业务账号删除；保留至少 3 年。", bold_lead="保留：")
    bullet(doc, "每月锁定统计期；锁定后只能新增“调整说明”，不能改历史记录。", bold_lead="锁定：")

    h2(doc, "6.4 数据质量指标")
    add_table(
        doc,
        ["指标", "定义", "目标"],
        [
            ["报工覆盖率", "有报工记录的订单 / 应报工订单", "≥ 98%"],
            ["重复率", "重复提示后被确认重复的笔数 / 总笔数", "< 1%"],
            ["超报率", "pending 笔数 / 总笔数", "< 3%"],
            ["同步成功率", "成功同步的离线记录 / 离线记录", "≥ 99.5%"],
            ["日结对账差异", "系统与手工差异 / 系统产量", "< 2%"],
            ["员工查询率", "当日查看过本人记录的员工 / 当日报工员工", "≥ 70%"],
        ],
        widths=[4.0, 8.7, 3.8],
        font_size=8.5,
        first_col_bold=True,
        align_center=[2],
        cap="表 29 数据质量指标",
    )


def section_data(doc):
    h1(doc, "07 数据模型", page_break=True)
    para(doc, "数据模型的核心是「一个订单可以有多个生产任务，一个任务只属于一条产线，一条报工记录只属于一个任务的某道工序」。")
    add_image(doc, DIAG / "data-model.png", 16.2, "图 11 核心数据模型（ER 示意）")

    h2(doc, "7.1 建模原则")
    bullet(doc, "数量使用 DECIMAL(12,3)，禁止 FLOAT/DOUBLE，避免 0.1+0.2 的精度问题。", bold_lead="精度：")
    bullet(doc, "每条记录保存 unit，统计时按 unit 分组；不做隐式换算。", bold_lead="单位：")
    bullet(doc, "line_type 同时存在于 job 和 record，便于查询与分区，但以 job 为准。", bold_lead="产线：")
    bullet(doc, "记录不物理删除；void 状态保留原值，correction 记录原因与审批。", bold_lead="不可变：")
    bullet(doc, "所有时间存 UTC，展示时转 Asia/Shanghai；统计期按本地日期切分。", bold_lead="时间：")

    h2(doc, "7.2 核心表")
    tables = [
        (
            "production_order 订单",
            ["字段", "类型", "说明"],
            [
                ["order_id", "BIGINT PK", "订单主键"],
                ["order_no", "VARCHAR(64) UNIQUE", "淘宝订单号/内部单号"],
                ["platform", "VARCHAR(32)", "淘宝/线下/其他"],
                ["customer", "VARCHAR(128)", "客户名称"],
                ["status", "VARCHAR(16)", "draft/active/done/cancelled"],
                ["due_date", "DATE", "交期"],
                ["created_at", "TIMESTAMPTZ", "创建时间"],
            ],
        ),
        (
            "production_job 生产任务",
            ["字段", "类型", "说明"],
            [
                ["job_id", "BIGINT PK", "任务主键"],
                ["order_id", "BIGINT FK", "所属订单"],
                ["line_type", "VARCHAR(16)", "写真/亚克力"],
                ["product", "VARCHAR(128)", "产品名"],
                ["spec", "VARCHAR(255)", "规格"],
                ["planned_qty", "DECIMAL(12,3)", "计划数量"],
                ["unit", "VARCHAR(8)", "m²/件/套"],
                ["qr_token", "VARCHAR(64) UNIQUE", "流转卡 token"],
                ["status", "VARCHAR(16)", "draft/active/done/cancelled"],
                ["due_date", "DATE", "交期"],
            ],
        ),
        (
            "job_step 工序配置",
            ["字段", "类型", "说明"],
            [
                ["id", "BIGINT PK", "主键"],
                ["job_id", "BIGINT FK", "任务"],
                ["step_no", "SMALLINT", "1–5"],
                ["unit", "VARCHAR(8)", "该工序单位"],
                ["planned_qty", "DECIMAL(12,3)", "该工序计划量"],
                ["completed_qty", "DECIMAL(12,3)", "已确认完成量（冗余汇总）"],
                ["status", "VARCHAR(16)", "not_started/in_progress/done"],
            ],
        ),
        (
            "piece_record 报工记录",
            ["字段", "类型", "说明"],
            [
                ["record_id", "BIGINT PK", "记录主键"],
                ["job_id", "BIGINT FK", "任务"],
                ["step_no", "SMALLINT", "工序号"],
                ["line_type", "VARCHAR(16)", "产线（冗余，便于统计）"],
                ["employee_id", "BIGINT FK", "员工"],
                ["qty", "DECIMAL(12,3)", "数量"],
                ["unit", "VARCHAR(8)", "单位"],
                ["status", "VARCHAR(16)", "pending/valid/void"],
                ["idempotency_key", "VARCHAR(64) UNIQUE", "客户端 UUID"],
                ["source", "VARCHAR(16)", "scan/manual/import"],
                ["photo_key", "VARCHAR(255)", "照片对象键（可空）"],
                ["device_id", "VARCHAR(64)", "设备标识"],
                ["record_time", "TIMESTAMPTZ", "发生时间"],
                ["note", "VARCHAR(500)", "备注"],
            ],
        ),
        (
            "employee 员工",
            ["字段", "类型", "说明"],
            [
                ["employee_id", "BIGINT PK", "员工主键"],
                ["name", "VARCHAR(64)", "姓名"],
                ["phone", "VARCHAR(32)", "手机号（加密/脱敏）"],
                ["role", "VARCHAR(32)", "花名册岗位"],
                ["status", "VARCHAR(16)", "active/inactive"],
                ["wechat_openid", "VARCHAR(64)", "小程序 openid"],
            ],
        ),
        (
            "employee_skill 技能矩阵",
            ["字段", "类型", "说明"],
            [
                ["id", "BIGINT PK", "主键"],
                ["employee_id", "BIGINT FK", "员工"],
                ["line_type", "VARCHAR(16)", "产线"],
                ["step_no", "SMALLINT", "工序"],
                ["effective_from", "DATE", "生效日期"],
                ["effective_to", "DATE", "失效日期（可空）"],
                ["approved_by", "BIGINT", "授权人"],
            ],
        ),
        (
            "record_correction 冲销/更正",
            ["字段", "类型", "说明"],
            [
                ["correction_id", "BIGINT PK", "主键"],
                ["record_id", "BIGINT FK", "原记录"],
                ["action", "VARCHAR(16)", "void/replace"],
                ["delta", "DECIMAL(12,3)", "增减量（replace 时）"],
                ["reason_code", "VARCHAR(32)", "原因码"],
                ["reason", "VARCHAR(500)", "说明"],
                ["evidence_key", "VARCHAR(255)", "证据文件"],
                ["requested_by", "BIGINT", "申请人"],
                ["approved_by", "BIGINT", "审批人"],
                ["status", "VARCHAR(16)", "pending/approved/rejected"],
                ["created_at", "TIMESTAMPTZ", "申请时间"],
            ],
        ),
        (
            "audit_log 审计日志",
            ["字段", "类型", "说明"],
            [
                ["event_id", "BIGINT PK", "主键"],
                ["actor_id", "BIGINT", "操作人"],
                ["action", "VARCHAR(32)", "create/approve/reject/... "],
                ["entity_type", "VARCHAR(32)", "record/correction/job"],
                ["entity_id", "BIGINT", "对象 ID"],
                ["before_json", "JSONB", "变更前"],
                ["after_json", "JSONB", "变更后"],
                ["ip", "VARCHAR(64)", "来源 IP"],
                ["device_id", "VARCHAR(64)", "设备"],
                ["created_at", "TIMESTAMPTZ", "时间"],
            ],
        ),
    ]
    for idx, (title, headers, rows) in enumerate(tables, 1):
        h3(doc, f"7.2.{idx} {title}")
        add_table(doc, headers, rows, widths=[4.0, 4.2, 8.3], font_size=8.0, first_col_bold=True)

    h2(doc, "7.3 索引与约束")
    add_table(
        doc,
        ["对象", "索引/约束", "目的"],
        [
            ["piece_record", "UNIQUE(idempotency_key)", "防重复提交"],
            ["piece_record", "INDEX(job_id, step_no, status)", "订单工序汇总"],
            ["piece_record", "INDEX(employee_id, record_time)", "个人日/月统计"],
            ["piece_record", "INDEX(line_type, record_time)", "双线日报"],
            ["employee_skill", "UNIQUE(employee_id, line_type, step_no, effective_from)", "技能不重复"],
            ["job_step", "UNIQUE(job_id, step_no)", "每任务每工序一条配置"],
            ["production_job", "UNIQUE(qr_token)", "流转卡唯一"],
            ["record_correction", "INDEX(record_id, status)", "待审批查询"],
        ],
        widths=[3.8, 8.6, 4.1],
        font_size=8.3,
        first_col_bold=True,
        cap="表 30 关键索引与约束",
    )

    h2(doc, "7.4 计量单位规则")
    add_table(
        doc,
        ["工序", "建议默认单位", "可选单位", "说明"],
        [
            ["写真排版", "m²", "单/件", "以排版文件面积或拼版单数为准，需确认"],
            ["写真打印", "m²", "—", "按实际打印面积"],
            ["写真过版覆膜", "m²", "件", "按覆膜/裱板面积"],
            ["写真裁切", "m²", "件", "按成品面积或件数，需确认"],
            ["写真综合", "件", "个", "包装、贴标、整理"],
            ["亚克力排图", "件", "m²", "按排图件数或面积"],
            ["亚克力 UV 打印", "m²", "件", "按打印面积"],
            ["亚克力过胶", "m²", "件", "按过胶面积或件数"],
            ["亚克力裁切", "件", "m²", "文档表格与正文有冲突，需确认"],
            ["亚克力综合", "件", "套", "组装、打磨、包装"],
        ],
        widths=[4.3, 3.3, 3.2, 5.7],
        font_size=8.2,
        first_col_bold=True,
        align_center=[1, 2],
        cap="表 31 各工序计量单位建议（需现场确认）",
    )
    callout(
        doc,
        "单位不是“技术细节”，是“业务合同”",
        "如果系统默认排版按平方米，但车间实际按“拼版单数”结算，员工会认为系统在克扣；反之亦然。上线前必须把每个工序的单位写成一张确认单，让厂长和班组长签字。",
        "amber",
    )


def section_tech(doc):
    h1(doc, "08 技术架构与接口", page_break=True)
    add_image(doc, DIAG / "architecture.png", 16.2, "图 12 推荐技术架构")

    h2(doc, "8.1 技术选型")
    add_table(
        doc,
        ["层", "推荐", "理由"],
        [
            ["工人端", "微信小程序原生 + TypeScript", "扫码/相机/离线能力最好；无需安装；更新即时"],
            ["管理端", "Vue 3 + Vite + Element Plus", "表格/筛选/导出生态成熟；响应式适配手机"],
            ["后端", "FastAPI + SQLAlchemy + Pydantic", "团队已有 Python 基础；开发快；OpenAPI 文档自动生成"],
            ["数据库", "PostgreSQL 16", "事务、唯一约束、JSONB、窗口函数适合统计"],
            ["缓存", "Redis", "幂等键、限流、看板缓存"],
            ["文件", "阿里云 OSS / 腾讯云 COS / MinIO", "现场照片、导出文件"],
            ["部署", "Docker Compose + Nginx + HTTPS", "2C4G 可起步；后续可平滑上云"],
            ["监控", "结构化日志 + Sentry + 每日报表", "出错可定位；业务异常可预警"],
        ],
        widths=[2.5, 6.8, 7.2],
        font_size=8.4,
        first_col_bold=True,
        cap="表 32 技术选型",
    )
    para(doc, "如果团队更熟悉 Java，后端可替换为 Spring Boot + MyBatis-Plus，数据模型与接口保持不变。关键不是框架，而是幂等、事务、审计和权限。")

    h2(doc, "8.2 部署拓扑")
    para(doc, "单机 Docker Compose 即可支撑 17 人、100 并发以内的场景：Nginx 负责 HTTPS 与静态资源，API 容器 2 个副本，PostgreSQL 主库 + 每日备份，Redis 单实例，文件走对象存储。后续扩容时把数据库迁到云 RDS，API 无状态水平扩展。")
    add_table(
        doc,
        ["资源", "起步配置", "说明"],
        [
            ["应用服务器", "2 vCPU / 4 GB", "API + Nginx + Redis"],
            ["数据库", "2 vCPU / 4 GB / 100 GB", "PostgreSQL，日增数据量很小"],
            ["对象存储", "50 GB", "照片与导出文件"],
            ["备份", "每日全量 + WAL 归档", "保留 30 天，月末归档 3 年"],
            ["带宽", "5 Mbps", "图片压缩后单张 < 300 KB"],
        ],
        widths=[3.6, 5.2, 7.7],
        font_size=8.5,
        first_col_bold=True,
        cap="表 33 起步资源配置",
    )

    h2(doc, "8.3 API 设计")
    add_table(
        doc,
        ["方法", "路径", "用途", "权限"],
        [
            ["POST", "/api/v1/auth/wechat/login", "微信登录，换取 JWT", "公开"],
            ["GET", "/api/v1/me", "当前员工信息与技能", "登录"],
            ["GET", "/api/v1/jobs/by-qr/{token}", "扫码解析订单与工序", "登录"],
            ["GET", "/api/v1/jobs/{id}", "订单详情与五工序进度", "登录"],
            ["POST", "/api/v1/records", "提交报工（Idempotency-Key）", "员工"],
            ["GET", "/api/v1/records/mine", "本人记录（分页/筛选）", "员工"],
            ["POST", "/api/v1/records/{id}/corrections", "申请冲销/更正", "员工"],
            ["GET", "/api/v1/dashboard/summary", "管理端概览", "厂长/管理员"],
            ["POST", "/api/v1/admin/jobs", "新建订单/任务", "厂长/管理员"],
            ["PATCH", "/api/v1/admin/records/{id}/approve", "确认/驳回", "厂长"],
            ["GET", "/api/v1/admin/staff/matrix", "人员技能矩阵", "厂长/管理员"],
            ["GET", "/api/v1/admin/reports/export", "导出 CSV/Excel", "厂长/管理员"],
        ],
        widths=[1.4, 7.0, 6.0, 2.1],
        font_size=8.0,
        first_col_bold=True,
        cap="表 34 核心 API",
    )

    h2(doc, "8.4 报工提交的时序")
    steps = [
        "小程序生成客户端 UUID（idempotency_key），把记录写入本地队列。",
        "POST /records，Header 带 Idempotency-Key、Authorization、X-Device-Id。",
        "服务端先查幂等键：存在则直接返回原记录（200），不重复写。",
        "开启事务：校验技能、单位、数量、上游累计；锁定 job_step 行（SELECT ... FOR UPDATE）。",
        "写入 piece_record；更新 job_step.completed_qty；写 audit_log。",
        "若超报：status=pending，不更新 completed_qty；返回待确认提示。",
        "提交事务，返回记录与最新今日累计。",
        "小程序收到成功响应，移出本地队列，刷新首页数字。",
    ]
    for s in steps:
        numbered(doc, s)
    callout(
        doc,
        "并发要点",
        "两个人同时报同一道工序时，必须用行锁或原子更新保证累计不超卖；不能先查再写。幂等键必须由客户端生成并在重试时保持不变。",
        "red",
    )

    h2(doc, "8.5 二维码设计")
    add_table(
        doc,
        ["项目", "设计"],
        [
            ["内容", "不透明 token，例如 QJ-20261106-001-AB12；不写客户电话/地址"],
            ["生成", "服务端随机 128-bit + HMAC 签名；数据库存 hash"],
            ["打印", "热敏标签 70×100mm；二维码 ≥ 30×30mm；附订单号后 4 位"],
            ["补发", "管理员可重印，token 不变；旧卡继续有效"],
            ["作废", "订单取消时吊销 token；扫码提示“已作废”"],
            ["防伪", "签名校验 + 订单状态 + 设备/时间异常检测"],
        ],
        widths=[3.0, 13.5],
        font_size=8.5,
        first_col_bold=True,
        cap="表 35 二维码设计",
    )

    h2(doc, "8.6 安全与隐私")
    bullet(doc, "全站 HTTPS；JWT 短期 access token + 长期 refresh token；管理端强制二次验证。", bold_lead="传输：")
    bullet(doc, "员工只能看自己；班组长看本组；厂长看全厂；导出带水印与操作日志。", bold_lead="权限：")
    bullet(doc, "手机号加密存储/脱敏展示；照片只存对象键；不采集精确位置。", bold_lead="最小化：")
    bullet(doc, "每日备份；数据库不暴露公网；管理端 IP 白名单（可选）。", bold_lead="运维：")
    bullet(doc, "正式上线前完成小程序主体、隐私政策、员工告知与同意。", bold_lead="合规：")

    h2(doc, "8.7 性能与容量")
    add_table(
        doc,
        ["指标", "目标", "说明"],
        [
            ["报工接口 P95", "< 800ms", "含校验与事务"],
            ["首页加载", "< 1.5s", "4G/普通安卓机"],
            ["并发", "100 在线", "17 人规模绰绰有余"],
            ["日记录量", "1,000 条", "按 17 人 × 20 笔估算"],
            ["数据保留", "3 年", "按月分区/归档"],
            ["可用性", "99.5%", "离线队列兜底"],
        ],
        widths=[4.0, 4.2, 8.3],
        font_size=8.5,
        first_col_bold=True,
        align_center=[1],
        cap="表 36 性能与容量目标",
    )


def section_reports(doc):
    h1(doc, "09 报表与统计口径", page_break=True)
    h2(doc, "9.1 口径定义")
    add_table(
        doc,
        ["状态/概念", "定义", "是否计入统计"],
        [
            ["valid 已计入", "厂长确认或系统自动通过的有效记录", "是"],
            ["pending 待确认", "超报、补录、异常，等待厂长处理", "否"],
            ["void 已冲销", "被驳回或主动冲销的记录", "否"],
            ["计划量", "订单/工序的计划完成数量", "作为分母/参考"],
            ["上游已转", "上一道工序已确认的完成量", "用于可报上限"],
            ["个人产量", "某员工在统计期内的有效记录合计", "按单位分别汇总"],
        ],
        widths=[3.8, 9.2, 3.5],
        font_size=8.5,
        first_col_bold=True,
        align_center=[2],
        cap="表 37 统计口径",
    )

    h2(doc, "9.2 报表清单")
    add_table(
        doc,
        ["报表", "维度", "用途", "频率"],
        [
            ["个人日报", "员工 × 产线 × 工序 × 单位", "员工自查、班组长核对", "每日"],
            ["个人月报", "员工 × 产线 × 工序 × 单位", "月底计件底稿", "每月"],
            ["订单进度", "订单 × 五工序", "交期跟踪、卡点发现", "实时"],
            ["双线汇总", "产线 × 工序 × 日期", "厂长看产能结构", "每日/每周"],
            ["异常清单", "pending/void × 原因", "质量与诚信管理", "每日"],
            ["员工汇总", "员工 × 产线 × 工序", "导出给财务/绩效", "每月"],
        ],
        widths=[3.0, 6.2, 5.2, 2.1],
        font_size=8.3,
        first_col_bold=True,
        cap="表 38 报表清单",
    )

    h2(doc, "9.3 导出字段")
    para(doc, "CSV/Excel 至少包含以下列，保证脱离系统后仍可复核：")
    add_table(
        doc,
        ["字段", "示例", "说明"],
        [
            ["日期 / 时间", "2026-11-06 09:30", "本地时区"],
            ["订单号", "TB20261106001", "可追溯到淘宝订单"],
            ["产品", "奶茶店灯箱海报", "便于人工识别"],
            ["产线", "写真", "写真/亚克力"],
            ["工序", "打印", "五道工序之一"],
            ["员工", "肖宏", "报工本人"],
            ["数量 / 单位", "6 m²", "不合并不同单位"],
            ["状态", "已计入", "已计入/待确认/已冲销"],
            ["备注", "客户临时加印", "异常原因"],
        ],
        widths=[3.4, 6.2, 6.9],
        font_size=8.4,
        first_col_bold=True,
        cap="表 39 导出字段",
    )

    h2(doc, "9.4 对账方法")
    para(doc, "建议每天做“三数对账”：系统有效产量、流转卡手写数量、班组长的生产记录。三者不一致时，先查扫描时间与工序，再查是否有补录/冲销，最后才怀疑系统。")
    add_table(
        doc,
        ["差异类型", "常见原因", "处理"],
        [
            ["系统少", "漏扫、离线未同步、员工不会用", "补录 + 培训；检查队列"],
            ["系统多", "重复扫、代人报、数量输错", "冲销 + 重申一人一号"],
            ["单位不一致", "把件当平方米、把单当件", "修正单位配置；重报"],
            ["工序错位", "扫错流转卡、选错工序", "冲销后重报；核对二维码"],
        ],
        widths=[3.2, 7.4, 5.9],
        font_size=8.5,
        first_col_bold=True,
        cap="表 40 常见对账差异",
    )

    para(doc, "报表的价值在于可复核，而不在于数量多；跨岗位排名、跨单位相加和工资预估，都不在本期报表范围内。", size=9.5, color=MUTED)


def section_plan(doc):
    h1(doc, "10 实施计划与验收", page_break=True)
    h2(doc, "10.1 阶段计划")
    add_table(
        doc,
        ["阶段", "周期", "交付", "责任"],
        [
            ["0 口径确认", "3 天", "岗位授权表、单位确认单、审批人清单", "厂长 + 产品"],
            ["1 原型试用", "已完成", "可运行 H5/PWA 演示、管理端演示", "产品 + 研发"],
            ["2 MVP 开发", "2 周", "小程序报工、订单/二维码、异常、个人统计", "研发"],
            ["3 管理端", "1 周", "概览、订单、人员矩阵、导出", "研发"],
            ["4 单班组试点", "1 周", "试点报告、问题清单、培训材料", "厂长 + 班组长"],
            ["5 双轨运行", "1 个月", "系统 vs 手工差异表、优化项", "生产 + 财务"],
            ["6 全员推广", "1 周", "全员账号、正式规则、月度归档", "厂长 + 管理员"],
        ],
        widths=[3.0, 2.2, 7.8, 3.5],
        font_size=8.4,
        first_col_bold=True,
        cap="表 41 实施阶段",
    )
    callout(
        doc,
        "不要跳过“双轨运行”",
        "系统上线第一个月，保留手工记录不是倒退，而是给员工和管理层一个对照。差异每天解释清楚，第二个月才能真正停掉手工账。",
        "blue",
    )

    h2(doc, "10.2 团队配置")
    add_table(
        doc,
        ["角色", "投入", "职责"],
        [
            ["产品/项目负责人", "0.5 人", "口径、流程、验收、跨部门协调"],
            ["后端", "1 人", "数据模型、API、权限、导出"],
            ["前端/小程序", "1 人", "工人端、管理端、离线队列"],
            ["测试/实施", "0.5 人", "用例、试点培训、数据核对"],
            ["关键用户", "2 人", "班组长 + 综合岗位各 1 人，参与试用"],
        ],
        widths=[4.0, 2.6, 9.9],
        font_size=8.6,
        first_col_bold=True,
        cap="表 42 团队配置",
    )

    h2(doc, "10.3 试点方案")
    bullet(doc, "选一个配合度高、工序完整的班组，最好包含写真和亚克力各一条线。", bold_lead="选点：")
    bullet(doc, "第 1 天现场跟班，记录员工实际动作、扫码位置、网络情况；第 2–3 天双轨录入。", bold_lead="跟班：")
    bullet(doc, "每天下班前 10 分钟对账，差异当天解释，不隔夜。", bold_lead="对账：")
    bullet(doc, "收集 3 类反馈：好不好用、准不准、愿不愿意继续用。", bold_lead="反馈：")
    bullet(doc, "试点结束给出“继续/调整/暂停”的明确结论，不无限期试用。", bold_lead="决策：")

    h2(doc, "10.4 培训与推行")
    add_table(
        doc,
        ["对象", "内容", "形式", "时长"],
        [
            ["员工", "扫码、输数量、看今日产量、申请更正", "现场演示 + 一页纸", "15 分钟"],
            ["班组长", "日结、差异排查、代报/补录", "小班培训", "30 分钟"],
            ["厂长", "概览、异常确认、订单、导出", "一对一", "45 分钟"],
            ["管理员", "人员技能、二维码、账号、备份", "操作手册 + 演练", "1 小时"],
        ],
        widths=[2.6, 7.3, 4.2, 2.4],
        font_size=8.5,
        first_col_bold=True,
        cap="表 43 培训计划",
    )

    h2(doc, "10.5 验收标准")
    add_table(
        doc,
        ["类别", "验收项", "标准"],
        [
            ["功能", "扫码报工", "10 个真实订单全部可扫；扫不出可手工输入"],
            ["功能", "上游校验", "同单位超报被转待确认；不同单位不误拦"],
            ["功能", "异常确认", "厂长可确认/驳回；状态与统计实时更新"],
            ["功能", "导出", "CSV 用 Excel 打开无乱码；字段完整"],
            ["性能", "报工响应", "P95 < 800ms；弱网有明确反馈"],
            ["数据", "日结对账", "连续 5 个工作日差异 < 2%"],
            ["体验", "报工耗时", "熟练员工中位数 < 15 秒"],
            [" adoption", "试点日活", "试点班组 ≥ 90% 员工每天使用"],
            ["安全", "权限", "员工无法查看他人明细；厂长无法删除记录"],
        ],
        widths=[2.2, 6.0, 8.3],
        font_size=8.3,
        first_col_bold=True,
        cap="表 44 验收标准",
    )

    h2(doc, "10.6 上线检查清单")
    for item in [
        "17 名员工账号、岗位、技能矩阵已确认并导入。",
        "10 个工序的单位、计划量、审批人已确认。",
        "流转卡二维码已打印并贴到实际流转卡上。",
        "试点班组完成 15 分钟培训，每人至少成功报工 3 笔。",
        "厂长/班组长会看概览、会处理异常、会导出。",
        "离线队列、重复提交、超报、冲销四条路径测试通过。",
        "每日备份、HTTPS、隐私政策、员工告知完成。",
        "双轨运行差异表已建立，责任人明确。",
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run("□  ")
        set_run_font(r, FONT_CN, 10, bold=True, color=BLUE)
        r = p.add_run(item)
        set_run_font(r, FONT_BODY, 10.2, color=INK)


def section_risk(doc):
    h1(doc, "11 风险、假设与待确认事项", page_break=True)
    h2(doc, "11.1 风险清单")
    add_table(
        doc,
        ["风险", "概率/影响", "应对"],
        [
            ["多能工跨线归属不清", "中/高", "报工时强制选产线；授权名单固定；统计按记录归属"],
            ["亚克力过胶兼岗不成立", "中/高", "现场确认；调整技能矩阵；不要默认放行"],
            ["计量单位口径错误", "高/高", "每个工序一张确认单；系统中单位可配置"],
            ["员工共用账号/代报", "中/高", "一人一号；设备绑定；代报留痕；抽查"],
            ["弱网导致漏记", "高/中", "离线队列；待同步标识；日结对账"],
            ["员工抵触“被监控”", "中/高", "只统产量；员工可见自己的全部记录；先试点"],
            ["二维码被复制", "中/中", "签名 token；订单完成失效；异常频次"],
            ["范围蔓延到工资/绩效", "高/中", "合同与验收明确边界；变更走评审"],
            ["小程序主体/备案延误", "中/中", "第 1 周启动；先用 H5 试点"],
            ["数据丢失", "低/高", "每日备份；对象存储版本；季度恢复演练"],
        ],
        widths=[5.0, 2.8, 8.7],
        font_size=8.2,
        first_col_bold=True,
        align_center=[1],
        cap="表 45 风险清单",
    )

    h2(doc, "11.2 待确认问题")
    add_table(
        doc,
        ["#", "问题", "影响", "责任人"],
        [
            ["1", "王坚、张知亮的全线授权是否覆盖所有班次？", "多能工顶岗范围", "厂长"],
            ["2", "亚克力过胶由过膜过板兼岗，还是另设？", "第 3 道无人可报", "厂长"],
            ["3", "排版按平方米、单还是件？", "统计口径与员工预期", "厂长/财务"],
            ["4", "写真裁切按平方米还是件？", "同上", "厂长/财务"],
            ["5", "综合岗位跨线时如何分摊产线？", "双线统计归属", "厂长"],
            ["6", "是否允许班组长代报？谁审批？", "数据真实性与效率", "厂长"],
            ["7", "一个订单是否会同时包含两条线？", "是否拆任务", "业务"],
            ["8", "历史纸质/Excel 数据是否要导入？", "期初余额与对账", "财务"],
            ["9", "小程序主体、域名、备案是否就绪？", "上线时间", "行政/IT"],
            ["10", "车间网络与手机设备情况？", "离线与相机方案", "IT"],
        ],
        widths=[0.9, 8.4, 5.0, 2.2],
        font_size=8.2,
        first_col_bold=True,
        align_center=[0],
        cap="表 46 待确认问题",
    )

    h2(doc, "11.3 设计决策记录（ADR）")
    add_table(
        doc,
        ["编号", "决策", "理由", "替代方案"],
        [
            ["ADR-01", "订单按产线拆生产任务", "双线独立统计；避免跨线污染", "订单直接带 line_type（无法处理跨线单）"],
            ["ADR-02", "每条记录保存独立单位", "平方米/件/套不可互换", "统一换算（会造假）"],
            ["ADR-03", "超报转待确认，不硬拦", "现场有补印/返工/分批", "硬拦截（逼员工改数）"],
            ["ADR-04", "记录不可删除，只冲销", "可追溯、可复核", "允许管理员改数（无法审计）"],
            ["ADR-05", "微信小程序优先", "扫码/离线/低门槛", "原生 App（成本高）"],
            ["ADR-06", "本期不做工资/绩效", "边界清晰，降低信任成本", "一体化（范围失控）"],
        ],
        widths=[1.8, 5.2, 5.7, 3.8],
        font_size=8.2,
        first_col_bold=True,
        cap="表 47 设计决策记录",
    )

    h2(doc, "11.4 结论与建议")
    para(doc, "这套系统在技术和交互上都不复杂，真正的难点在“口径”和“推行”。建议先用配套的可运行演示，让厂长、班组长和 2–3 名一线员工实际点一遍；把“谁做哪道工序、按什么单位、超报谁批”这三件事定下来，再进入开发。")
    para(doc, "如果只能先做一件事，就把「扫码报工 + 今日个人产量 + 厂长异常确认」做出来。它最能建立信任，也最能暴露流程问题。")


def appendix(doc):
    h1(doc, "附录 A 演示账号与运行", page_break=True)
    add_table(
        doc,
        ["账号", "岗位", "可体验"],
        [
            ["肖宏", "写真/异型（打印）", "写真打印、超报待确认"],
            ["王坤", "裁切（激光切割）", "亚克力裁切"],
            ["梁建华", "过膜过板", "写真覆膜、亚克力过胶"],
            ["肖尾珍", "综合岗位", "双线综合"],
            ["李厂长", "厂长/管理员", "管理端全部功能"],
        ],
        widths=[3.0, 5.0, 8.5],
        font_size=8.8,
        first_col_bold=True,
        cap="表 48 演示账号",
    )
    para(doc, "运行方式：双击 D:\\工厂个人计件软件\\启动计件通.bat，电脑访问 http://127.0.0.1:8787；手机与电脑同一 Wi-Fi，访问启动窗口显示的局域网地址。")
    para(doc, "演示数据保存在浏览器 localStorage；可在管理端「报表导出 → 恢复演示数据」重置。正式版需要后端与数据库，不能把演示数据当生产数据。")

    h1(doc, "附录 B 17 人岗位矩阵", page_break=True)
    headers = ["姓名", "写真排版", "写真打印", "写真覆膜", "写真裁切", "写真综合", "亚克力排图", "UV打印", "亚克力过胶", "亚克力裁切", "亚克力综合"]
    rows = []
    for e in [
        ("肖尾珍", "综合岗位", {"综合": True}),
        ("余道京", "综合岗位", {"综合": True}),
        ("陈根华", "综合岗位", {"综合": True}),
        ("王坤", "裁切（激光切割）", {"亚克力裁切": True}),
        ("王坚", "多能工", {"all": True}),
        ("刘浩", "裁切（激光切割）", {"写真裁切": True, "亚克力裁切": True}),
        ("张知亮", "多能工", {"all": True}),
        ("邓强", "UV打印", {"UV打印": True}),
        ("梁建华", "过膜过板", {"写真覆膜": True, "亚克力过胶": True}),
        ("刘绍珍", "过膜过板", {"写真覆膜": True, "亚克力过胶": True}),
        ("胡汝奇", "亚克力排图", {"亚克力排图": True}),
        ("喻宏伟", "亚克力排图", {"亚克力排图": True}),
        ("肖宏", "写真/异型（打印）", {"写真打印": True}),
        ("周艳红", "综合岗位", {"综合": True}),
        ("钟发兰", "综合岗位", {"综合": True}),
        ("朱宗耀", "写真/异型（排版）", {"写真排版": True}),
        ("黄伟", "裁切（激光切割）", {"写真裁切": True, "亚克力裁切": True}),
    ]:
        name, role, skills = e
        row = [name]
        for key in ["写真排版", "写真打印", "写真覆膜", "写真裁切", "写真综合", "亚克力排图", "UV打印", "亚克力过胶", "亚克力裁切", "亚克力综合"]:
            if skills.get("all") or key in skills:
                row.append("✓")
            elif skills.get("综合") and key.endswith("综合"):
                row.append("✓")
            else:
                row.append("—")
        rows.append(row)
    add_table(doc, headers, rows, widths=[1.8] + [1.47] * 10, font_size=7.4, align_center=list(range(1, 11)), cap="表 49 17 人 × 10 工序技能矩阵（演示版映射）")
    para(doc, "注：王坚、张知亮为双线全线多能工；黄伟、刘浩兼写真/亚克力裁切；亚克力过胶由过膜过板兼岗，属于业务假设。正式版仍应由厂长逐人授权并留档。", size=9, color=MUTED)

    h1(doc, "附录 C 术语表", page_break=True)
    add_table(
        doc,
        ["术语", "解释"],
        [
            ["流转卡", "随实物一起流转的纸质卡，印有二维码，用于扫码报工"],
            ["生产任务 Job", "订单按产线拆分后的生产单元，一条产线一个任务"],
            ["工序步骤 JobStep", "任务下的五道工序配置，含单位与计划量"],
            ["报工记录 Record", "某人某任务某工序的一次完成，含数量、单位、时间"],
            ["上游已转", "上一道工序已确认的完成量，用于限制下游可报数量"],
            ["冲销", "对已计入记录的更正，保留原记录并新增一条冲销记录"],
            ["幂等键", "客户端生成的唯一 ID，保证重复提交不会产生第二条记录"],
            ["P95", "95% 的请求耗时低于该值"],
            ["RBAC", "基于角色的访问控制"],
            ["CSV", "逗号分隔值文件，Excel 可直接打开"],
        ],
        widths=[3.5, 13.0],
        font_size=8.5,
        first_col_bold=True,
        cap="表 50 术语表",
    )
    para(doc, "参考：①《工厂计件统计软件设计方案（双线五工序）》；② 17 人花名册截图；③ 计件通可运行 MVP。", size=8.5, color=MUTED)


# ------------------------------------------------------------------
# 构建
# ------------------------------------------------------------------
def main():
    doc = Document()
    setup_page(doc)
    setup_styles(doc)
    doc.core_properties.title = "工厂个人计件统计软件 · 手机端产品与系统设计方案"
    doc.core_properties.author = "计件通项目组"
    doc.core_properties.subject = "双线五工序计件统计"
    doc.core_properties.keywords = "计件, 工序, 手机端, 小程序, 工厂"

    cover(doc)
    document_info(doc)
    executive_summary(doc)
    section_background(doc)
    section_field(doc)
    section_product(doc)
    section_flow(doc)
    section_mobile(doc)
    section_trust(doc)
    section_data(doc)
    section_tech(doc)
    section_reports(doc)
    section_plan(doc)
    section_risk(doc)
    appendix(doc)

    doc.save(OUT)
    print("saved", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
