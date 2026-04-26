# my_hermes_skill_dev

Hermes skill 开发仓库，存放自建的 Hermes skill 项目。

## Skills

| Skill | 说明 |
|-------|------|
| [travel-invoice](travel-invoice/) | 出差发票自动整理 — 扫描邮箱发票、提取附件、打包 PDF |

## 新增 Skill

在 `my_hermes_skill_dev/` 下新建目录，按以下结构组织：

```
<skill-name>/
├── SKILL.md          # Skill 定义（名称、描述、工作流、排错指南）
├── scripts/          # 脚本文件
├── references/       # 参考文档、配置说明
└── README.md         # Skill 说明
```

开发完成后复制到 `~/.hermes/skills/` 对应目录即可启用。
