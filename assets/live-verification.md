# Hy3 Live 验证记录

本文件仅记录脱敏结论，不保存 API Key、Authorization、服务器地址、绝对路径、原始模型
响应或个人数据。

## 2026-07-28 12:55 UTC

| 字段 | 记录值 |
| --- | --- |
| SYLUlive `diaofenyuan` | `2efb524fb3090f877a8205dca63dd6200e745e8a` |
| 远端 MCP 源码基线 | `0a2dafdfa3c41c06d31b727fb777707fa29a223e`，工作树存在未提交契约修改 |
| 本地实现基线 | `765a5b634f18aaa616b3c424462572651c54b034`，包装器模块入口待部署确认 |
| 契约版本 | `sylulive-hy3/1` |
| Python 包版本 | `0.1.0` |
| MCP SDK 版本 | `1.28.1` |
| Provider 协议 | `anthropic_messages` |
| Provider Host | 已脱敏 |
| Fixture 回退 | 未发生，成功结果均标记 `mode=live` |

### 工具调用

| 工具 | 状态 | Schema | 推理强度 |
| --- | --- | --- | --- |
| `compare_competitions` | 已验证 | `1` | `low` |
| `analyze_academic_snapshot` | 已验证 | `1` | `high` |
| `plan_student_week` | 已验证 | `1` | `high` |
| `answer_campus_question` | 失败 | `hy3_schema_invalid` | 未接受结果 |

三个生产工具使用公开 Fixture 输入顺序执行，均返回严格结构化成功信封。便携问答工具在两次
有界尝试后仍未满足输出 Schema，因此结果被拒绝；该失败不影响 `sylulive_runtime` 的三个
生产工具，但 portable Live 验证仍未通过。

### 协议与防护

| 项目 | 状态 |
| --- | --- |
| Go SDK 真实 stdio 契约测试 | 已验证 |
| 三个生产工具 Schema SHA-256 | 已验证，与 Go 固定摘要一致 |
| `chat_template_kwargs.reasoning_effort` | OpenAI 路径自动化已验证；本次 Anthropic 路径不适用 |
| Anthropic `/messages` 请求结构 | 自动化已验证 |
| 401 / 403、429、5xx、超时、连接错误分类 | 自动化已验证 |
| 128 KiB 原始响应流式限制 | 自动化已验证，远端候选版本已部署 |
| 真实端点故障注入 | 未验证 |
| 安全 `env -i` 包装器 | 本地候选已具备，远端模块入口待部署确认 |

### 上线判定

远端后端审计时已设置 `AI_EXTERNAL_MCP_ENABLED=true`，早于本地候选版本部署。由于远端
部署目录不可追溯到单一干净提交，且 portable 问答与真实故障注入仍未通过，本记录不构成
全量生产验收。部署本地候选版本、复核三项生产工具并验证降级前，不应扩大流量。

## 2026-07-28 13:58 UTC

| 字段 | 记录值 |
| --- | --- |
| MCP 实现基线 | `765a5b634f18aaa616b3c424462572651c54b034` |
| stdio 包装器 | LF 已验证；使用固定生产 Python 模块入口，不依赖可搬迁的 console-script shebang |
| MCP 握手 | `initialize` 通过，协议版本 `2025-06-18` |
| 工具注册 | 状态工具及三个生产工具已精确注册，无额外工具 |
| MCP 状态 | `mode=live`、`tool_profile=sylulive_runtime`、`contract_version=sylulive-hy3/1` |
| Go 启动健康检查 | 已通过，MCP 子进程由 Go 主进程持有 |
| 后端健康检查 | `/health` 返回 200，AI runtime 已启用 |
| 能力接口 | 路由存在；匿名请求按预期返回 401，登录态工具明细未在本次验证 |
| 回滚点 | 启用前配置已备份，旧 MCP 部署目录仍保留 |

### 部署产物摘要

服务器未从 wheel 安装，也未保留 Git 元数据。本次实际运行产物由 `fca990c` 源码归档和
`765a5b6` 的 stdio 包装器修复组成；后者是两者之间唯一影响运行时的代码变更。

| 产物 | SHA-256 |
| --- | --- |
| `sylulive-mcp-fca990c.tar.gz` | `88980d0ba99745e97683736e0bed7914da1149dbd1ffd235ba20f7ff637bf01e` |
| 生产 `bin/run-stdio` | `8ad235494dca70e186f61c470d1971f734c898e68e27f59b2ce8d8bb6c422051` |
| `assets/contracts/sylulive-hy3-v1.json` | `51668ddf302f47d0cd8b9f053088cf59ed2f5b4c5e242380d32299abfa0bc7d4` |
| `assets/contracts/sylulive-mcp-v2.json` | `540e8aea7a3fb40f2d5d7f47f8dea6c0f12eea60ec48141056d9f5d57caafff8` |
| `assets/contracts/sylulive-mcp-v3.json` | `07896383a5c9a491f4a4239a3bfdaf0e27e44460e143b24887926296d118ffec` |
| `shenliyuan.service` | `897a109bc58c65233d29e2d5d1e4bd5ed0fcd52d578601fdb854732378649ca7` |
| 脱敏外部 MCP 运行配置文件 | `2b1df86745779ad60cbb53912b8ca0a415dfe8930a81a4c09cc23c64cd23d989` |

生产标签 `sylulive-mcp-prod-20260728` 精确指向 `765a5b6`。该标签固定运行时实现，后续
验证记录提交不移动此标签。运行配置摘要仅用于检测服务器配置漂移，不公开配置内容。

本次启用仅确认生产 stdio 链路、契约注册和进程生命周期。portable 问答工具不属于
`sylulive_runtime`，其 Live Schema 失败不影响本次三个生产工具的注册状态；真实故障注入和
登录态业务入口仍需单独验收。
