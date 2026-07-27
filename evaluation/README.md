# 可复现可靠性评测

本目录包含 30 个确定性护栏案例和 5 个完整 MCP 协议案例。前者直接验证可客观判定的计算与安全属性，后者使用官方 MCP SDK 实际启动 stdio 子进程，执行 `initialize -> tools/list -> tools/call`。两组评测都不把 Fixture 输出冒充真实 Hy3 效果，也不使用“回答更好”等主观指标。

| 类别 | 案例数 | 核验内容 |
| --- | ---: | --- |
| 学业分析 | 10 | 挂科、必修挂科学分、缺失字段、学分缺口的确定性结果 |
| 周计划 | 10 | 固定事件、睡眠、最小时间块、每日上限和计划重叠 |
| 竞赛比较 | 5 | 学校认定、人工评价、学生适配、证据质量四维分离 |
| 安全边界 | 5 | 路径穿越、绝对路径、非法路径、缺失来源和敏感字段拒绝 |

运行并更新结果：

```powershell
uv run python evaluation/run_evaluation.py
```

检查已提交结果是否与当前代码一致：

```powershell
uv run python evaluation/run_evaluation.py --check
```

运行 5 个完整 MCP 协议案例并更新机器可读结果：

```powershell
uv run python scripts/sdk_stdio_client.py --write
```

检查协议结果：

```powershell
uv run python scripts/sdk_stdio_client.py --check
```

协议案例覆盖五个工具发现、学业分析、竞赛四维分离、无硬约束违规的周计划，以及 `../secret.env` 返回稳定的 `path_traversal_rejected`。结果分别保存在 `results.json` 和 `mcp-results.json`。

真实 Hy3 Live 验证单独记录在 `assets/live-verification.md`。直接模型基线必须使用同一批提示、真实 API 和人工标注后才能发布；在这些条件满足前，本项目不会生成虚假的对照数字。
