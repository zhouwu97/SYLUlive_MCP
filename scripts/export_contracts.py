"""生成并写入已版本化的 MCP 工具契约清单。"""

from __future__ import annotations

import json

from sylulive_mcp.contracts import build_contract_manifest, committed_manifest_path


def main() -> None:
    """将运行时代码生成的 Schema 提交为跨仓库契约。"""

    target = committed_manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_contract_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
