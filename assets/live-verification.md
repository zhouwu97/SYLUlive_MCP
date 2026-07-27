# Hy3 Live 验证记录

本文件只记录脱敏验证结论。状态统一使用“已验证”“未验证”“失败”“不适用”；不得记录 API Key、
完整环境变量、绝对路径、API Host、模型完整原始响应或其他凭据。真实端点未构造的异常场景必须
保留为“未验证”，不能用自动化测试替代真实端点结论。

| 字段 | 记录值 |
| --- | --- |
| 验证时间（UTC） | 2026-07-27 06:55 |
| SYLUlive_MCP 代码提交 | `c312a9352cd0be89cb7bd3215607320779090d5f` |
| SYLUlive 主服务提交 | `e57a1447e2393899db9844d39186e94d7f7753b8` |
| 包版本 | `0.1.0` |
| Python 版本 | `3.12.10` |
| MCP SDK 版本 | `1.28.1` |
| 客户端 | MCP SDK stdio；SYLUlive Go MCP 客户端 |
| Hy3 模型名 | 已脱敏 |
| API Host | 已脱敏且未写入仓库 |
| `HY3_MODE` | `live` |
| Fixture 已关闭 | 已验证 |
| Bundle SHA-256 | `2b93e4b02819497f821bddb73c5a5cb6e5fe711379e1986c19cccaa0cb4f7b2d`（`newline-lf-v1` 规范化摘要） |
| Manifest 文件 SHA-256 | `155320f6a0ea4da8494eb16c7b37aacbd739d4913bdd412cf0709d2b23a90a79` |

## 1. 真实调用与协议

| 范围 | 状态 | 脱敏结论 |
| --- | --- | --- |
| 四个核心工具真实 Hy3 调用 | 已验证 | 第一轮 16 次中 15 次成功，1 次 `hy3_output_invalid` |
| 已知互斥问题修复后复核 | 已验证 | 5 次中 4 次成功，1 次 `hy3_request_failed`，无 `hy3_output_invalid` |
| 输出 Schema 与来源白名单 | 已验证 | 成功响应通过严格模型与来源 ID 校验 |
| Go 到 Python MCP 的真实 stdio 契约 | 已验证 | 三个远端核心工具的列表、状态摘要与 Go 固定摘要一致 |
| Fixture 参与真实端点矩阵 | 不适用 | `Fixture=false` |

App 的正式政策检索继续使用生产 Go RAG；独立 MCP 的 v0.8 Bundle 用于便携演示、离线验证和
跨客户端能力。两者共享 `policy_query_contract_v0.8.json`，不应描述为 App 的全部政策问答都经由
外部 Hy3 MCP。

## 2. 非法输出与重试

| 场景 | 状态 | 记录 |
| --- | --- | --- |
| 非法 JSON | 已验证（自动化） | 最多追加一次 JSON 修复提示，仍失败返回 `hy3_output_invalid` |
| 合法 JSON 但 Schema 不符 | 已验证（自动化） | 最多重试一次，仍失败返回 `hy3_schema_invalid` |
| 来源 ID 越界 | 已验证（自动化） | 立即返回 `hy3_source_reference_invalid`，不重试 |
| 传输错误后的请求内容 | 已验证（自动化） | 不追加与传输故障无关的 Schema 修复提示 |

## 3. 端点异常

| 场景 | 自动化状态 | 真实端点状态 | 期望行为 |
| --- | --- | --- | --- |
| HTTP 401 / 403 | 已验证 | 未验证 | `hy3_auth_failed`，不重试 |
| HTTP 429 | 已验证 | 未验证 | `hy3_rate_limited`，短退避后最多重试一次 |
| HTTP 500 | 已验证 | 未验证 | `hy3_server_error`，短退避后最多重试一次 |
| 请求超时 | 已验证 | 未验证 | `hy3_timeout`，立即失败 |
| 连接中断 | 已验证 | 未验证 | `hy3_connection_failed`，短退避后最多重试一次 |
| Bundle 或契约摘要不一致 | 已验证 | 不适用 | `policy_bundle_integrity_failed`，不得伪装为无资料 |

## 4. 响应内容边界

| 场景 | 状态 | 记录 |
| --- | --- | --- |
| 超长字段 | 已验证（自动化） | 由 Pydantic 长度约束拒绝 |
| 额外未声明字段 | 已验证（自动化） | 由严格输出模型拒绝 |
| 错误或不存在的来源 ID | 已验证（自动化） | 由 `allowed_source_ids` 拒绝 |
| 数值越界 | 已验证（自动化） | 由输入模型和确定性复核拒绝 |

## 5. 参数兼容性

| 项目 | 状态 | 记录 |
| --- | --- | --- |
| `chat_template_kwargs.reasoning_effort` | 已验证 | 真实成功调用接受该字段 |
| `response_format` | 已验证 | 真实成功调用接受 JSON object 模式 |
| 不接受参数时的降级路径 | 未验证 | 本轮未在真实端点构造不兼容响应 |
| temperature | 已验证 | 使用仓库配置值，不在验证记录中覆盖 |

自动化复核命令：

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python scripts/validate_examples.py
uv run python scripts/selfcheck.py
```

跨仓库 stdio 测试要求调用本机已安装的 MCP 可执行文件；具体绝对路径不写入仓库。
