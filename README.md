# liepin-workbuddy-mcp

一个供 [WorkBuddy](https://www.workbuddy.cn) 使用的本地 **stdio MCP Server** 适配层，把猎聘官方命令行工具 `liepin-cli` 的能力（职位搜索、简历读取、求职期望更新、职位投递）暴露为 MCP 工具。

本项目**不自行实现猎聘 API 客户端**——不调用未公开接口、不抓取页面、不模拟登录，只通过官方授权页链接的 `liepin-cli` 完成操作。

> ⚠️ 第三方说明：官方 `liepin-cli` 仓库目前**未声明开源许可证**，因此本仓库不 vendoring、不复制、不再分发其源码，只依赖用户本机已安装的 CLI 命令。猎聘 CLI 的安装与授权请以官方授权页为准。

## 能力一览

| MCP 工具 | 作用 | 是否写操作 |
| --- | --- | --- |
| `liepin_search_jobs` | 按岗位、城市、薪资、公司等条件搜索职位 | 只读 |
| `liepin_get_resume` | 读取当前账号简历 | 只读 |
| `liepin_update_job_expectation` | 更新求职期望 | 写（需明确确认） |
| `liepin_apply_job` | 投递指定职位 | 写（需明确确认，逐职位核对） |

投递与更新都是**不可轻易撤回**的动作：适配器为两者设置了精确的确认文本门槛，缺失确认会直接阻止调用，杜绝批量或猜测式投递。

## 项目结构

```text
yx/
├── connector-meta.json           # WorkBuddy 连接器元信息
├── mcp.json                      # MCP 配置样例（按本机修改 command 路径后使用）
├── pyproject.toml
├── src/liepin_workbuddy_mcp/
│   ├── __init__.py
│   ├── cli.py                    # 对 liepin-cli 的安全子进程封装
│   └── server.py                 # FastMCP stdio server
├── skills/liepin-job-search/SKILL.md
└── tests/
```

## 安装与配置

### 1. 安装官方猎聘 CLI

猎聘 CLI 安装与授权遵循官方授权页：<https://www.liepin.com/mcp/auth>（授权页所链接仓库为 <https://github.com/liepin-tech-2026/liepin-cil>）。任选官方 README 中的一种方式安装，确保 `liepin-cli` 在 `PATH` 中可调用。

首次授权在**可交互终端**中执行：

```bash
liepin-cli setup
```

按提示打开授权页、登录，把页面生成的 Token 粘贴到终端。Token 只保存在本机 CLI 配置中，**不要**发到聊天、截图或项目文件；凭证有效期 90 天。

检查授权状态：

```bash
liepin-cli auth status
```

### 2. 安装本项目

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. 在 WorkBuddy 中配置 MCP

项目根目录的 `mcp.json` 是配置样例。将其中的 `mcpServers.liepin-workbuddy` 节点**合并**到 WorkBuddy 的用户级 MCP 配置（`~/.workbuddy/mcp.json`），并按本机实际安装位置修改 `command` 路径；不要覆盖已有的其它 MCP server 项。合并后在 WorkBuddy 连接器管理页面找到 `liepin-workbuddy`，点击「信任」并启用。

> 提示：MCP server 通过 stdio 通信，进程本身不打印启动横幅或调试日志。

### 4. 开始使用

- 「用猎聘搜索深圳的产品经理岗位，期望薪资 25k–35k。」
- 「读取我的猎聘简历，帮我总结优势和需要补强的地方。」
- 「搜索符合条件的岗位，逐个比较；投递前先把岗位信息给我确认。」

薪资单位、薪资类型等筛选值以 `liepin-cli job search --help` 展示的格式为准；不确定时先查帮助，不要猜测编码。职位返回为 CLI 的原始 JSON，本项目透传、不承诺字段形状。

## 本地运行与测试

```bash
.venv/bin/python -m pytest -q
```

也可在终端直接启动 MCP server：

```bash
.venv/bin/liepin-workbuddy-mcp
```

## 安全边界与限制

- 写操作（更新求职期望、投递）必须在用户查看字段并明确确认后才执行。
- 职位搜索结果中的 `job_id`、`job_kind` 均须原样取自本次结果，禁止推断或捏造。
- 简历数据涉及个人信息，仅在当前授权账号与用户确认的范围内调用，不另行保存副本。
- 官方 CLI 未声明许可证，本项目不随附其源码；因此**无真实授权账号时，集成测试无法验证线上数据**，单元测试使用假 CLI 验证命令组装、JSON 解析、错误脱敏与确认门槛。