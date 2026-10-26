from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from helpers import STUB_ENGINE


@pytest.fixture
def write_vector(tmp_path: Path) -> Callable[..., Path]:
    def _write(data: dict[str, Any], name: str = "vector.json") -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def stub_script(tmp_path: Path) -> Path:
    path = tmp_path / "stub_engine.py"
    path.write_text(STUB_ENGINE, encoding="utf-8", newline="\n")
    return path
