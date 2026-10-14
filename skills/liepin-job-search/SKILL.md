---
name: liepin-job-search
description: 使用猎聘官方 CLI 在 WorkBuddy 中搜索匹配职位、查看简历，并在用户明确确认后更新求职期望或投递。适用于用户指定城市、岗位、薪资、公司条件或要求分析猎聘简历时。
---

# 猎聘求职助手

## 能力与边界

- 通过 MCP 工具调用用户本机的 `liepin-cli`，不自行调用猎聘未公开接口、不抓取网页，也不反向工程。
- `liepin_search_jobs` 可提交岗位名、地点、薪资范围、公司名、经验、学历、公司性质和页码。猎聘 CLI 的筛选参数格式由猎聘 CLI 自身决定；不确认格式时先少传过滤项，返回原始 JSON，不臆测字段。
- `liepin_get_resume` 读取当前猎聘账号简历，结果只在当前对话分析，不另行保存。
- `liepin_update_job_expectation` 是写操作。先解释将修改的记录 ID 和每个字段，等待用户明确同意，再精确传 `confirmation="确认更新猎聘求职期望"`。`record_id` 必须来自简历读取结果。
- `liepin_apply_job` 会实际投递。必须先搜索取得 `job_id` 与 `job_kind`，核对职位、公司、薪资和地点等可见信息，展示给用户并逐职位请求同意；仅在用户明确同意该职位后才传 `confirmation="确认投递该猎聘职位"`。禁止猜测 `job_kind`、捏造缺失详情或批量投递。

## 首次使用

1. 由用户按猎聘授权页说明安装官方 CLI：<https://www.liepin.com/mcp/auth>。官方授权页所链接仓库：<https://github.com/liepin-tech-2026/liepin-cil>。
2. 在用户可交互终端中运行 `liepin-cli setup`，由用户亲自登录并授权。Token 保存在 CLI 本机配置中；不要索取或复述 Token。
3. 安装本项目依赖并配置 `mcp.json`。连接前确认 `liepin-cli` 已可在当前系统 PATH 调用。
4. 若 CLI 未安装、授权失败或版本不兼容，停止操作并说明如何修复，不尝试绕过授权或切换非官方端点。

## 数据解释

CLI 返回原始 JSON。字段结构可能随其版本变化；仅解释结果中确实存在的职位、公司、薪资和地点字段。若 CLI 返回非 JSON 或数据字段不足，告诉用户哪些信息拿不到，不根据职位 ID 或名称推断。
