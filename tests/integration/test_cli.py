from __future__ import annotations

import json
import sys
from pathlib import Path

from helpers import ROOT, run_cli


def read_seed(name: str) -> dict[str, object]:
    return json.loads((ROOT / "vectors" / name).read_text(encoding="utf-8"))


def test_version() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "ctp 0.1.0"


def test_no_arguments_exits_with_usage_error() -> None:
    result = run_cli()
    assert result.returncode == 4
    assert "usage:" in result.stderr


def test_validate_seed_vector_passes() -> None:
    result = run_cli("validate", "--vector", "vectors/001-chatml-basic.json")
    assert result.returncode == 0, result.stderr
    assert "PASS 001-chatml-basic [reference]" in result.stdout
    assert result.stdout.rstrip().endswith("OK")


def test_validate_reports_mismatch_with_exit_code_one(tmp_path: Path) -> None:
    vector = read_seed("001-chatml-basic.json")
    vector["expected"]["reference"]["text"] = "wrong"  # type: ignore[index]
    path = tmp_path / "mismatch.json"
    path.write_text(json.dumps(vector), encoding="utf-8")
    result = run_cli("validate", "--vector", str(path))
    assert result.returncode == 1
    assert "FAIL 001-chatml-basic [reference]" in result.stdout
    assert "text differs at char 0" in result.stdout


def test_schema_error_exits_two(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    result = run_cli("validate", "--vector", str(path))
    assert result.returncode == 2
    assert "E_SCHEMA" in result.stderr


def test_missing_vector_file_exits_two(tmp_path: Path) -> None:
    result = run_cli("validate", "--vector", str(tmp_path / "absent.json"))
    assert result.returncode == 2
    assert "E_SCHEMA" in result.stderr


def test_unknown_engine_exits_four() -> None:
    result = run_cli("validate", "--vector", "vectors/001-chatml-basic.json", "--engine", "bogus")
    assert result.returncode == 4
    assert "E_CONFIG" in result.stderr


def test_command_arg_without_command_exits_four() -> None:
    result = run_cli("validate", "--vector", "vectors/001-chatml-basic.json", "--command-arg", "x")
    assert result.returncode == 4
    assert "E_CONFIG" in result.stderr


def test_validate_dir_on_seed_vectors() -> None:
    result = run_cli("validate-dir", "vectors")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("PASS ") == 13
    assert "13 vectors, 13 engine checks: 13 matched, 0 mismatched, 0 errors" in result.stdout


def test_validate_dir_reports_bad_vector(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    result = run_cli("validate-dir", str(tmp_path))
    assert result.returncode == 2
    assert "ERROR bad [schema]" in result.stdout


def test_validate_dir_missing_directory_exits_two(tmp_path: Path) -> None:
    result = run_cli("validate-dir", str(tmp_path / "missing"))
    assert result.returncode == 2


def test_json_output_has_summary() -> None:
    result = run_cli("validate-dir", "vectors", "--json")
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)["summary"]
    assert summary["vectors"] == 13
    assert summary["engines_checked"] == 13
    assert summary["matched"] == 13
    assert summary["mismatched"] == 0
    assert summary["errors"] == 0


def test_sarif_file_written_for_failures(tmp_path: Path) -> None:
    vector = read_seed("001-chatml-basic.json")
    vector["expected"]["reference"]["text"] = "wrong"  # type: ignore[index]
    vector_path = tmp_path / "v.json"
    vector_path.write_text(json.dumps(vector), encoding="utf-8")
    sarif_path = tmp_path / "out.sarif"
    result = run_cli("validate", "--vector", str(vector_path), "--sarif", str(sarif_path))
    assert result.returncode == 1
    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"][0]["ruleId"] == "CTP001"


def test_sarif_green_run_has_no_results(tmp_path: Path) -> None:
    sarif_path = tmp_path / "green.sarif"
    result = run_cli("validate-dir", "vectors", "--sarif", str(sarif_path))
    assert result.returncode == 0
    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert payload["runs"][0]["results"] == []


def test_render_preserves_unicode() -> None:
    result = run_cli("render", "--vector", "vectors/009-unicode-content.json")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "héllo 世界 🙂\n"


def test_render_error_exits_two(tmp_path: Path) -> None:
    vector = {
        "id": "broken",
        "messages": [{"role": "user", "content": "hi"}],
        "template": "{% if %}",
        "expected": {"reference": {"text": ""}},
    }
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(vector), encoding="utf-8")
    result = run_cli("render", "--vector", str(path))
    assert result.returncode == 2
    assert "E_RENDER" in result.stderr


def test_doctor_reports_versions_and_no_network() -> None:
    result = run_cli("doctor")
    assert result.returncode == 0
    assert "ctp 0.1.0" in result.stdout
    assert "jinja2" in result.stdout
    assert "network: none" in result.stdout


def test_command_engine_end_to_end(tmp_path: Path, stub_script: Path) -> None:
    vector = {
        "id": "stub-vector",
        "messages": [{"role": "user", "content": "hi"}],
        "template": "{{ messages[0]['content'] }}",
        "expected": {"stub": {"text": "hi"}},
    }
    path = tmp_path / "stub.json"
    path.write_text(json.dumps(vector), encoding="utf-8")
    result = run_cli(
        "validate",
        "--vector",
        str(path),
        "--engine",
        "command:stub",
        "--command",
        sys.executable,
        "--command-arg",
        str(stub_script),
        "--command-arg",
        "echo",
    )
    assert result.returncode == 0, result.stderr
    assert "PASS stub-vector [stub]" in result.stdout


def test_command_engine_timeout_exits_three(tmp_path: Path, stub_script: Path) -> None:
    vector = {
        "id": "stub-vector",
        "messages": [{"role": "user", "content": "hi"}],
        "template": "{{ messages[0]['content'] }}",
        "expected": {"stub": {"text": "hi"}},
    }
    path = tmp_path / "stub.json"
    path.write_text(json.dumps(vector), encoding="utf-8")
    result = run_cli(
        "validate",
        "--vector",
        str(path),
        "--engine",
        "command:stub",
        "--command",
        sys.executable,
        "--command-arg",
        str(stub_script),
        "--command-arg",
        "sleep",
        "--timeout",
        "0.5",
    )
    assert result.returncode == 3
    assert "timed out" in result.stdout


def test_missing_engine_binary_exits_three(tmp_path: Path) -> None:
    vector = {
        "id": "stub-vector",
        "messages": [{"role": "user", "content": "hi"}],
        "template": "{{ messages[0]['content'] }}",
        "expected": {"stub": {"text": "hi"}},
    }
    path = tmp_path / "stub.json"
    path.write_text(json.dumps(vector), encoding="utf-8")
    result = run_cli(
        "validate",
        "--vector",
        str(path),
        "--engine",
        "command:stub",
        "--command",
        str(tmp_path / "absent-engine.exe"),
    )
    assert result.returncode == 3
    assert "cannot run engine" in result.stdout


def test_readme_command_engine_example() -> None:
    result = run_cli(
        "validate",
        "--vector",
        "examples/echo-engine/vector.json",
        "--engine",
        "command:echo",
        "--command",
        sys.executable,
        "--command-arg",
        "examples/echo-engine/engine.py",
    )
    assert result.returncode == 0, result.stderr
    assert "PASS echo-example [echo]" in result.stdout
