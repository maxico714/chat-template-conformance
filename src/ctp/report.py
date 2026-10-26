from __future__ import annotations

import contextlib
from pathlib import Path

from .validate import ERROR, MISMATCH, Report

_TOOL = "ctp"
_HELP = "https://github.com/maxico714/chat-template-conformance"


def _uri(path: str) -> str:
    target = Path(path)
    with contextlib.suppress(OSError, ValueError):
        target = target.resolve().relative_to(Path.cwd().resolve())
    return target.as_posix()


def format_text(report: Report) -> str:
    lines: list[str] = []
    for vector in report.vectors:
        for warning in vector.warnings:
            lines.append(f"WARN {vector.id}: {warning}")
        for check in vector.checks:
            if check.status == "match":
                lines.append(f"PASS {vector.id} [{check.engine}]")
            elif check.status == MISMATCH:
                lines.append(f"FAIL {vector.id} [{check.engine}]: {check.detail}")
            else:
                lines.append(f"ERROR {vector.id} [{check.engine}]: {check.detail}")
    summary = (
        f"{len(report.vectors)} vectors, {report.checked} engine checks: "
        f"{report.matches} matched, {report.mismatches} mismatched, {report.errors} errors"
    )
    if report.warnings:
        summary += f", {report.warnings} warnings"
    lines.append(summary)
    lines.append("OK" if report.ok else "FAILED")
    return "\n".join(lines)


def to_sarif(report: Report) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for vector in report.vectors:
        for check in vector.checks:
            if check.status == "match":
                continue
            rule = "CTP001" if check.status == MISMATCH else "CTP002"
            results.append(
                {
                    "ruleId": rule,
                    "level": "error",
                    "message": {
                        "text": f"{vector.id} [{check.engine}]: {check.detail or check.status}"
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": _uri(vector.path)},
                                "region": {"startLine": 1},
                            }
                        }
                    ],
                }
            )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": _TOOL,
                        "informationUri": _HELP,
                        "rules": [
                            {
                                "id": "CTP001",
                                "name": "TemplateOutputMismatch",
                                "shortDescription": {
                                    "text": "Rendered output differs from the recorded expectation"
                                },
                                "helpUri": _HELP,
                            },
                            {
                                "id": "CTP002",
                                "name": "EngineOrVectorError",
                                "shortDescription": {
                                    "text": "Engine or vector failed before comparison"
                                },
                                "helpUri": _HELP,
                            },
                        ],
                    }
                },
                "results": results,
            }
        ],
    }


__all__ = ["ERROR", "format_text", "to_sarif"]
