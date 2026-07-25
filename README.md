# Hy3 Campus Decision Copilot

基于 Hy3 的校园学业、竞赛与时间决策 MCP Server。项目以 `stdio` 方式独立运行在
`E:\AI\xynewui_mcp`，不依赖也不会修改 SYLUlive Flutter 客户端、Go 后端、PostgreSQL、
真实学生账号、教务密码、Cookie、JWT 或生产 RAG。

第一版仅提供只读的分析、比较、解释与规划能力。示例资料均为演示数据，不能替代学校当年
正式通知、学院审核或个人学业指导。

## 能力范围

| 工具 | 作用 | 本地确定性约束 |
| --- | --- | --- |
| `hy3_campus_status` | 查看脱敏运行状态和可用能力 | 不返回密钥、绝对路径或完整环境变量 |
| `answer_campus_question` | 基于本地 Markdown 文档回答校园问题 | 仅引用检索到的本地来源；没有可靠证据时拒绝作答 |
| `compare_competitions` | 比较 2 至 5 项赛事 | 学校认定、人工评价、学生适配、证据质量四维分离，不生成总分 |
| `analyze_academic_snapshot` | 分析非身份化学业快照 | 学分、挂科、二课缺口和完整度由本地程序计算 |
| `plan_student_week` | 安排一周目标 | 不占用固定事件或睡眠，遵守最小时间块和每日上限 |

`HY3_MODE=disabled` 时只注册状态工具；`fixture` 和 `live` 模式注册全部五个工具。

## 环境要求与安装

- Python 3.11 或更高版本，推荐 Python 3.12。
- [uv](https://docs.astral.sh/uv/) 用于依赖和虚拟环境管理。
- Windows PowerShell 示例中的项目目录为 `E:\AI\xynewui_mcp`。

```powershell
cd E:\AI\xynewui_mcp
uv sync
Copy-Item .env.example .env
```

不要把真实 API Key 提交到 `.env`、客户端配置或任何验证记录中。

## 运行模式

| 模式 | 配置 | 行为 | 适用场景 |
| --- | --- | --- | --- |
| Disabled | `HY3_MODE=disabled` | 只暴露 `hy3_campus_status` | 默认安全状态、配置检查 |
| Fixture | `HY3_MODE=fixture` | 读取 `tests/fixtures/hy3` 的固定响应，并执行与 Live 相同的结构校验 | 本地演示、CI、离线开发 |
| Live | `HY3_MODE=live` | 真实调用显式配置的 Hy3 OpenAI-compatible API | 已取得有效 Key 后的人工验证 |

启动 Fixture Server：

```powershell
cd E:\AI\xynewui_mcp
$env:HY3_MODE = "fixture"
$env:HY3_CAMPUS_ROOT = "./examples"
$env:HY3_FIXTURE_ROOT = "./tests/fixtures/hy3"
uv run hy3-campus-decision-mcp
```

该进程的 stdout 专用于 MCP JSON-RPC；诊断日志只写入 stderr。不要在启动后向同一终端
输入普通文本作为调试输出。

## 客户端接入

仓库提供可直接作为起点的客户端配置：

- [Cursor 配置](clients/cursor.mcp.json)
- [CodeBuddy 配置](clients/codebuddy.mcp.json)

两个配置都使用 Fixture 模式，命令等价于：

```json
{
  "command": "uv",
  "args": [
    "--directory",
    "E:/AI/xynewui_mcp",
    "run",
    "hy3-campus-decision-mcp"
  ],
  "env": {
    "HY3_MODE": "fixture",
    "HY3_CAMPUS_ROOT": "./examples",
    "HY3_FIXTURE_ROOT": "./tests/fixtures/hy3"
  }
}
```

若将仓库放到其他位置，只修改 `--directory` 的绝对目录；`HY3_CAMPUS_ROOT` 和
`HY3_FIXTURE_ROOT` 保持相对项目根目录的路径即可。

## 工具输入契约

所有工具输入都拒绝未知字段。核心工具成功时使用统一信封：

```json
{
  "status": "ok",
  "result": {},
  "deterministic_findings": {},
  "sources": [],
  "warnings": [],
  "model": {
    "provider": "hy3",
    "model": "hy3",
    "mode": "fixture",
    "reasoning_effort": "medium"
  },
  "meta": {
    "schema_version": "1",
    "generated_at": "2026-07-25T00:00:00Z"
  }
}
```

失败时只返回稳定错误结构，例如：

```json
{
  "status": "error",
  "code": "competition_count_invalid",
  "message": "比较工具至少需要两项赛事。"
}
```

### `answer_campus_question`

```json
{
  "query": "创新创业学分如何认定？",
  "category": "policy",
  "max_sources": 5
}
```

`category` 可为 `policy`、`academic`、`competition` 或 `general`。返回的来源仅含
`examples/campus_documents` 下的相对路径和 `source_id`。任何 `official: false` 的演示来源
都会附带“这是演示文档，不代表学校现行正式政策。”警告。

### `compare_competitions`

目录名称模式：

```json
{
  "competition_names": ["蓝桥杯", "中国国际大学生创新大赛"],
  "student_profile": {
    "major": "计算机科学与技术",
    "grade": "大三",
    "weekly_hours": 8
  }
}
```

也可使用 `competitions` 提供 2 至 5 个自定义对象；`competition_names` 与 `competitions`
必须二选一。自定义对象只接受 `name` 及可选的 `category`、`recognition_note`、`difficulty`、
`recommended_weekly_hours`，并被标记为 `custom_input` 证据质量。

### `analyze_academic_snapshot`

必须且只能提供 `snapshot` 或 `snapshot_path`：

```json
{
  "snapshot_path": "academic/safe_snapshot.json"
}
```

内联 `snapshot` 至少包含 `courses`、`earned_credits`、`required_credits`、`erke_earned` 和
`erke_required`。工具会在任何模型调用前递归拒绝 `student_id`、姓名、手机号、邮箱、Cookie、
令牌和密码等敏感字段及其大小写、下划线、短横线、驼峰变体。

### `plan_student_week`

必须且只能提供 `schedule` 或 `schedule_path`。`weekday=1` 为周一、`weekday=7` 为周日；
`week_start` 必须为对应 IANA 时区的一周周一，时间使用 `HH:mm`，固定事件不能跨午夜或重叠。

```json
{
  "schedule_path": "schedules/sample_week.json",
  "goals": [
    {"name": "准备蓝桥杯", "weekly_minutes": 360, "priority": "high"}
  ],
  "constraints": {
    "minimum_block_minutes": 30,
    "daily_max_minutes": 240,
    "sleep_start": "23:30",
    "sleep_end": "07:00"
  }
}
```

当总目标超出可用容量时，结果会在 `deterministic_findings.unscheduled` 中保留未安排时长，
不会为完成目标而占用固定事件或睡眠。

## 数据、路径与网络安全

- 路径输入只能是 `HY3_CAMPUS_ROOT` 内的相对路径，拒绝绝对路径、`..` 穿越和符号链接越界。
- 第一版仅读取 `.md`、`.txt`、`.json`、`.jsonl`、`.csv`，受文件数量和单文件大小限制。
- Live 端点接受 `https://host`、`https://host/v1` 或完整
  `https://host/v1/chat/completions`，最终统一为一个 `/v1/chat/completions` 地址。
- HTTPS 始终允许；HTTP 仅允许 `localhost`、`127.0.0.1`、`::1`，或在
  `HY3_ALLOW_PRIVATE_HTTP=true` 时使用 IP 私网地址。公网 HTTP、URL userinfo、query、fragment
  和重定向均被拒绝。
- 日志和工具结果不包含 API Key、Authorization、完整模型原始响应、用户身份字段或绝对路径。
- 项目不会连接 SYLUlive 生产 API、数据库、账号体系或教务系统，也不执行远程写操作。

完整配置项见 [`.env.example`](.env.example)。

## 本地验证与 CI

下列命令全部在 Fixture 模式下运行，不需要 Hy3 Key：

```powershell
cd E:\AI\xynewui_mcp
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/selfcheck.py
uv run python scripts/sdk_stdio_client.py
uv run python scripts/validate_examples.py
```

`sdk_stdio_client.py` 会启动真实子进程，验证 `initialize`、`tools/list` 及四个核心工具的
`tools/call`。GitHub Actions 在 Python 3.11 与 3.12 上执行主要离线验证，配置位于
[CI 工作流](.github/workflows/ci.yml)。

## Live 验证

真实 Hy3 验证不会进入公共 CI，也不能由 Fixture 结果替代。取得合法 Hy3 API 配置后，使用：

```powershell
cd E:\AI\xynewui_mcp
$env:HY3_MODE = "live"
$env:HY3_API_BASE = "https://your-hy3-host/v1"
$env:HY3_API_KEY = "<仅在当前终端设置>"
$env:HY3_MODEL = "hy3"
uv run python scripts/verify_live_hy3.py
```

脚本会拒绝非 Live 模式、缺失 Key、Fixture 降级及四个核心工具中的任一失败。成功后，将
脱敏的时间、提交 SHA、包版本、MCP SDK 版本、客户端版本、模型名、API Host 脱敏值和各工具
的 Schema/确定性复核结果填写到 [Live 验证记录模板](assets/live-verification.md)。
该模板当前明确标记为“未执行”，不应被视为真实 Hy3 验证已完成。

## 目录说明

```text
src/hy3_campus_decision_mcp/  MCP Server、Hy3 客户端、安全策略和确定性算法
examples/                     面向用户的公开演示资料
tests/fixtures/               仅供测试和 Fixture Provider 使用的固定响应
clients/                      Cursor 与 CodeBuddy 配置
scripts/                      离线自检、stdio 协议验证、示例校验和 Live 验证脚本
assets/                       验证记录模板
```

## 许可证

[MIT](LICENSE)
