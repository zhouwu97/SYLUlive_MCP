"""兼容原开发命令的安装后 Fixture 自检包装器。"""

from __future__ import annotations

from hy3_campus_decision_mcp.__main__ import main as package_main


def main() -> None:
    """调用包内自检，确保脚本和正式 CLI 使用同一实现。"""

    package_main(["--selfcheck"])


if __name__ == "__main__":
    main()
