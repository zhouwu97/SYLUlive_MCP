# Hy3 Campus Decision Copilot

`SYLUlive_MCP` 是一个独立运行的标准 MCP Server，用于在本地示例数据上提供校园政策问答、竞赛比较、学业快照分析和周计划建议。

项目不连接 SYLUlive Flutter 客户端、Go 后端、PostgreSQL、学生账号或教务系统。第一版只支持 stdio transport，并通过 `HY3_MODE` 明确区分真实 Hy3、固定 Fixture 与禁用模式。

## 快速开始

```powershell
uv sync
$env:HY3_MODE = "fixture"
uv run hy3-campus-decision-mcp
```

默认 `HY3_MODE=disabled`，此时只注册 `hy3_campus_status`。使用 Fixture 模式进行本地演示和测试：

```powershell
$env:HY3_MODE = "fixture"
$env:HY3_FIXTURE_ROOT = "./tests/fixtures/hy3"
uv run pytest -q
```

真实 Hy3 调用需要显式配置 `HY3_MODE=live`、`HY3_API_BASE` 和 `HY3_API_KEY`。详见 [`.env.example`](.env.example)。

## 开发命令

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/selfcheck.py
uv run python scripts/sdk_stdio_client.py
```

## 安全边界

- 仅接受 `HY3_CAMPUS_ROOT` 内的相对路径。
- 在发送给模型前递归拒绝学号、姓名、Cookie、令牌等敏感字段。
- API Key、绝对路径和完整模型原文不会写入日志或工具结果。
- 示例政策和赛事数据仅用于演示，不代表学校正式发布内容。

## 许可证

[MIT](LICENSE)
