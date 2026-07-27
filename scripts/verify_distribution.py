"""在全新虚拟环境中验证 wheel 的 CLI、资源和 stdio 自检。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(command: list[str], *, cwd: Path) -> str:
    """执行隔离验证命令并返回标准输出。"""

    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main() -> None:
    """安装唯一 wheel，并验证安装产物不依赖源码目录。"""

    project_root = Path(__file__).resolve().parents[1]
    wheels = list((project_root / "dist").glob("hy3_campus_decision_mcp-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"dist 中应存在一个待验证 wheel，实际为 {len(wheels)} 个")

    with tempfile.TemporaryDirectory(prefix="hy3-campus-wheel-") as temporary:
        root = Path(temporary)
        environment = root / ".venv"
        _run(["uv", "venv", "--python", sys.executable, str(environment)], cwd=root)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        executable = environment / (
            "Scripts/hy3-campus-decision-mcp.exe"
            if sys.platform == "win32"
            else "bin/hy3-campus-decision-mcp"
        )
        _run(["uv", "pip", "install", "--python", str(python), str(wheels[0])], cwd=root)
        version = _run([str(executable), "--version"], cwd=root)
        selfcheck = json.loads(_run([str(executable), "--selfcheck"], cwd=root))
        if selfcheck.get("status") != "ok" or selfcheck.get("tool_count") != 5:
            raise RuntimeError("安装后 stdio 自检未发现完整工具集")

    print(json.dumps({"status": "ok", "version": version, "tool_count": 5}))


if __name__ == "__main__":
    main()
