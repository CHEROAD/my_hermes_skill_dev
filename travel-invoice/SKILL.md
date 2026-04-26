---
name: travel-invoice
description: 自动扫描邮箱中出差发票（酒店、高铁、航空、高德打车），提取附件并打包成 PDF 发送给自己
version: 1.1.0
author: user
license: MIT
metadata:
  hermes:
    tags: [Email, PDF, Invoice, Travel, Automation, Productivity]
prerequisites:
  commands: [himalaya]
  python_packages: [reportlab, PyPDF2]
---

# Travel Invoice - 出差发票自动整理

自动扫描 QQ 邮箱中近 2 个月的出差发票邮件，提取附件并打包成 PDF 发送给自己。

## 功能

- 🔍 扫描含以下关键词的邮件：酒店、高铁、航空、高德打车
- 📎 提取发票 PDF/图片附件
- 📄 打包成单个 PDF 文件
- 📧 发送到自己邮箱

## 关键词配置

| 类型 | 搜索关键词 |
|------|-----------|
| 酒店 | 酒店、住宿、希尔顿、万豪、洲际、喜来登、凯悦、香格里拉、华住、如家、汉庭、7天、维也纳、全季、民宿、公寓 |
| 高铁 | 高铁、火车、动车、12306、铁路、网上购票 |
| 航空 | 航空、机票、航班、国航、东航、南航、厦航 |
| 高德 | 高德、打车、滴滴 |

**排除词**：作废、红字、退货、退款、支付通知、退票通知、改签通知、候补订单、兑现成功

> **匹配优先级**：打车 > 酒店 > 航空 > 高铁。"电子发票"是通用词，放高铁关键词里，但打车/酒店含更具体词会先命中，避免高德打车被误分类为高铁。

## 使用方法

### 手动触发

```
/skill travel-invoice
```

或者直接说：

```
整理我的出差发票
扫描最近三个月的高铁发票
帮我打包航空机票发票
```

### 工作流程

1. 扫描最近 3 个月（90天）邮件
2. 按类型分类（酒店/高铁/航空/打车）
3. 提取附件并下载
4. **按闭环行程分组**（核心步骤，见下方规则）
5. 每段闭环行程生成单独 PDF，未闭环行程只告知用户不生成
6. **⚠️ 把PDF发到聊天窗口展示，等用户确认**
7. 用户明确说"发送"后才能发邮件到自己邮箱

> **🚫 绝不自动发送邮件！所有发邮件必须经过用户许可。** 必须先把结果和PDF展示给用户，等用户明确说"发送"或"确认"后才能发邮件。未获许可=不发。

> **用户要的是真实发票附件，不是文字列表PDF。** 直接把每张发票 PDF 发到聊天窗口，跳过没有附件的邮件。

### 闭环行程分组规则

**核心逻辑**：每段行程必须是从武汉出发、回到武汉的闭环。该行程期间的所有发票打包为一个PDF。

1. **打车票优先闭环** — 用高德行程单的起止地点判断行程边界：
   - 武汉打车：起点/终点含"武汉站"的打车票标记为去站或回站
   - 外地打车：标记为目的地城市内交通
2. **高铁/航空辅助闭环** — 用出站/回站列车配对确认行程：
   - 出站：武汉站→目的地
   - 回站：目的地→武汉站
   - 配对规则：每趟出站列车配最近的后续回站列车
3. **酒店归入行程** — 开票日期落在行程区间内的酒店发票归入该行程
4. **未闭环不生成** — 没有回程票的行程只告诉用户，不生成PDF
5. **缺打车票时询问用户** — 如果没有电子打车票辅助判断闭环，先问用户是否缺哪一段，等用户回复后再按指令决定是否生成
6. **PDF内发票排列顺序**（用户明确要求）：
   - **高铁票放最前面**
   - **打车票按时间顺序排中间**（每笔发票+行程单配对相邻）
   - **酒店票放最后面**
   - 即：出站高铁 → 回站高铁 → 出发打车 → 市内打车 → 返回打车 → 酒店

**行程分组步骤**：
```python
# 1. pdftotext 提取行程单文本 → 解析起止地点、日期
# 2. pdftotext 提取高铁发票文本 → 解析出发站、到达站、日期
# 3. 按日期排序所有出站/回站记录
# 4. 配对：每趟出站找最近的回站，形成闭环行程
# 5. 将打车票、酒店发票按日期归入对应行程
# 6. 未配对的出站记录标记为"未闭环"
```

### 附件筛选规则

| 类型 | 保留 | 排除 | 说明 |
|------|------|------|------|
| 酒店 | 电子发票 (`dzfp_*.pdf`) | 结账单 | **结账单 ≠ 发票**，结账单只是消费明细，没有税务监制章，不能报销，必须排除 |
| 高铁 | ZIP 自动解压后的 `.pdf` | `.ofd` 文件 | 12306附件是ZIP包，脚本自动解压提取PDF |
| 高德打车 | 电子发票.pdf + 电子行程单.pdf | `.ofd` `.xml` | 行程单用CropBox裁剪去广告+页码 |

### PDF 合并

每段闭环行程用 PyPDF2 单独合并成独立PDF文件（qpdf不可用则用PyPDF2）：

```python
from PyPDF2 import PdfMerger
merger = PdfMerger()
for fpath in trip_pdf_list:
    merger.append(fpath)
merger.write(output_path)
merger.close()
```

### 高德行程单排版规则

1. **发票+行程单配对** — 每笔高德打车：发票页紧跟行程单页，相邻排列
2. **行程单 PDF 裁剪去广告** — 高德行程单有大量广告，用 PyPDF2 修改页面 CropBox 直接裁剪 PDF（保持原始矢量内容，不转图片）：
   - **精确裁剪坐标**（基于 A4 595×842pt 行程单实测）：CropBox lower_left=(0, 460), upper_right=(595, 665)
   - 广告区域: PDF y=665~842（顶部约21%），空白+页码: PDF y=0~460（底部约55%）
   - 保留区域: y=460~665（标题+信息+表格，约205pt≈72mm高）
   - 非标准尺寸按比例缩放: top_ratio=665/842≈0.79, bottom_ratio=460/842≈0.55
   - **裁剪后不保留A4纸大小**，按实际内容尺寸排版
   - **页码也要去掉**（用户明确要求）
   - 可用 `mutool draw -o preview.png -r 200 input.pdf` 验证裁剪效果（mutool 正确识别 CropBox）
   - 输出仍是原始矢量 PDF，不是图片转的 PDF

### 输出示例

```
✅ 扫描完成！
📊 发现发票: 酒店(3), 高铁(5), 航空(2), 高德(4)
📄 已打包 PDF，共 14 张发票
📎 PDF 已发送到聊天窗口，请确认
```

**等用户确认后：**
```
📧 已发送到: {{MY_EMAIL}}
```

## 配置文件

参考 `references/configuration.md` 自定义：
- 搜索关键词
- 日期范围
- 发送邮箱
- 附件保存路径

## 故障排除

### 重要工作流规则

1. **🚫 所有发邮件必须经用户许可** — 扫描完先在聊天窗口展示结果和PDF，等用户明确说"发送"后才发邮件，绝不自动发送
2. **闭环行程分组** — 每段行程必须 武汉出发→武汉返回 闭环，未闭环不生成只告知；打车票优先判断行程边界
3. **每段行程独立PDF** — 不再合并成一个大PDF，而是每段闭环行程生成单独PDF文件
4. **缺少回程先询问** — 无回程票的行程不自动生成，先告知用户缺哪段，等用户回复后再按指令行事
5. **发票排列顺序** — 高铁票放最前面，打车票按时间排中间，酒店票放最后面
6. **发票+行程单配对排列** — 高德打车的发票和行程单要相邻排版（发票紧跟行程单），不能分散
7. **行程单 PDF 裁剪去广告** — 高德行程单用 PyPDF2 修改 CropBox 裁掉广告，保持原始矢量 PDF，不转图片交付
8. **PDF合并用PyPDF2** — qpdf在此系统不可用，用 PyPDF2 PdfMerger 合并；大文件注意timeout
9. **高铁发票信息提取** — 用 pdftotext -layout 提取起止站和日期，用于闭环行程分组；注意全角数字转换

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 扫描结果为0但邮件存在 | page-size=200 不够用，12306邮件在第2页 | 脚本使用 page-size=500 覆盖全部邮件 |
| 找不到 12306 发票 | 主题不含"12306"字样 | 12306 邮件主题是"网上购票系统-电子发票通知"，匹配**发件人** `rails.com.cn` |
| 高德打车邮件归到高铁 | "电子发票"是通用词，train 关键词先匹配 | 匹配优先级：taxi > hotel > airline > train |
| 扫出太多非发票邮件 | "网上购票"太宽泛，匹配了支付/退票通知 | 排除词增加：支付通知、退票通知、改签通知、候补订单、兑现成功；"网上购票"改为"电子发票" |
| JSON 解析失败 | himalaya 输出有 WARN 行 | 脚本使用 `plain` 格式而非 JSON 格式规避此问题 |
| 附件下载失败 | 命令未使用 shell 模式 | 下载命令需要 pipe，需 `shell=True` |
| himalaya attachment download 报错 unexpected argument | 误用 `--envelope-id` flag | himalaya 用位置参数：`himalaya attachment download <ID> -d <path>`，ID 直接跟在命令后，不是 flag |
| SMTP 发送失败 | QQ 邮箱授权码过期 | 重新生成授权码：QQ邮箱网页版 → 设置 → 账户 → 开启 SMTP |
| himalaya "cannot find UID" 错误 | IMAP保存副本失败，但SMTP发送已成功 | ❌不要重试！邮件已发出，重试会重复发送。只需忽略此错误 |
| PyPDF2 合并超时 | terminal 直接跑 Python 脚本会超时 | 用 `qpdf --empty --pages` 替代 PyPDF2，更快更稳定 |
| PyPDF2 裁剪超时（中文文件名） | terminal 中执行含中文文件名的 Python 一行脚本反复超时 | 先用 write_file 写脚本到临时文件，再 `python3 /tmp/script.py` 执行，避免 shell 中文转义问题 |
| pdftoppm 忽略 CropBox | pdftoppm 渲染完整 mediabox，裁剪后页面看似未变 | 用 `mutool draw -r 200` 替代 pdftoppm 验证裁剪效果 |
| PyPDF2 修改 MediaBox 后内容消失 | MediaBox 改小后坐标系错位，内容落在页面外 | 只修改 CropBox（不改 MediaBox），PDF viewer 和 mutool 会正确显示 |
| ghostscript translate 裁剪失败 | GS 的 translate 会缩放/移动整个内容流，效果不可控 | 不要用 GS 裁剪行程单，用 PyPDF2 CropBox |
| mutool trim 按 CropBox 裁剪输出空白 | mutool trim 重写 mediabox 但丢弃了裁剪区域外的内容 | 不要用 mutool trim，只用 PyPDF2 设 CropBox，交付给用户的 PDF viewer 会正确显示 |

### 华住酒店发票下载方法

华住酒店集团邮件中的发票链接格式为 `https://vat.huazhu.com/invoice/queryFiles/{uuid}`，这是一个Vue SPA页面，需要Geetest验证才能查看。**但可以直接通过下载API绕过验证**：

- **PDF下载**: `https://vat.huazhu.com/gp/invoice/download/{uuid}.pdf`
- **OFD下载**: `https://vat.huazhu.com/gp/invoice/download/{uuid}.ofd`
- **XML下载**: `https://vat.huazhu.com/gp/invoice/download/{uuid}.xml`

其中 `{uuid}` 就是邮件链接中的那段hash（如 `fdab1811629e4ce3add18c86d86c2427`）。

```bash
# 直接下载PDF，无需浏览器交互或Geetest验证
curl -s -L "https://vat.huazhu.com/gp/invoice/download/{uuid}.pdf" -o invoice.pdf
```

**注意**：
- SPA页面（`/invoice/queryFiles/`）在浏览器中会超时/需要验证，不要试图用browser_navigate渲染它
- `/gp/notify/download/{uuid}` 路径**不能**用于发票下载（返回"fileUuid不存在"错误），只有 `/gp/invoice/download/` 才是正确的路径
- 需要用 `-L` 参数跟随重定向

### 发票提取方法

从PDF发票中提取行程信息用 `pdftotext -layout`：
```bash
pdftotext -layout 'input.pdf' -
```

**高铁发票提取要点：**
- 开票日期、出发站→到达站、车次号、乘车日期
- 全角数字需转换（２０２６→2026）

**高德行程单提取要点：**
- 行程时间、城市、起点、终点、金额、服务商
- 行程单已裁剪（CropBox），pdftotext仍能提取全部文字内容

### SMTP 授权码

QQ 邮箱授权码可能失效或未开启 SMTP 服务。修复步骤：
1. 登录 QQ 邮箱网页版
2. **设置 → 账户 → POP3/IMAP/SMTP/Exchange... 服务**
3. 开启 **SMTP 服务**
4. 如有必要，重新生成授权码
5. 更新 `~/.config/himalaya/config.toml` 中的 `auth.cmd`

### 调试模式

手动运行脚本查看详细输出：
```bash
python3 ~/.hermes/skills/productivity/travel-invoice/scripts/travel_invoice.py
```

手动测试 himalaya：
```bash
# 查看邮件列表（用 page-size 500 避免漏扫）
himalaya envelope list --page 1 --page-size 500 --output plain

# 搜索 12306 邮件
himalaya envelope list --page 1 --page-size 500 --output plain | grep -i "12306\|电子发票\|希尔顿"

# 测试 SMTP 发送
echo 'From: {{MY_EMAIL}}
To: {{MY_EMAIL}}
Subject: Test
Content-Type: text/plain
Test' | himalaya message send
```
