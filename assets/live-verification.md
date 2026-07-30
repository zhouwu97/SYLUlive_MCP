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

## 2026-07-28 14:38 UTC

| 字段 | 记录值 |
| --- | --- |
| SYLUlive `diaofenyuan` 实现 | `51f41de8cbf3f6761ddbdfc96b781ad3f6a65549` |
| Go 1.25 Linux/amd64 二进制 SHA-256 | `5040ffd609c98babe1d281e38838ef212f2fee52b6b851b924b67a1f8b409440` |
| MCP 生产标签 | `sylulive-mcp-prod-20260728`，指向 `765a5b634f18aaa616b3c424462572651c54b034` |
| `/health` 外部 MCP 状态 | configured、healthy，Live 模式，契约 `sylulive-hy3/1`，三个工具 |
| 登录态 capabilities | 匿名 401 已验证；登录态工具明细待专用测试账号验证 |

本次后端部署使公开健康接口直接反映已验证 MCP Session 与实际 Go ToolRegistry，不再以
`AI_EXTERNAL_MCP_ENABLED` 单独推导健康或工具数量。

### 非破坏性故障矩阵

| 场景 | 自动化结果 |
| --- | --- |
| 本地 MCP 包装器不存在 | `external_mcp_unavailable`，client 保持不健康 |
| MCP Session 调用时断开 | 当前调用失败，后续调用重新握手成功 |
| MCP 调用超时 | `external_mcp_timeout`，旧 Session 被清理 |
| 生产工具 Schema 漂移 | 不兼容工具不进入 Go ToolRegistry |
| MCP 工具返回超大或无效 JSON | Go 在 128 KiB 上限拒绝结果 |
| Hy3 401 / 403 | `hy3_auth_failed` |
| Hy3 429 | `hy3_rate_limited` |
| Hy3 5xx | `hy3_upstream_unavailable` |
| Hy3 超时 | `hy3_timeout`，错误不含 API Key |
| Hy3 原始响应超过限制 | JSON 解析前以 `hy3_output_too_large` 拒绝 |
| 周计划与课程冲突 | Go 本地确定性复核拒绝远端计划 |
| 外部分析授权关闭 | 读取个人快照前停止，不调用远端工具 |

以上结果来自隔离测试进程和 MockTransport，不会中断生产服务。独立预生产 systemd 实例上的
真实 Provider 故障注入仍未执行，因此“真实端点故障注入”继续保持未验证。

## 2026-07-30 本地部署前门禁

本节只记录当前本地工作区的验证，不表示新契约已经部署到生产。

| 字段 | 记录值 |
| --- | --- |
| 纯工具契约 | `sylulive-mcp/5` |
| 纯工具包版本 | `0.5.0` |
| Hy3 契约 | `sylulive-hy3/2` |
| Hy3 包版本 | `0.2.0` |
| Python 测试 | `63 passed` |
| Ruff | format 与 lint 均通过 |
| Fixture stdio | 五个生产工具逐项调用通过 |
| `sylulive-mcp-v5.json` | `21bdd92b4988f29bca9f6b6f4c3170e4d8ebe702745f09f26782587cb9fc5973` |
| `sylulive-hy3-v2.json` | `e0afd2958c097c255933c1ac826e81dc75fe30ac7ccd9039cbb2a49916a4042a` |

Hy3 五个固定工具及 Schema SHA-256：

```text
compare_competitions
  183668200d82156e6385342d747d229e5ab8fe49ba4351afaf8fccc9c896905c
explain_competition_candidates
  869bed351400771f7272b5c05b97d2c20875c7ddff0db65cb9d064b5c1f84721
compare_selected_competitions
  b8e151f2e964f96dcbc5d533632da63f5adf9b7106f681d861edb7f05cc0b463
analyze_academic_snapshot
  fc50ff6b196c409d59df53df777f49b265fd4bfa66e34969e5787527a38fad23
plan_student_week
  0cb4a9c774ea6799b8f95945d89c21195c0cb228315ab73fd849259814cc7518
```

生产部署仍需重新验证服务器上的提交、包装器、健康状态、工具注册和 Go 固定摘要。
