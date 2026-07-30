"""生成并写入已版本化的 MCP 工具契约清单。"""

from __future__ import annotations

import json

from hy3_campus_decision_mcp.contracts import (
    build_contract_manifest as build_hy3_contract_manifest,
)
from hy3_campus_decision_mcp.contracts import (
    committed_manifest_path as hy3_committed_manifest_path,
)
from sylulive_mcp.contracts import (
    build_contract_manifest as build_mcp_contract_manifest,
)
from sylulive_mcp.contracts import (
    committed_manifest_path as mcp_committed_manifest_path,
)


def _write_manifest(target: object, manifest: dict[str, object]) -> None:
    """使用稳定格式写入单个版本化契约清单。"""

    path = target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """将纯 MCP 与 Hy3 运行时 Schema 一并提交为跨仓库契约。"""

    _write_manifest(
        mcp_committed_manifest_path(),
        build_mcp_contract_manifest(),
    )
    _write_manifest(
        hy3_committed_manifest_path(),
        build_hy3_contract_manifest(),
    )


if __name__ == "__main__":
    main()
