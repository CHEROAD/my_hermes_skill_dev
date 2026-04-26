# Travel Invoice - 出差发票自动整理

自动扫描邮箱中的出差发票邮件，提取附件并打包成 PDF 发送给自己。

## 功能

- 扫描近 90 天邮件，按关键词匹配发票：酒店、高铁、航空、高德打车
- 自动下载发票附件（PDF/图片/ZIP）
- 按闭环行程分组，每段行程生成独立 PDF
- 高德行程单自动裁剪广告和页码
- 发送前需用户确认，绝不自动发邮件

## 目录结构

```
travel-invoice/
├── SKILL.md              # Skill 定义文件（触发词、工作流、排错指南）
├── scripts/
│   └── travel_invoice.py # 主脚本（扫描→下载→合并→发送）
└── references/
    └── configuration.md  # 配置说明（关键词、日期范围、邮箱等）
```

## 安装

```bash
cp -r travel-invoice ~/.hermes/skills/productivity/
```

Hermas 已配置好邮箱即可使用。

## 使用方法

### 通过 Hermes 触发

```
/skill travel-invoice
```

或直接说：

- 整理我的出差发票
- 扫描最近三个月的高铁发票
- 帮我打包航空机票发票

### 手动运行脚本

```bash
# 仅扫描+生成PDF（默认模式，不自动发邮件）
python3 scripts/travel_invoice.py scan

# 扫描+生成+发送（需先确认后再用）
python3 scripts/travel_invoice.py full

# 单独发送已生成的PDF
python3 scripts/travel_invoice.py send /tmp/xxx/出差发票汇总.pdf
```

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `MY_EMAIL` | 收发邮件地址 | `user@qq.com` |

### 首次使用

1. 安装 himalaya 并配置 QQ 邮箱 IMAP/SMTP
2. 安装 Python 依赖：`pip install PyPDF2`
3. 设置环境变量：`export MY_EMAIL=your@qq.com`
4. 运行 `python3 scripts/travel_invoice.py scan` 测试

## 依赖

- **命令行工具**: [himalaya](https://github.com/pimalaya/himalaya)（邮件客户端）
- **Python 包**: reportlab, PyPDF2
- **可选**: qpdf（PDF 合并，比 PyPDF2 更快更稳定）

## 关键词配置

| 类型 | 关键词 |
|------|--------|
| 酒店 | 酒店、住宿、希尔顿、万豪、如家、汉庭、7天、维也纳、全季... |
| 高铁 | 高铁、火车、动车、12306、铁路、电子发票 |
| 航空 | 航空、机票、航班、国航、东航、南航、厦航 |
| 打车 | 高德、打车、滴滴 |

**匹配优先级**: 打车 > 酒店 > 航空 > 高铁

**排除词**: 作废、红字、退货、退款、支付通知、退票通知、改签通知、候补订单、兑现成功

## 工作流程

1. 扫描近 90 天邮件 → 按关键词分类
2. 下载附件 → ZIP 自动解压、酒店排除结账单
3. 闭环行程分组（武汉出发→武汉返回）
4. 合并 PDF（高铁→打车→酒店顺序）
5. 展示结果，等用户确认后发送邮件

## 许可

MIT
