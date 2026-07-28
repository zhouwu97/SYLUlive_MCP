from pathlib import Path

WRAPPER = Path(__file__).parents[1] / "bin" / "run-stdio"


def test_stdio_wrapper_is_lf_only() -> None:
    content = WRAPPER.read_bytes()

    assert content.startswith(b"#!/bin/sh\n")
    assert b"\r\n" not in content


def test_stdio_wrapper_uses_relocatable_python_module_entrypoint() -> None:
    content = WRAPPER.read_text(encoding="utf-8")

    assert "/opt/SYLUlive_MCP/.venv/bin/python -m hy3_campus_decision_mcp" in content
    assert "/opt/SYLUlive_MCP/.venv/bin/hy3-campus-decision-mcp" not in content
