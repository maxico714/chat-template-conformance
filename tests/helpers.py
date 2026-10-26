from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

BASE_VECTOR: dict[str, Any] = {
    "id": "unit-vector",
    "messages": [{"role": "user", "content": "hi"}],
    "template": "{{ messages[0]['content'] }}",
    "expected": {"reference": {"text": "hi"}},
}

STUB_ENGINE = """\
import json
import sys
import time

mode = sys.argv[1]
payload = json.load(sys.stdin)
if mode == "echo":
    print(json.dumps({"text": payload["messages"][0]["content"]}))
elif mode == "tokens":
    print(json.dumps({"token_ids": [7, 8]}))
elif mode == "both":
    print(json.dumps({"text": "hi", "token_ids": [1]}))
elif mode == "invalid-json":
    print("not json")
elif mode == "not-object":
    print(json.dumps([1, 2]))
elif mode == "empty":
    print(json.dumps({}))
elif mode == "bad-text":
    print(json.dumps({"text": 5}))
elif mode == "bad-tokens":
    print(json.dumps({"token_ids": [True]}))
elif mode == "fail":
    print("boom", file=sys.stderr)
    sys.exit(3)
elif mode == "sleep":
    time.sleep(10)
else:
    raise SystemExit(f"unknown mode {mode}")
"""


def make_vector(**overrides: Any) -> dict[str, Any]:
    data = json.loads(json.dumps(BASE_VECTOR))
    data.update(overrides)
    return data


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    env.pop("PYTHONIOENCODING", None)
    return subprocess.run(
        [sys.executable, "-m", "ctp", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd or ROOT),
        env=env,
        timeout=180,
        check=False,
    )
