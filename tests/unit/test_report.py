from __future__ import annotations

import json
from pathlib import Path

from ctp.report import format_text, to_sarif
from ctp.validate import EngineCheck, Report, VectorCheck


def sample_report(status: str = "mismatch") -> Report:
    return Report(
        vectors=[
            VectorCheck(
                id="v1",
                path="vectors/v1.json",
                checks=(EngineCheck(engine="reference", status=status, detail="nope"),),
            )
        ]
    )


def test_format_text_lists_checks_and_summary() -> None:
    lines = format_text(sample_report()).splitlines()
    assert lines[0] == "FAIL v1 [reference]: nope"
    assert lines[1] == "1 vectors, 1 engine checks: 0 matched, 1 mismatched, 0 errors"
    assert lines[-1] == "FAILED"


def test_format_text_marks_success() -> None:
    text = format_text(sample_report("match"))
    assert "PASS v1 [reference]" in text
    assert text.endswith("OK")


def test_format_text_includes_warnings_and_keeps_ok() -> None:
    report = Report(
        vectors=[
            VectorCheck(
                id="v1",
                path="",
                checks=(EngineCheck(engine="reference", status="match"),),
                warnings=("env.jinja2: drift",),
            )
        ]
    )
    text = format_text(report)
    assert "WARN v1: env.jinja2: drift" in text
    assert "1 warnings" in text
    assert text.endswith("OK")


def test_sarif_documents_schema_and_rules() -> None:
    payload = to_sarif(sample_report())
    assert payload["version"] == "2.1.0"
    assert str(payload["$schema"]).endswith("sarif-2.1.0.json")
    driver = payload["runs"][0]["tool"]["driver"]  # type: ignore[index]
    assert driver["name"] == "ctp"
    assert [rule["id"] for rule in driver["rules"]] == ["CTP001", "CTP002"]


def test_sarif_skips_matches() -> None:
    payload = to_sarif(sample_report("match"))
    assert payload["runs"][0]["results"] == []  # type: ignore[index]


def test_sarif_result_shape_for_mismatch() -> None:
    result = to_sarif(sample_report())["runs"][0]["results"][0]  # type: ignore[index]
    assert result["ruleId"] == "CTP001"
    assert result["level"] == "error"
    assert result["message"]["text"] == "v1 [reference]: nope"
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "vectors/v1.json"
    assert location["region"]["startLine"] == 1


def test_sarif_uses_error_rule_for_engine_errors() -> None:
    report = Report(
        vectors=[
            VectorCheck(
                id="v1",
                path="v.json",
                checks=(EngineCheck(engine="stub", status="error", detail="boom", kind="engine"),),
            )
        ]
    )
    assert to_sarif(report)["runs"][0]["results"][0]["ruleId"] == "CTP002"  # type: ignore[index]


def test_uri_is_relative_when_inside_the_working_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "vectors" / "v.json"
    target.parent.mkdir()
    target.write_text("{}", encoding="utf-8")
    report = Report(
        vectors=[
            VectorCheck(
                id="v",
                path=str(target),
                checks=(EngineCheck(engine="reference", status="mismatch"),),
            )
        ]
    )
    result = to_sarif(report)["runs"][0]["results"][0]  # type: ignore[index]
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "vectors/v.json"


def test_uri_falls_back_to_absolute_posix_path(tmp_path: Path, monkeypatch) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    outside = tmp_path / "elsewhere" / "v.json"
    report = Report(
        vectors=[
            VectorCheck(
                id="v",
                path=str(outside),
                checks=(EngineCheck(engine="reference", status="mismatch"),),
            )
        ]
    )
    result = to_sarif(report)["runs"][0]["results"][0]  # type: ignore[index]
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri.endswith("elsewhere/v.json")
    assert "\\" not in uri


def test_sarif_is_json_serialisable() -> None:
    json.dumps(to_sarif(sample_report()))
