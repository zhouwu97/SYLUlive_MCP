# Hy3 Live 验证记录

本文件是 Live 验证的提交记录模板。仅当 `HY3_MODE=live`、Fixture 未参与、四个核心工具与全部
异常场景均通过后填写；不得记录 API Key、完整环境变量、绝对路径或模型原始响应。

**只要本文件还存在“未执行”，就不得把主服务的 `AI_EXTERNAL_MCP_ENABLED` 置为 `true`。**
离线 Fixture 与协议测试只能证明链路可运行，不能证明真实端点的参数、`reasoning_effort`、
`response_format`、响应字段和超时行为兼容。

| 字段 | 记录值 |
| --- | --- |
| 验证时间（UTC） | 未执行 |
| SYLUlive_MCP 提交 SHA | 未执行 |
| SYLUlive 主服务提交 SHA | 未执行 |
| 包版本 | `0.1.0` |
| Python 版本 | 未执行 |
| MCP SDK 版本 | 未执行 |
| 客户端名称与版本 | 未执行 |
| Hy3 模型名 | 未执行 |
| API Host 脱敏值 | 未执行 |
| `HY3_MODE` | `live` |
| Fixture 已关闭 | 未执行 |

## 1. 工具真实调用

| 工具 | 真实调用 | Schema 校验 | 确定性复核 |
| --- | --- | --- | --- |
| `answer_campus_question` | 未执行 | 未执行 | 来源引用未执行 |
| `compare_competitions` | 未执行 | 未执行 | 四维结果未执行 |
| `analyze_academic_snapshot` | 未执行 | 未执行 | 学分与挂科未执行 |
| `plan_student_week` | 未执行 | 未执行 | 冲突与睡眠保护未执行 |

## 2. 非法输出与重试

| 场景 | 期望行为 | 记录 |
| --- | --- | --- |
| 模型返回非法 JSON | 重试一次；仍失败返回结构化错误，不得伪造结果 | 未执行 |
| 重试后成功 | 只记一次成功，不重复调用下游工具 | 未执行 |

## 3. 端点异常

| 场景 | 期望行为 | 记录 |
| --- | --- | --- |
| HTTP 401 | 稳定错误码，不重试，不落盘 Key | 未执行 |
| HTTP 429 | 稳定错误码，按退避处理，不无限重试 | 未执行 |
| HTTP 500 | 稳定错误码，Go 侧降级到本地确定性结果 | 未执行 |
| 请求超时 | 在配置的超时内中断，返回超时错误码 | 未执行 |
| 连接中断 | 会话可重建或明确降级，不留下悬挂 Run | 未执行 |

## 4. 响应内容边界

| 场景 | 期望行为 | 记录 |
| --- | --- | --- |
| 超长字段 | 被长度约束截断或拒绝，不进入信封 | 未执行 |
| 额外未声明字段 | 被 `additionalProperties=false` 拒绝 | 未执行 |
| 错误或不存在的来源 ID | 被 `allowed_source_ids` 拒绝 | 未执行 |
| 数值越界（学分、节次、活动数） | 被确定性复核拒绝 | 未执行 |

## 5. 参数兼容性

| 项目 | 记录 |
| --- | --- |
| 真实端点是否接受 `chat_template_kwargs.reasoning_effort` | 未执行 |
| 不接受时的降级路径是否生效 | 未执行 |
| 真实端点是否接受 `response_format` | 未执行 |
| 实际生效的 temperature | 未执行 |

执行命令：

```powershell
$env:HY3_MODE = "live"
$env:HY3_API_BASE = "https://your-hy3-host/v1"
$env:HY3_API_KEY = "<redacted>"
$env:HY3_MODEL = "hy3"
uv run python scripts/verify_live_hy3.py
```

第 2 至第 5 节需要人工构造异常场景（例如临时把 `HY3_API_BASE` 指向一个返回固定状态码的
本地代理），脚本不会自动伪造真实端点的 429、500 或超时。
