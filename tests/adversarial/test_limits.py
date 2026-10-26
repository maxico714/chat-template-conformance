from __future__ import annotations

import json
import sys
from pathlib import Path

from helpers import make_vector, run_cli

from ctp.schema import MAX_MESSAGES


def write(tmp_path: Path, data: dict[str, object], name: str = "vector.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_malformed_json_is_a_schema_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{"id": 1,}', encoding="utf-8")
    result = run_cli("validate", "--vector", str(path))
    assert result.returncode == 2
    assert "E_SCHEMA" in result.stderr
    assert "line 1" in result.stderr


def test_oversized_vector_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_bytes(b" " * 2_000_001)
    result = run_cli("validate", "--vector", str(path))
    assert result.returncode == 2
    assert "max" in result.stderr


def test_huge_token_list_is_rejected_before_rendering(tmp_path: Path) -> None:
    data = make_vector(expected={"reference": {"token_ids": [0] * 100_001}})
    result = run_cli("validate", "--vector", str(write(tmp_path, data)))
    assert result.returncode == 2
    assert "token_ids" in result.stderr


def test_too_many_messages_are_rejected(tmp_path: Path) -> None:
    data = make_vector(messages=[{"role": "user", "content": "x"}] * (MAX_MESSAGES + 1))
    result = run_cli("validate", "--vector", str(write(tmp_path, data)))
    assert result.returncode == 2
    assert "messages" in result.stderr


def test_sandbox_escape_attempt_is_blocked(tmp_path: Path) -> None:
    data = make_vector(
        template="{{ ''.__class__.__mro__ }}",
        expected={"reference": {"text": ""}},
    )
    result = run_cli("validate", "--vector", str(write(tmp_path, data)))
    assert result.returncode == 2
    assert "ERROR unit-vector [reference]" in result.stdout
    assert "SecurityError" in result.stdout


def test_env_mismatch_warns_but_does_not_fail(tmp_path: Path) -> None:
    data = make_vector(env={"jinja2": "0.0.1", "python": "2.7.18"})
    result = run_cli("validate", "--vector", str(write(tmp_path, data)))
    assert result.returncode == 0
    assert "WARN unit-vector: env.jinja2" in result.stdout
    assert "WARN unit-vector: env.python" in result.stdout
    assert result.stdout.rstrip().endswith("OK")


def test_engine_that_exits_nonzero_is_reported(tmp_path: Path, stub_script: Path) -> None:
    data = make_vector(expected={"stub": {"text": "hi"}})
    result = run_cli(
        "validate",
        "--vector",
        str(write(tmp_path, data)),
        "--engine",
        "command:stub",
        "--command",
        sys.executable,
        "--command-arg",
        str(stub_script),
        "--command-arg",
        "fail",
    )
    assert result.returncode == 3
    assert "exited with 3" in result.stdout
    assert "boom" in result.stdout


def test_engine_that_writes_garbage_is_reported(tmp_path: Path, stub_script: Path) -> None:
    data = make_vector(expected={"stub": {"text": "hi"}})
    result = run_cli(
        "validate",
        "--vector",
        str(write(tmp_path, data)),
        "--engine",
        "command:stub",
        "--command",
        sys.executable,
        "--command-arg",
        str(stub_script),
        "--command-arg",
        "invalid-json",
    )
    assert result.returncode == 3
    assert "invalid JSON" in result.stdout


def test_non_utf8_vector_is_a_schema_error(tmp_path: Path) -> None:
    path = tmp_path / "binary.json"
    path.write_bytes(b"\xff\xfe{}")
    result = run_cli("validate", "--vector", str(path))
    assert result.returncode == 2
    assert "E_SCHEMA" in result.stderr
