#!/usr/bin/env python3
"""
Travel Invoice - 出差发票自动整理脚本
扫描邮箱 → 下载附件 → 打包 PDF → 发送

依赖: himalaya, reportlab, PyPDF2
"""

import json
import os
import re
import sys
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
HIMALAYA_BIN = os.path.expanduser("~/.local/bin/himalaya")
TEMP_DIR = tempfile.mkdtemp(prefix="travel_invoice_")
OUTPUT_PDF = os.path.join(TEMP_DIR, "出差发票汇总.pdf")

# 邮件配置
MY_EMAIL = os.environ.get("MY_EMAIL", "{{MY_EMAIL}}")

# 搜索关键词配置
KEYWORDS = {
    "hotel": ["酒店", "住宿", "酒店预订", "如家", "汉庭", "7天", "维也纳", "全季", "希尔顿", "万豪", "洲际", "喜来登", "凯悦", "香格里拉", "民宿", "公寓"],
    "train": ["高铁", "火车", "动车", "铁路", "12306", "电子发票"],
    "airline": ["航空", "机票", "航班", "国航", "东航", "南航", "厦航"],
    "taxi": ["高德", "打车", "滴滴", "出租"],
}

EXCLUDE_KEYWORDS = ["作废", "红字", "退货", "退款", "支付通知", "退票通知", "改签通知", "候补订单", "兑现成功"]


def run_command(cmd, capture=True, shell=False):
    """执行 shell 命令"""
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=60,
            shell=shell
        )
        return result.stdout if capture else ""
    except Exception as e:
        print(f"命令执行失败: {cmd}, 错误: {e}")
        return ""


def get_recent_emails(days=90, page_size=500):
    """获取近 N 天的邮件"""
    print(f"📬 扫描近 {days} 天的邮件...")

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 使用 plain 格式输出（JSON 格式可能有问题）
    # page-size 500 覆盖所有邮件，避免分页丢失发票
    cmd = [
        HIMALAYA_BIN, "envelope", "list",
        "--page", "1",
        "--page-size", str(page_size),
        "--output", "plain"
    ]

    output = run_command(cmd)
    if not output:
        print("⚠️ 无法获取邮件列表")
        return []

    # 解析 plain 格式: | ID | FLAGS | SUBJECT | FROM | DATE |
    emails = []
    for line in output.strip().split("\n"):
        # 跳过表头和空行
        if "|" not in line or "ID" in line or "---" in line:
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            email_id = parts[1].strip()
            subject = parts[3].strip()
            sender = parts[4].strip()  # 发件人
            date_str = parts[5].strip()

            # 解析日期
            try:
                # 格式: 2026-04-21 14:34+00:00
                email_date = datetime.fromisoformat(date_str.replace("+00:00", "").replace(" ", "T"))
                # 检查是否在日期范围内
                if start_date <= email_date <= end_date:
                    emails.append({
                        "id": email_id,
                        "subject": subject,
                        "sender": sender,
                        "date": date_str
                    })
            except:
                # 解析失败，保留邮件
                emails.append({
                    "id": email_id,
                    "subject": subject,
                    "sender": sender,
                    "date": date_str
                })

    print(f"📬 共获取 {len(emails)} 封邮件")
    return emails


def match_invoice_email(subject, sender=None):
    """判断邮件是否为发票相关，只看标题"""
    if not subject:
        return None

    # 排除词（非发票的通用通知）
    for ex in EXCLUDE_KEYWORDS:
        if ex in subject:
            return None

    # 按优先级匹配：先匹配特定类型（打车 > 酒店 > 航空），再匹配通用词
    # 高德打车优先（因为标题可能也含"发票"等通用词）
    for kw in KEYWORDS["taxi"]:
        if kw in subject:
            return "taxi"

    # 酒店
    for kw in KEYWORDS["hotel"]:
        if kw in subject:
            return "hotel"

    # 航空
    for kw in KEYWORDS["airline"]:
        if kw in subject:
            return "airline"

    # 高铁最后匹配（"电子发票"等通用词放这里）
    # 检查发件人是否包含 12306
    sender_lower = sender.lower() if sender else ""
    if "12306" in sender_lower or "rails.com.cn" in sender_lower:
        return "train"

    for kw in KEYWORDS["train"]:
        if kw in subject:
            return "train"

    return None


def scan_invoices():
    """扫描发票邮件"""
    print("\n🔍 开始扫描发票邮件...")

    emails = get_recent_emails(days=90)

    # 分类结果
    categorized = {
        "hotel": [],
        "train": [],
        "airline": [],
        "taxi": [],
        "other": []
    }

    type_names = {
        "hotel": "🏨 酒店",
        "train": "🚄 高铁",
        "airline": "✈️ 航空",
        "taxi": "🚕 高德打车"
    }

    matched_count = 0

    for email in emails:
        subject = email.get("subject", "")
        sender = email.get("sender", "")
        email_id = email.get("id", "")
        date = email.get("date", "")

        inv_type = match_invoice_email(subject, sender)

        if inv_type:
            matched_count += 1
            if inv_type in categorized:
                categorized[inv_type].append({
                    "id": email_id,
                    "subject": subject,
                    "date": date
                })
            print(f"  ✅ [{type_names.get(inv_type, inv_type)}] {subject[:50]}")

    # 打印统计
    print(f"\n📊 扫描结果:")
    for inv_type, items in categorized.items():
        if items:
            print(f"  {type_names.get(inv_type, inv_type)}: {len(items)} 封")

    total = sum(len(v) for v in categorized.values())
    print(f"\n共发现 {total} 封发票邮件")

    return categorized


def download_attachments(emails, inv_type):
    """下载附件"""
    if not emails:
        return []

    print(f"\n📥 下载 {inv_type} 附件...")

    type_dir = os.path.join(TEMP_DIR, inv_type)
    os.makedirs(type_dir, exist_ok=True)

    downloaded = []

    for email in emails[:10]:  # 限制每个类型最多 10 封
        email_id = email.get("id", "")
        subject = email.get("subject", "")

        # 下载附件到指定目录
        cmd = f"{HIMALAYA_BIN} attachment download -d {type_dir} {email_id}"
        result = run_command(cmd)

        if result and "Downloaded" in result:
            # 查找下载的文件
            files = os.listdir(type_dir)
            new_files = [f for f in files if f.endswith(('.pdf', '.PDF', '.jpg', '.jpeg', '.png', '.zip', '.ofd'))]
            downloaded.append({
                "email_id": email_id,
                "subject": subject,
                "dir": type_dir,
                "files": new_files
            })
            print(f"  ✅ {subject[:40]} - {len(new_files)} 个文件")
        else:
            print(f"  ⚠️ {subject[:40]} - 无附件或下载失败")

    return downloaded


def crop_itinerary_pdf(pdf_path):
    """裁剪高德行程单 PDF，用 PyPDF2 修改 CropBox 去掉广告和页码，保持原始矢量内容
    
    原始行程单 A4 页面(595x842pt)布局:
    - 0~665pt: 广告banner (去掉)
    - 665~460pt: 标题+信息+表格 (保留)
    - 460~0pt: 空白+页码 (去掉)
    
    PDF坐标系从左下角开始，y轴向上。像素坐标从上到下，
    经精确测量: 广告结束≈像素y=534→PDF y=665, 表格结束≈像素y=1018→PDF y=460
    
    Args:
        pdf_path: 原始行程单 PDF 路径
    
    Returns:
        裁剪后的 PDF 路径（原地覆盖）
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        run_command("pip install PyPDF2")
        from PyPDF2 import PdfReader, PdfWriter

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        mb = page.mediabox
        orig_h = float(mb.height)
        orig_w = float(mb.width)
        
        # 精确裁剪坐标 (基于 A4 595x842 行程单实测)
        if abs(orig_h - 842) < 10:  # 标准 A4 行程单
            page.cropbox.lower_left = (0, 460)
            page.cropbox.upper_right = (orig_w, 665)
        else:
            # 非标准尺寸，按比例裁剪
            top_ratio = 665 / 842   # ≈0.79
            bottom_ratio = 460 / 842  # ≈0.55
            page.cropbox.lower_left = (0, orig_h * bottom_ratio)
            page.cropbox.upper_right = (orig_w, orig_h * top_ratio)
        
        writer.add_page(page)
    
    # 原地覆盖
    with open(pdf_path, "wb") as f:
        writer.write(f)
    
    print(f"  ✂️ 已裁剪行程单: {os.path.basename(pdf_path)}")
    return pdf_path


def create_pdf_report(categorized):
    """生成 PDF 报告 — 行程单用 CropBox 裁剪去广告，其他发票直接合并，全部保持原始矢量 PDF"""
    print("\n📄 合并 PDF 报告...")

    # 收集所有 PDF 文件路径，按类型排序
    pdf_pages = []  # [(pdf_path, inv_type, subject), ...]

    type_order = ["taxi", "hotel", "airline", "train"]
    type_names = {
        "hotel": "🏨 酒店",
        "train": "🚄 高铁",
        "airline": "✈️ 航空",
        "taxi": "🚕 高德打车"
    }

    for inv_type in type_order:
        emails = categorized.get(inv_type, [])
        if not emails:
            continue

        type_dir = os.path.join(TEMP_DIR, inv_type)
        if not os.path.isdir(type_dir):
            continue

        # 收集该类型下的所有 PDF 文件
        # 先解压 zip 附件（12306 高铁发票是 zip 包含 pdf+ofd）
        for f in sorted(os.listdir(type_dir)):
            fpath = os.path.join(type_dir, f)
            if f.lower().endswith('.zip') and os.path.isfile(fpath):
                import zipfile
                try:
                    with zipfile.ZipFile(fpath, 'r') as zf:
                        for member in zf.namelist():
                            if member.lower().endswith('.pdf'):
                                zf.extract(member, type_dir)
                                print(f"  📦 解压: {member} <- {f}")
                except Exception as e:
                    print(f"  ⚠️ 解压失败 {f}: {e}")

        for f in sorted(os.listdir(type_dir)):
            fpath = os.path.join(type_dir, f)
            if f.lower().endswith('.pdf') and os.path.isfile(fpath):
                # 酒店排除结账单（只保留正式发票）
                if inv_type == "hotel" and "结账单" in f:
                    print(f"  ⏭️ 跳过结账单: {f}")
                    continue
                # 高德行程单：用 CropBox 裁剪去广告
                if inv_type == "taxi" and "行程单" in f:
                    crop_itinerary_pdf(fpath)
                pdf_pages.append((fpath, inv_type, f))

    # 高德打车: 确保发票+行程单配对（相邻排列）
    # 文件名一般: 电子发票.pdf / 电子行程单.pdf，已按文件名排序

    if not pdf_pages:
        print("⚠️ 没有找到 PDF 附件")
        return None

    # 用 qpdf 直接合并所有 PDF 页面
    page_args = [p[0] for p in pdf_pages]
    
    # 检查 qpdf 是否可用
    qpdf_check = run_command(["which", "qpdf"])
    
    if qpdf_check.strip():
        print(f"  使用 qpdf 合并 {len(page_args)} 个 PDF...")
        cmd = ["qpdf", "--empty", "--pages"] + page_args + ["--", OUTPUT_PDF]
        result = run_command(cmd)
        
        if os.path.exists(OUTPUT_PDF) and os.path.getsize(OUTPUT_PDF) > 0:
            print(f"✅ PDF 已生成: {OUTPUT_PDF}")
            for inv_type in type_order:
                count = sum(1 for p in pdf_pages if p[1] == inv_type)
                if count:
                    print(f"  {type_names.get(inv_type, inv_type)}: {count} 个文件")
            return OUTPUT_PDF
    
    # qpdf 不可用或失败，用 PyPDF2 备选
    print("  qpdf 不可用，使用 PyPDF2 合并...")
    try:
        from PyPDF2 import PdfMerger
    except ImportError:
        run_command("pip install PyPDF2")
        from PyPDF2 import PdfMerger

    merger = PdfMerger()
    for fpath, inv_type, fname in pdf_pages:
        try:
            merger.append(fpath)
        except Exception as e:
            print(f"  ⚠️ 跳过 {fname}: {e}")

    merger.write(OUTPUT_PDF)
    merger.close()

    if os.path.exists(OUTPUT_PDF):
        print(f"✅ PDF 已生成: {OUTPUT_PDF}")
        for inv_type in type_order:
            count = sum(1 for p in pdf_pages if p[1] == inv_type)
            if count:
                print(f"  {type_names.get(inv_type, inv_type)}: {count} 个文件")
        return OUTPUT_PDF
    
    return None


def send_email(pdf_path):
    """发送邮件（需用户确认后调用）"""
    print(f"\n📤 发送邮件到 {MY_EMAIL}...")

    # 读取 PDF 文件
    with open(pdf_path, "rb") as f:
        import base64
        pdf_data = base64.b64encode(f.read()).decode('ascii')

    # 使用 himalaya 发送
    subject = f"出差发票汇总 {datetime.now().strftime('%Y-%m-%d')}"

    # 构建 MML 格式邮件 (纯 ASCII 更安全)
    mml_content = f"""From: {MY_EMAIL}
To: {MY_EMAIL}
Subject: {subject}
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset=utf-8

Hi,

Attached is your travel invoice summary for the past 90 days.

---
Travel Invoice Plugin

--boundary123
Content-Type: application/pdf; name="travel_invoice_summary.pdf"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="travel_invoice_summary.pdf"

{pdf_data}

--boundary123--
"""

    # 写入临时文件
    mml_path = os.path.join(TEMP_DIR, "email.mml")
    with open(mml_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(mml_content)

    # 发送 (使用 shell 模式支持 pipe)
    cmd = f"cat {mml_path} | {HIMALAYA_BIN} template send"
    result = run_command(cmd, shell=True)

    if result and ("sent" in result.lower() or "success" in result.lower() or "done" in result.lower()):
        print(f"✅ 邮件已发送!")
        return True
    else:
        # 邮件发送失败，但PDF已生成
        print(f"⚠️ 邮件发送失败，PDF 已保存到: {pdf_path}")
        return False


def cleanup():
    """清理临时文件"""
    import shutil
    try:
        shutil.rmtree(TEMP_DIR)
        print(f"🧹 已清理临时文件")
    except:
        pass


def main():
    """主流程：扫描 → 生成 PDF → 等待用户确认 → 发送
    
    mode:
      - "scan": 只扫描+生成PDF，不发送（默认，需用户确认后再单独调用发送）
      - "send": 读取上次扫描结果并发送邮件
      - "full": 扫描+生成+发送（仅当用户明确确认后使用）
    """
    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"

    print("=" * 50)
    print("✈️  Travel Invoice - 出差发票自动整理")
    print("=" * 50)

    try:
        if mode == "send":
            # 单独发送模式：需要指定 PDF 路径
            if len(sys.argv) < 3:
                print("❌ 发送模式需要指定 PDF 路径: travel_invoice.py send <pdf_path>")
                return
            pdf_path = sys.argv[2]
            if not os.path.exists(pdf_path):
                print(f"❌ PDF 文件不存在: {pdf_path}")
                return
            send_email(pdf_path)
            cleanup()
            return

        # mode == "scan" 或 "full"
        # 1. 扫描发票邮件
        categorized = scan_invoices()

        total = sum(len(v) for v in categorized.values())

        if total == 0:
            print("\n❌ 未发现任何发票邮件")
            print("💡 提示: 请确保邮件主题包含以下关键词:")
            print("   酒店、高铁、航空、高德打车 等")
            return

        # 2. 下载附件
        for inv_type in categorized:
            if categorized[inv_type]:
                download_attachments(categorized[inv_type], inv_type)

        # 3. 生成 PDF
        pdf_path = create_pdf_report(categorized)

        # 输出 PDF 路径供外部读取
        print(f"\n📎 PDF 文件路径: {pdf_path}")
        print(f"📋 请确认后再发送")

        if mode == "full":
            # 用户已确认，直接发送
            send_email(pdf_path)
        
        # scan 模式：不清理临时文件，保留 PDF 供用户查看
        if mode == "scan":
            print(f"💡 确认后请说「发送」，或运行: python3 {os.path.abspath(__file__)} send {pdf_path}")

        print("\n" + "=" * 50)
        print("✅ 处理完成!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
