# Hy3 Live 验证记录

本文件是 Live 验证的提交记录模板。仅当 `HY3_MODE=live`、Fixture 未参与、四个核心工具均通过后填写；不得记录 API Key、完整环境变量、绝对路径或模型原始响应。

| 字段 | 记录值 |
| --- | --- |
| 验证时间（UTC） | 未执行 |
| SYLUlive_MCP 提交 SHA | 未执行 |
| 包版本 | `0.1.0` |
| Python 版本 | 未执行 |
| MCP SDK 版本 | 未执行 |
| 客户端名称与版本 | 未执行 |
| Hy3 模型名 | 未执行 |
| API Host 脱敏值 | 未执行 |
| `HY3_MODE` | `live` |
| Fixture 已关闭 | 未执行 |

## 工具结果

| 工具 | 真实调用 | Schema 校验 | 确定性复核 |
| --- | --- | --- | --- |
| `answer_campus_question` | 未执行 | 未执行 | 来源引用未执行 |
| `compare_competitions` | 未执行 | 未执行 | 四维结果未执行 |
| `analyze_academic_snapshot` | 未执行 | 未执行 | 学分与挂科未执行 |
| `plan_student_week` | 未执行 | 未执行 | 冲突与睡眠保护未执行 |

执行命令：

```powershell
$env:HY3_MODE = "live"
$env:HY3_API_BASE = "https://your-hy3-host/v1"
$env:HY3_API_KEY = "<redacted>"
$env:HY3_MODEL = "hy3"
uv run python scripts/verify_live_hy3.py
```
