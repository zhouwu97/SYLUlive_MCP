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
- Go 签发的短期 Grant 由进程配置注入 Authorization Header，不进入模型可见参数。
- 所有工具拒绝未知字段、敏感身份字段、越界路径和超限输入。

## 工具

| 工具 | 职责 |
| --- | --- |
| `system_status` | 返回脱敏状态、架构能力和契约摘要 |
| `policy_search` | 最多用 4 个查询检索 20 条政策片段 |
| `policy_get_sources` | 复核最多 8 个来源的发布状态、有效期和内容哈希 |
| `competition_search` | 按名称或类别检索赛事事实 |
| `competition_get_details` | 获取最多 5 项赛事详情 |
| `competition_compare_facts` | 并列比较事实与画像匹配，不计算总分或推荐 |
| `academic_calculate_summary` | 确定性计算学分、挂科、GPA 透传和完整度 |
| `schedule_find_free_windows` | 扣除固定事件和睡眠后计算空闲窗口 |
| `schedule_validate_plan` | 校验 Agent 候选计划的冲突、超限和未安排时长 |

生产 MCP 不注册 `answer_campus_question`。本地检索展示入口位于 `demo/demo_answer_campus_question.py`，仅用于协议演示，不应被 Agent 加载。

## 运行模式

| 模式 | 行为 |
| --- | --- |
| `disabled` | 默认安全状态，只注册 `system_status` |
| `demo` | 注册全部工具，政策和赛事读取仓库公开样例 |
| `production` | 注册全部工具，政策和赛事通过带短期 Grant 的 Go 内部 API 读取 |

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
uv run sylulive-mcp
```

Agent 连接地址为 `http://sylulive-mcp:8000/mcp`。每个 HTTP 请求的 `Authorization: Bearer <grant>` 会在独立异步上下文中转发给 Go，不会使用模型参数传递。stdio 模式则由 Go 在启动单次 Run 的隔离进程时设置 `SYLULIVE_MCP_GRANT`。

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
```

学业与日程工具接收 Go 已最小化、去身份化的结构化输入并在本地确定性计算，不需要访问数据库。

## LangChain 接入

`langchain-mcp-adapters` 可通过 Streamable HTTP 或 stdio 加载本服务。Agent Service 负责按 Run 只暴露授权工具，并限制工具轮数、单工具次数和最终证据数量。本仓库的 Schema 已将 `policy_search` 限制为每次 4 个 query、20 个结果，将来源复核限制为 8 条。

Go 在接受 Agent 的结构化回答前仍必须验证：

```text
回答引用的 source_id
  ⊆ 本次 policy_search 实际返回的 source_id
  且 policy_get_sources 复核为仍发布、仍有效、内容哈希未变化
```

## 契约与验证

契约版本为 `sylulive-mcp/2`，版本化清单位于 `assets/contracts/sylulive-mcp-v2.json`。

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python scripts/export_contracts.py
uv run python scripts/selfcheck.py
```

`scripts/selfcheck.py` 会启动真实 stdio 子进程，完成 initialize、tools/list 和核心 tools/call。stdout 专用于 MCP JSON-RPC，日志只写入 stderr。

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
