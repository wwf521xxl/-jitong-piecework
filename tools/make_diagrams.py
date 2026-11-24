# -*- coding: utf-8 -*-
"""生成设计方案中的流程、架构和数据模型示意图。"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"D:\工厂个人计件软件\docs\diagrams")
OUT.mkdir(parents=True, exist_ok=True)

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def center_text(draw, box, text, fnt, fill):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x1 + (x2 - x1 - tw) / 2 - bbox[0], y1 + (y2 - y1 - th) / 2 - bbox[1]), text, font=fnt, fill=fill)


def arrow(draw, x1, y1, x2, y2, color="#9DB0C6", width=3):
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    # 箭头头部
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 12
    for sign in (-1, 1):
        draw.line((x2, y2, x2 - size * math.cos(angle + sign * 0.5), y2 - size * math.sin(angle + sign * 0.5)), fill=color, width=width)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


# ============================================================
# 图 1：双线五工序与数据主线
# ============================================================
def flow_diagram():
    W, H = 1600, 850
    img = Image.new("RGB", (W, H), "#F4F6F9")
    d = ImageDraw.Draw(img)
    d.text((70, 54), "双线五工序：一张流转卡走完生产全流程", font=font(42, True), fill="#10233C")
    d.text((72, 112), "订单是起点，流转卡是载体，报工记录是唯一事实来源", font=font(21), fill="#718096")

    steps = [
        ("订单接入", "淘宝 / 线下 / 客户", "#EAF2FF", "#1467E8"),
        ("拆生产任务", "按写真 / 亚克力拆", "#EAF2FF", "#1467E8"),
        ("生成流转卡", "二维码 + 订单信息", "#E8F8F0", "#067647"),
        ("扫码报工", "手机 3 步完成", "#FFF4E5", "#B25A00"),
        ("异常确认", "超报 / 补录 / 冲销", "#FFF0F0", "#B42318"),
        ("统计与导出", "日报 / 月报 / Excel", "#F1EDFF", "#5B3FD6"),
    ]
    x, y, w, h, gap = 58, 180, 220, 108, 29
    boxes = []
    for i, (title, sub, bg, fg) in enumerate(steps):
        bx = x + i * (w + gap)
        rounded(d, (bx, y, bx + w, y + h), 18, "#FFFFFF", "#E7ECF2", 2)
        d.rounded_rectangle((bx, y, bx + 7, y + h), radius=3, fill=fg)
        d.text((bx + 24, y + 22), title, font=font(23, True), fill="#10233C")
        d.text((bx + 24, y + 58), sub, font=font(15), fill="#718096")
        boxes.append((bx, y, bx + w, y + h))
        if i < len(steps) - 1:
            arrow(d, bx + w + 4, y + h / 2, bx + w + gap - 6, y + h / 2)

    # 双线流程
    panel_y = 355
    rounded(d, (56, panel_y, W - 56, H - 92), 22, "#FFFFFF", "#E7ECF2", 2)
    d.text((86, panel_y + 30), "两条产线，各自五道工序，数据在底层隔离", font=font(24, True), fill="#10233C")
    d.text((1190, panel_y + 35), "第 5 道综合岗位可跨线", font=font(16), fill="#718096")

    lanes = [
        ("写真线", "#1467E8", "#EAF2FF", ["排版", "打印", "过版覆膜", "裁切", "综合"]),
        ("亚克力线", "#F79009", "#FFF4E5", ["排图", "UV打印", "过胶", "裁切", "综合"]),
    ]
    for li, (lane, color, soft, names) in enumerate(lanes):
        ly = panel_y + 100 + li * 160
        rounded(d, (86, ly, 238, ly + 72), 13, color)
        center_text(d, (86, ly, 238, ly + 72), lane, font(25, True), "#FFFFFF")
        for i, name in enumerate(names):
            bx = 280 + i * 244
            bw = 205
            rounded(d, (bx, ly, bx + bw, ly + 72), 13, soft if i < 4 else "#F1EDFF", None)
            center_text(d, (bx, ly, bx + bw, ly + 72), f"{i + 1}  {name}", font(22, True), color if i < 4 else "#5B3FD6")
            if i < 4:
                arrow(d, bx + bw + 5, ly + 36, bx + 240, ly + 36, "#C9D6E5")

    d.text((86, H - 72), "每条记录固定包含：订单 / 产线 / 工序 / 员工 / 数量 / 单位 / 时间 / 设备", font=font(18), fill="#526173")
    d.rounded_rectangle((1180, H - 84, W - 86, H - 40), radius=10, fill="#0B1F33")
    center_text(d, (1180, H - 84, W - 86, H - 40), "只统计件数，不算工资", font(17, True), "#FFFFFF")

    img.save(OUT / "flow.png", quality=95)


# ============================================================
# 图 2：技术架构
# ============================================================
def architecture_diagram():
    W, H = 1600, 920
    img = Image.new("RGB", (W, H), "#F4F6F9")
    d = ImageDraw.Draw(img)
    d.text((70, 50), "推荐技术架构：手机端优先，离线可用，数据可审计", font=font(40, True), fill="#10233C")
    d.text((72, 108), "微信小程序承载工人端；管理端使用响应式 Web；后端保持轻量、可扩展", font=font(20), fill="#718096")

    # 客户端层
    d.text((72, 170), "客户端", font=font(20, True), fill="#526173")
    client = [
        ("微信小程序", "工人扫码报工\n相机 / 离线队列", "#EAF2FF", "#1467E8"),
        ("管理后台", "Vue 3 + Vite\n订单 / 异常 / 报表", "#E8F8F0", "#067647"),
        ("H5 / PWA 备用", "低门槛试用\n无需安装", "#FFF4E5", "#B25A00"),
    ]
    for i, (title, sub, bg, fg) in enumerate(client):
        bx = 200 + i * 410
        rounded(d, (bx, 160, bx + 360, 286), 16, bg, None)
        d.text((bx + 24, 182), title, font=font(24, True), fill=fg)
        d.multiline_text((bx + 24, 222), sub, font=font(16), fill="#526173", spacing=6)

    # 接入层
    rounded(d, (180, 326, 1420, 410), 16, "#0B1F33")
    d.text((210, 348), "统一接入", font=font(19, True), fill="#FFFFFF")
    items = ["HTTPS / TLS", "微信登录 / 手机号", "JWT + RBAC", "幂等键", "限流与审计"]
    for i, item in enumerate(items):
        d.text((460 + i * 175, 350), item, font=font(16), fill="#D7E4F1")
    d.text((460, 380), "所有请求带设备号与客户端记录 UUID；重复提交不会产生第二条记录", font=font(14), fill="#8FA9C2")

    # 服务层
    d.text((72, 448), "服务层", font=font(20, True), fill="#526173")
    services = [
        ("报工服务", "技能校验 / 上游校验\n超报转确认 / 冲销"),
        ("订单与流转卡", "订单拆任务 / 二维码\n打印 / 补发 / 作废"),
        ("规则与风控", "重复检测 / 异常规则\n设备与频次"),
        ("统计报表", "日报 / 月报 / 工序\nCSV / Excel"),
        ("人员权限", "员工 / 技能矩阵\n角色 / 审批"),
        ("文件服务", "现场照片 / 附件\n对象存储"),
    ]
    for i, (title, sub) in enumerate(services):
        col, row = i % 3, i // 3
        bx = 200 + col * 410
        by = 438 + row * 130
        rounded(d, (bx, by, bx + 360, by + 108), 14, "#FFFFFF", "#E7ECF2", 2)
        d.text((bx + 20, by + 18), title, font=font(21, True), fill="#10233C")
        d.multiline_text((bx + 20, by + 54), sub, font=font(14), fill="#718096", spacing=4)

    # 数据层
    d.text((72, 740), "数据层", font=font(20, True), fill="#526173")
    data = [("PostgreSQL", "主数据 / 流水 / 审计", "#EAF2FF"), ("Redis", "幂等 / 缓存 / 限流", "#FFF4E5"), ("对象存储", "照片 / 导出文件", "#E8F8F0"), ("备份", "每日全量 + 日志", "#F1EDFF")]
    for i, (title, sub, bg) in enumerate(data):
        bx = 200 + i * 305
        rounded(d, (bx, 728, bx + 278, 830), 13, bg, None)
        d.text((bx + 18, 746), title, font=font(20, True), fill="#10233C")
        d.text((bx + 18, 782), sub, font=font(14), fill="#526173")

    # 离线说明
    rounded(d, (1340, 170, 1530, 286), 14, "#FFFFFF", "#F7D49A", 2)
    d.text((1356, 186), "弱网可用", font=font(18, True), fill="#B25A00")
    d.multiline_text((1356, 220), "本地队列\n联网重放\n服务端幂等", font=font(14), fill="#8A5A18", spacing=4)
    img.save(OUT / "architecture.png", quality=95)


# ============================================================
# 图 3：数据模型
# ============================================================
def data_model_diagram():
    W, H = 1600, 940
    img = Image.new("RGB", (W, H), "#F4F6F9")
    d = ImageDraw.Draw(img)
    d.text((70, 46), "核心数据模型：订单 → 生产任务 → 工序 → 报工记录", font=font(39, True), fill="#10233C")
    d.text((72, 102), "一条报工记录只属于一个生产任务的一道工序；所有更正都通过冲销记录完成", font=font(19), fill="#718096")

    def box(x, y, w, h, name, fields, color="#1467E8", soft="#EAF2FF"):
        rounded(d, (x, y, x + w, y + h), 14, "#FFFFFF", "#E2E9F1", 2)
        d.rounded_rectangle((x, y, x + w, y + 42), radius=12, fill=soft)
        d.rectangle((x, y + 26, x + w, y + 42), fill=soft)
        d.text((x + 16, y + 9), name, font=font(18, True), fill=color)
        d.multiline_text((x + 16, y + 54), fields, font=font(13), fill="#526173", spacing=5)

    box(70, 180, 270, 200, "production_order", "order_no\ncustomer\nplatform\nstatus\ndue_date", "#5B3FD6", "#F1EDFF")
    box(410, 180, 300, 230, "production_job", "job_id\norder_id\nline_type\nproduct / spec\nplanned_qty / unit\nqr_token\nstatus", "#1467E8", "#EAF2FF")
    box(780, 180, 280, 220, "job_step", "job_id\nstep_no 1-5\nunit\nplanned_qty\ncompleted_qty\nstatus", "#067647", "#E8F8F0")
    box(1130, 180, 350, 260, "piece_record", "record_id\njob_id / step_no\nemployee_id\nqty DECIMAL(12,3)\nunit\nstatus: valid/pending/void\nidempotency_key\nrecord_time", "#B25A00", "#FFF4E5")

    box(410, 500, 300, 200, "employee", "employee_id\nname / phone\nrole\nstatus\nwechat_openid", "#1467E8", "#EAF2FF")
    box(780, 500, 280, 200, "employee_skill", "employee_id\nline_type\nstep_no\neffective_from\napproved_by", "#067647", "#E8F8F0")
    box(1130, 500, 350, 200, "record_correction", "correction_id\nrecord_id\nreason\ndelta / action\nrequested_by\napproved_by\nstatus", "#B42318", "#FFF0F0")
    box(70, 500, 270, 200, "audit_log", "event_id\nactor / action\nentity / before\nafter / ip\ndevice / time", "#5B3FD6", "#F1EDFF")

    # 连线
    arrow(d, 340, 260, 404, 260, "#9DB0C6")
    arrow(d, 710, 260, 774, 260, "#9DB0C6")
    arrow(d, 1060, 260, 1124, 260, "#9DB0C6")
    arrow(d, 560, 410, 560, 494, "#9DB0C6")
    arrow(d, 710, 560, 774, 560, "#9DB0C6")
    arrow(d, 1060, 600, 1124, 600, "#9DB0C6")
    d.line((1305, 440, 1305, 500), fill="#9DB0C6", width=3)
    d.line((70 + 135, 500, 1305, 440), fill="#C9D6E5", width=2)

    # 说明
    rounded(d, (70, 770, 1530, 880), 14, "#FFFFFF", "#E7ECF2", 2)
    d.text((94, 790), "关键约束", font=font(19, True), fill="#10233C")
    d.text((94, 826), "① 一个订单可拆多个生产任务，但每个任务只属于一条产线；② 数量使用 DECIMAL，禁止浮点；③ 每条记录保存独立单位；④ 记录不物理删除，冲销与更正在 correction/audit 中留痕。", font=font(14), fill="#526173")
    img.save(OUT / "data-model.png", quality=95)


if __name__ == "__main__":
    flow_diagram()
    architecture_diagram()
    data_model_diagram()
    print("diagrams written:", [p.name for p in OUT.glob("*.png")])
