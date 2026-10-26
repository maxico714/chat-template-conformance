"""Minimal `ctp` command engine used by the README example.

It reads the vector payload from stdin and writes a JSON object with a `text` field.
It is a protocol demonstration, not a chat-template engine: it never evaluates the
template, so it only passes vectors whose expectation is the first message's content.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def main() -> int:
    payload: dict[str, Any] = json.load(sys.stdin)
    messages = payload.get("messages") or []
    text = messages[0].get("content") if messages else ""
    sys.stdout.write(json.dumps({"text": text}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
