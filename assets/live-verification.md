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
