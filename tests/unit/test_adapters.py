from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from helpers import make_vector

from ctp.adapters import (
    CommandConfig,
    ConfigError,
    EngineError,
    EngineUnavailable,
    available_engines,
    command,
    env_mismatches,
    environment_fingerprint,
    mock,
    reference,
    run_engine,
)
from ctp.schema import Vector, parse_vector


def build(**overrides: Any) -> Vector:
    return parse_vector(make_vector(**overrides))


def stub_config(stub_script: Path, mode: str, timeout: float = 30.0) -> CommandConfig:
    return CommandConfig(exe=sys.executable, args=(str(stub_script), mode), timeout=timeout)


def test_reference_returns_text_without_token_ids() -> None:
    result = reference(build())
    assert result.engine == "reference"
    assert result.text == "hi"
    assert result.token_ids is None


def test_mock_is_deterministic_and_utf8_based() -> None:
    first = mock(build())
    assert first == mock(build())
    assert first.token_ids == (1000 + ord("h"), 1000 + ord("i"))
    unicode_result = mock(build(messages=[{"role": "user", "content": "é"}]))
    assert unicode_result.token_ids == (1000 + 0xC3, 1000 + 0xA9)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"exe": ""},
        {"exe": "python", "timeout": 0},
        {"exe": "python", "timeout": -1},
        {"exe": "python", "timeout": float("nan")},
        {"exe": "python", "timeout": float("inf")},
    ],
)
def test_command_config_rejects_invalid_values(kwargs: Mapping[str, Any]) -> None:
    with pytest.raises(ConfigError):
        CommandConfig(**kwargs)


def test_command_engine_echoes_text(stub_script: Path) -> None:
    result = command(stub_config(stub_script, "echo"), build(), "stub")
    assert result.engine == "stub"
    assert result.text == "hi"
    assert result.token_ids is None


def test_command_engine_returns_token_ids_only(stub_script: Path) -> None:
    assert command(stub_config(stub_script, "tokens"), build(), "stub").token_ids == (7, 8)


def test_command_engine_returns_text_and_tokens(stub_script: Path) -> None:
    result = command(stub_config(stub_script, "both"), build(), "stub")
    assert (result.text, result.token_ids) == ("hi", (1,))


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("invalid-json", "invalid JSON"),
        ("not-object", "JSON object"),
        ("empty", "must return"),
        ("bad-text", "non-string text"),
        ("bad-tokens", "invalid token_ids"),
    ],
)
def test_command_engine_rejects_bad_output(stub_script: Path, mode: str, message: str) -> None:
    with pytest.raises(EngineError) as excinfo:
        command(stub_config(stub_script, mode), build(), "stub")
    assert message in excinfo.value.detail
    assert not excinfo.value.unavailable


def test_command_engine_reports_nonzero_exit(stub_script: Path) -> None:
    with pytest.raises(EngineError) as excinfo:
        command(stub_config(stub_script, "fail"), build(), "stub")
    assert "exited with 3" in excinfo.value.detail
    assert "boom" in excinfo.value.detail


def test_command_engine_times_out(stub_script: Path) -> None:
    with pytest.raises(EngineError) as excinfo:
        command(stub_config(stub_script, "sleep", timeout=0.5), build(), "stub")
    assert "timed out" in excinfo.value.detail


def test_missing_executable_is_engine_unavailable(tmp_path: Path) -> None:
    config = CommandConfig(exe=str(tmp_path / "absent-engine.exe"))
    with pytest.raises(EngineUnavailable):
        command(config, build(), "stub")


@pytest.mark.parametrize("spec", ["bogus", "command:", ""])
def test_run_engine_rejects_unknown_specs(spec: str) -> None:
    with pytest.raises(ConfigError):
        run_engine(spec, build())


def test_command_spec_requires_a_config() -> None:
    with pytest.raises(ConfigError):
        run_engine("command:stub", build())


def test_run_engine_uses_the_label_from_the_spec(stub_script: Path) -> None:
    result = run_engine("command:stub", build(), stub_config(stub_script, "echo"))
    assert result.engine == "stub"
    assert result.text == "hi"


def test_run_engine_reference_and_mock() -> None:
    assert run_engine("reference", build()).engine == "reference"
    assert run_engine("mock", build()).engine == "mock"


def test_available_engines() -> None:
    assert available_engines(None) == ["reference", "mock"]
    assert available_engines(CommandConfig(exe=sys.executable)) == ["reference", "mock", "command"]


def test_environment_fingerprint_reports_running_versions() -> None:
    snapshot = environment_fingerprint()
    assert snapshot["jinja2"]
    assert snapshot["python"].startswith(str(sys.version_info.major))


def test_matching_env_produces_no_warnings() -> None:
    assert env_mismatches(build(env=environment_fingerprint())) == []


def test_mismatched_jinja2_warns() -> None:
    warnings = env_mismatches(build(env={"jinja2": "0.0.1"}))
    assert len(warnings) == 1
    assert "0.0.1" in warnings[0]
    assert environment_fingerprint()["jinja2"] in warnings[0]


def test_python_patch_version_is_not_a_warning() -> None:
    major_minor = ".".join(environment_fingerprint()["python"].split(".")[:2])
    assert env_mismatches(build(env={"python": f"{major_minor}.999"})) == []


def test_python_minor_version_mismatch_warns() -> None:
    warnings = env_mismatches(build(env={"python": "2.7.18"}))
    assert warnings
    assert "env.python" in warnings[0]


def test_non_string_env_value_warns() -> None:
    warnings = env_mismatches(build(env={"jinja2": 3}))
    assert warnings
    assert "must be a string" in warnings[0]
