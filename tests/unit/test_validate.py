from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from helpers import make_vector

from ctp.adapters import CommandConfig, ConfigError
from ctp.schema import Vector, parse_vector
from ctp.validate import (
    EngineCheck,
    Report,
    VectorCheck,
    check_vector,
    load_vectors,
    validate_directory,
    validate_vectors,
)


def build(**overrides: Any) -> Vector:
    return parse_vector(make_vector(**overrides))


def test_match_reports_success() -> None:
    check = check_vector(build(), ["reference"], None)
    assert [item.status for item in check.checks] == ["match"]
    assert check.ok
    assert Report(vectors=[check]).exit_code == 0


def test_text_mismatch_points_at_the_first_differing_char() -> None:
    check = check_vector(build(expected={"reference": {"text": "ho"}}), ["reference"], None)
    assert check.checks[0].status == "mismatch"
    assert check.checks[0].detail == "text differs at char 1: expected 'o' got 'i'"
    assert Report(vectors=[check]).exit_code == 1


def test_text_length_mismatch_is_reported() -> None:
    check = check_vector(build(expected={"reference": {"text": "hi!"}}), ["reference"], None)
    assert check.checks[0].detail == "text length differs: expected 3 chars, got 2 chars"


def test_token_mismatch_reports_index_and_values() -> None:
    vector = build(expected={"mock": {"text": "hi", "token_ids": [1104, 9999]}})
    check = check_vector(vector, ["mock"], None)
    assert check.checks[0].detail == "token ids differ at index 1: expected 9999, got 1105"


def test_token_count_mismatch_is_reported() -> None:
    vector = build(expected={"mock": {"text": "hi", "token_ids": [1104]}})
    check = check_vector(vector, ["mock"], None)
    assert check.checks[0].detail == "token count differs: expected 1, got 2"


def test_missing_engine_expectation_is_a_schema_error() -> None:
    check = check_vector(build(), ["mock"], None)
    assert check.checks[0].status == "error"
    assert check.checks[0].kind == "schema"
    assert "no expected output" in check.checks[0].detail
    assert Report(vectors=[check]).exit_code == 2


def test_render_error_is_a_schema_error() -> None:
    vector = build(template="{% if %}", expected={"reference": {"text": ""}})
    check = check_vector(vector, ["reference"], None)
    assert check.checks[0].kind == "schema"
    assert Report(vectors=[check]).exit_code == 2


def test_engine_failure_is_an_engine_error(tmp_path: Path) -> None:
    config = CommandConfig(exe=str(tmp_path / "absent-engine.exe"))
    vector = build(expected={"stub": {"text": "hi"}})
    check = check_vector(vector, ["command:stub"], config)
    assert check.checks[0].kind == "engine"
    assert check.checks[0].status == "error"
    assert Report(vectors=[check]).exit_code == 3


def test_command_engine_without_config_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        check_vector(build(expected={"stub": {"text": "hi"}}), ["command:stub"], None)


def test_command_engine_uses_the_expected_label(stub_script: Path) -> None:
    config = CommandConfig(exe=sys.executable, args=(str(stub_script), "echo"))
    check = check_vector(build(expected={"stub": {"text": "hi"}}), ["command:stub"], config)
    assert check.checks[0].engine == "stub"
    assert check.checks[0].status == "match"


def test_other_engines_continue_after_a_mismatch() -> None:
    vector = build(expected={"reference": {"text": "hi"}, "mock": {"text": "hi", "token_ids": [1]}})
    check = check_vector(vector, ["reference", "mock"], None)
    assert [item.status for item in check.checks] == ["match", "mismatch"]


def make_check(status: str, kind: str = "") -> VectorCheck:
    return VectorCheck(id="v", path="", checks=(EngineCheck(engine="e", status=status, kind=kind),))


def test_exit_code_precedence() -> None:
    assert Report().exit_code == 0
    assert Report(vectors=[make_check("match")]).exit_code == 0
    assert Report(vectors=[make_check("mismatch")]).exit_code == 1
    assert Report(vectors=[make_check("mismatch"), make_check("error", "engine")]).exit_code == 3
    assert Report(vectors=[make_check("mismatch"), make_check("error", "schema")]).exit_code == 2
    config_and_schema = [make_check("error", "schema"), make_check("error", "config")]
    assert Report(vectors=config_and_schema).exit_code == 4


def test_report_counts_and_ok_flag() -> None:
    report = Report(
        vectors=[
            VectorCheck(
                id="a",
                path="",
                checks=(
                    EngineCheck(engine="reference", status="match"),
                    EngineCheck(engine="mock", status="mismatch"),
                    EngineCheck(engine="stub", status="error", kind="engine"),
                ),
                warnings=("env.jinja2: drift",),
            )
        ]
    )
    assert (report.checked, report.matches, report.mismatches, report.errors) == (3, 1, 1, 1)
    assert report.warnings == 1
    assert report.ok is False


def test_env_mismatch_becomes_a_warning_but_not_a_failure() -> None:
    check = check_vector(build(env={"jinja2": "0.0.1"}), ["reference"], None)
    assert check.ok
    assert check.warnings
    assert "env.jinja2" in check.warnings[0]
    assert check.to_dict()["warnings"] == list(check.warnings)


def test_to_dict_omits_empty_warnings() -> None:
    assert "warnings" not in check_vector(build(), ["reference"], None).to_dict()


def test_load_vectors_collects_failures(tmp_path: Path) -> None:
    (tmp_path / "good.json").write_text(json.dumps(make_vector()), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    vectors, failures = load_vectors(tmp_path)
    assert [vector.id for vector in vectors] == ["unit-vector"]
    assert len(failures) == 1
    assert "bad.json" in failures[0][0]


def test_validate_directory_surfaces_schema_failures(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    report = validate_directory(tmp_path, ["reference"], None)
    assert report.exit_code == 2
    assert report.vectors[0].checks[0].kind == "schema"


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_vectors(tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        validate_directory(tmp_path / "absent", ["reference"], None)


def test_validate_vectors_reports_each_vector() -> None:
    report = validate_vectors([build(), build(id="second")], ["reference"], None)
    assert len(report.vectors) == 2
    assert report.exit_code == 0
    assert report.to_dict()["summary"] == {
        "vectors": 2,
        "engines_checked": 2,
        "matched": 2,
        "mismatched": 0,
        "errors": 0,
        "warnings": 0,
    }
