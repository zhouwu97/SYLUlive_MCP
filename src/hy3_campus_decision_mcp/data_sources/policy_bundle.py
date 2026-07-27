"""v0.8 政策包的完整性检查与脱敏状态。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..errors import CampusMcpError

POLICY_BUNDLE_VERSION = "v0.8"
POLICY_BUNDLE_FILE = "sylulive-policy-bundle-v0.8.jsonl"
POLICY_CONTRACT_FILE = "policy_query_contract_v0.8.json"
POLICY_MANIFEST_FILE = "policy-bundle-manifest.json"


def inspect_policy_bundle(campus_root: Path, *, strict: bool = False) -> dict[str, Any]:
    """校验政策包，并只返回版本、摘要和加载状态。"""

    root = campus_root / "policy_bundle"
    empty_status = {
        "policy_bundle_loaded": False,
        "policy_bundle_version": None,
        "policy_bundle_sha256": None,
        "intent_contract_loaded": False,
    }
    if not root.exists():
        return empty_status

    try:
        bundle = (root / POLICY_BUNDLE_FILE).read_bytes()
        contract = (root / POLICY_CONTRACT_FILE).read_bytes()
        manifest = json.loads((root / POLICY_MANIFEST_FILE).read_text(encoding="utf-8"))
        bundle_sha = hashlib.sha256(bundle).hexdigest()
        contract_sha = hashlib.sha256(contract).hexdigest()
        valid = (
            manifest.get("version") == POLICY_BUNDLE_VERSION
            and bundle_sha == manifest.get("documents_sha256")
            and contract_sha == manifest.get("intent_contract_sha256")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        valid = False
        bundle_sha = None

    if not valid:
        if strict:
            raise CampusMcpError(
                "policy_bundle_integrity_failed",
                "The local policy bundle failed its integrity check.",
            )
        return empty_status

    return {
        "policy_bundle_loaded": True,
        "policy_bundle_version": POLICY_BUNDLE_VERSION,
        "policy_bundle_sha256": bundle_sha,
        "intent_contract_loaded": True,
    }
