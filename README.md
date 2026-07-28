# SYLUlive MCP

SYLUlive MCP 是供 LangChain Agent 调用的纯工具服务。它只负责读取和计算事实，不调用任何大模型，也不生成最终回答、推荐或行动建议。

## 架构边界

```text
Flutter
  -> SYLUlive Go（鉴权、Run、SSE、预算、Grant、最终来源校验）
    -> LangChain Agent（Hy3、工具选择、多轮检索、结构化回答）
      -> SYLUlive MCP（事实检索、确定性计算、计划校验）
        -> Go 内部只读 API（生产数据唯一入口）
```

本仓库遵守以下约束：

- 不包含 Hy3 客户端、Prompt、LangGraph 或最终回答模型。
- 不连接 PostgreSQL，不持有数据库 DSN、用户 JWT、学号或 Cookie。
- 生产数据只经 Go 的 `/internal/mcp/*` API 读取。
- Streamable HTTP 使用每请求 Bearer Grant；stdio 才允许进程级短期 Grant。
- Grant 只注入 Go API 的 Authorization Header，不进入模型可见参数或工具结果。
- 所有工具拒绝未知字段、敏感身份字段、越界路径和超限输入。

## 工具

| 工具 | 职责 |
| --- | --- |
| `system_status` | 返回脱敏状态、架构能力和契约摘要 |
| `policy_search` | 最多用 4 个查询检索 20 条政策片段 |
| `policy_get_sources` | 复核最多 8 个来源的发布状态、有效期和内容哈希 |
| `competition_search` | 按名称或类别检索赛事事实 |
| `competition_get_details` | 获取最多 5 项赛事详情 |
| `competition_compare_facts` | 按稳定 ID 读取并比较 Go 持有的赛事事实 |
| `academic_get_summary` | 通过 Grant 获取最小化学业汇总，不接收课程或成绩明细 |
| `schedule_find_free_windows` | 通过 Grant 获取固定日程并计算空闲窗口 |
| `schedule_validate_plan` | 通过 Grant 获取固定日程并校验候选计划 |

生产 MCP 不注册 `answer_campus_question`。`demo` 模式使用独立契约，保留
`academic_calculate_summary` 以及本地学业快照、课表输入，仅用于仓库演示，不应被生产
Agent 加载。本地检索展示入口位于 `demo/demo_answer_campus_question.py`。

## 运行模式

| 模式 | 行为 |
| --- | --- |
| `disabled` | 默认安全状态，只注册 `system_status` |
| `demo` | 注册演示契约，只读取仓库公开样例和受限相对路径 |
| `production` | 注册生产契约，所有个人数据和赛事事实通过带 Grant 的 Go API 读取 |

安装和启动演示服务：

```powershell
uv sync
$env:SYLULIVE_MCP_MODE = "demo"
$env:SYLULIVE_DEMO_ROOT = "./examples"
uv run sylulive-mcp
```

容器化 Agent Service 使用 Streamable HTTP：

```powershell
$env:SYLULIVE_MCP_MODE = "production"
$env:SYLULIVE_MCP_TRANSPORT = "streamable-http"
$env:SYLULIVE_MCP_HOST = "0.0.0.0"
$env:SYLULIVE_MCP_PORT = "8000"
$env:SYLULIVE_MCP_ALLOWED_HOSTS = '["sylulive-mcp"]'
uv run sylulive-mcp
```

Agent 连接地址为 `http://sylulive-mcp:8000/mcp`。每个 HTTP 请求的 `Authorization: Bearer <grant>` 会在独立异步上下文中转发给 Go，不会使用模型参数传递。stdio 模式则由 Go 在启动单次 Run 的隔离进程时设置 `SYLULIVE_MCP_GRANT`。

Streamable HTTP 配置了 `SYLULIVE_MCP_GRANT` 时服务会拒绝启动，防止多个请求共享身份。
HTTP 入口还会校验 Host 并限制请求体；内部 API 响应以流式方式限制为默认 2 MiB。

生产进程示例：

```powershell
$env:SYLULIVE_MCP_MODE = "production"
$env:SYLULIVE_API_BASE = "https://sylulive-internal.example"
$env:SYLULIVE_MCP_GRANT = "<Go 按 Run 签发的短期不透明 Grant>"
uv run sylulive-mcp
```

生产内部 API 约定：

```text
POST /internal/mcp/policy/search
POST /internal/mcp/policy/sources
POST /internal/mcp/competition/search
POST /internal/mcp/competition/details
POST /internal/mcp/competition/compare
POST /internal/mcp/academic/summary
POST /internal/mcp/schedule/week
```

Go 根据 Grant 确定用户。学业工具只返回最小化汇总；日程工具只接收周日期、约束和
Agent 候选计划，MCP 获取授权固定日程后执行确定性计算；赛事比较只接收稳定 ID。

## LangChain 接入

`langchain-mcp-adapters` 可通过 Streamable HTTP 或 stdio 加载本服务。Agent Service 负责按 Run 只暴露授权工具，并限制工具轮数、单工具次数和最终证据数量。本仓库的 Schema 已将 `policy_search` 限制为每次 4 个 query、20 个结果，将来源复核限制为 8 条。

Go 在接受 Agent 的结构化回答前仍必须验证：

```text
回答引用的 source_id
  ⊆ 本次 policy_search 实际返回的 source_id
  且 policy_get_sources 复核为仍发布、仍有效、内容哈希未变化
```

## 契约与验证

契约版本为 `sylulive-mcp/3`，版本化清单位于 `assets/contracts/sylulive-mcp-v3.json`。
清单分别记录 production 与 demo 注册表，默认集成应使用 production 契约。

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python scripts/export_contracts.py
uv run python scripts/selfcheck.py
uv run python scripts/sdk_streamable_http_client.py
```

`scripts/selfcheck.py` 会启动真实 stdio 子进程，完成 initialize、tools/list 和核心 tools/call。stdout 专用于 MCP JSON-RPC，日志只写入 stderr。

## diaofenyuan 内置 Runtime

`diaofenyuan` 使用独立的 Hy3 契约入口 `hy3-campus-decision-mcp`。该入口返回
`hy3_campus_status` 和三个固定决策工具，契约版本为 `sylulive-hy3/1`；便携问答工具
只在默认的 `HY3_TOOL_PROFILE=portable` 中注册。生产 Go Runtime 应设置
`HY3_TOOL_PROFILE=sylulive_runtime`，并通过 `/opt/SYLUlive_MCP/bin/run-stdio` 启动，
避免把 Hy3 Key 放进仓库环境或命令行参数。

Live Provider 支持 `HY3_API_PROTOCOL=openai_chat_completions` 和
`HY3_API_PROTOCOL=anthropic_messages`。两种协议共享认证、限流、超时、上游故障和连接
错误分类，并在 JSON 解析前执行 `HY3_MAX_OUTPUT_BYTES` 流式字节限制。

部署前运行：

```powershell
uv run python scripts/verify_sylulive_contract.py
```

该检查会启动真实 Fixture 子进程，比较 `initialize`、`tools/list`、状态摘要和三个
输入/输出 Schema 的 SHA-256；任何 Schema 漂移都会失败，而不会伪装成兼容。

当前冻结兼容基线：

```text
SYLUlive/diaofenyuan  2efb524fb3090f877a8205dca63dd6200e745e8a
SYLUlive_MCP          d6d29582d164c6f9aa5c24745d7ecae88ce9f343
contract_version      sylulive-hy3/1
compare_competitions  b72f014a42546f6ab348c42a28203f859ee2b131ed00fefea6bf9db71dfbdff4
analyze_academic_snapshot
                      0784c8d703113093229e97a005f51e7e80d87a952e803286bcca7359ae2c5988
plan_student_week     d3e2930561ed3f7c23923ffd18ca74373d86dcffd1db78a953566684ab8535fb
```

## 目录

```text
src/sylulive_mcp/
  auth/grants.py                HTTP Bearer Grant 的请求级隔离
  clients/sylulive_api.py       Go 内部 API 与短期 Grant
  data_sources/                 仅供 demo 模式的公开数据加载
  deterministic/               学业和时间确定性算法
  safety/                       URL、路径、输入与敏感字段策略
  schemas/                      严格输入输出模型
  tools/                        8 个生产事实工具
demo/                           不注册到生产 MCP 的本地展示入口
examples/                       公开演示数据
tests/                          契约、协议、安全和算法测试
```

## 许可证

[MIT](LICENSE)
