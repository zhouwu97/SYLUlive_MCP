"""通过真实 stdio 协议执行本地 Fixture 自检。"""

from __future__ import annotations

import asyncio
import json

from sdk_stdio_client import verify_stdio_protocol


def main() -> None:
    """执行异步自检并输出精简结果。"""

    print(json.dumps(asyncio.run(verify_stdio_protocol()), ensure_ascii=False))


if __name__ == "__main__":
    main()
