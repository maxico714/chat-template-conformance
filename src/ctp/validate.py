from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .adapters import (
    CommandConfig,
    EngineError,
    RenderResult,
    ensure_engine_spec,
    env_mismatches,
    run_engine,
)
from .render import RenderError
from .schema import Vector, load_vector

MATCH = "match"
MISMATCH = "mismatch"
ERROR = "error"


def _snippet(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return repr(text)
    return repr(text[:limit] + "...")


def _text_detail(expected: str, actual: str) -> str:
    for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
        if left != right:
            return (
                f"text differs at char {index}: expected {_snippet(expected[index:])} "
                f"got {_snippet(actual[index:])}"
            )
    return f"text length differs: expected {len(expected)} chars, got {len(actual)} chars"


def _token_detail(expected: tuple[int, ...], actual: tuple[int, ...]) -> str:
    for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
        if left != right:
            return f"token ids differ at index {index}: expected {left}, got {right}"
    return f"token count differs: expected {len(expected)}, got {len(actual)}"


@dataclass(frozen=True)
class EngineCheck:
    engine: str
    status: str
    detail: str = ""
    kind: str = ""
    expected_text: str | None = None
    actual_text: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"engine": self.engine, "status": self.status}
        if self.detail:
            data["detail"] = self.detail
        if self.kind:
            data["kind"] = self.kind
        return data


@dataclass(frozen=True)
class VectorCheck:
    id: str
    path: str
    checks: tuple[EngineCheck, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return all(check.status == MATCH for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.id,
            "path": self.path,
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
        }
        if self.warnings:
            data["warnings"] = list(self.warnings)
        return data


@dataclass
class Report:
    vectors: list[VectorCheck] = field(default_factory=list)

    @property
    def checked(self) -> int:
        return sum(len(vector.checks) for vector in self.vectors)

    @property
    def matches(self) -> int:
        return sum(1 for vector in self.vectors for check in vector.checks if check.status == MATCH)

    @property
    def mismatches(self) -> int:
        return sum(
            1 for vector in self.vectors for check in vector.checks if check.status == MISMATCH
        )

    @property
    def errors(self) -> int:
        return sum(1 for vector in self.vectors for check in vector.checks if check.status == ERROR)

    @property
    def warnings(self) -> int:
        return sum(len(vector.warnings) for vector in self.vectors)

    @property
    def ok(self) -> bool:
        return not self.mismatches and not self.errors

    @property
    def exit_code(self) -> int:
        kinds = {check.kind for vector in self.vectors for check in vector.checks if check.kind}
        if "config" in kinds:
            return 4
        if "schema" in kinds:
            return 2
        if "engine" in kinds:
            return 3
        if self.mismatches:
            return 1
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "vectors": [vector.to_dict() for vector in self.vectors],
            "summary": {
                "vectors": len(self.vectors),
                "engines_checked": self.checked,
                "matched": self.matches,
                "mismatched": self.mismatches,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        }


def check_vector(vector: Vector, engines: list[str], config: CommandConfig | None) -> VectorCheck:
    checks: list[EngineCheck] = []
    for spec in engines:
        ensure_engine_spec(spec, config)
        label = spec.partition(":")[2] if spec.startswith("command:") else spec
        expected = vector.expected.get(label)
        if expected is None:
            checks.append(
                EngineCheck(
                    engine=label,
                    status=ERROR,
                    kind="schema",
                    detail=f"no expected output for engine '{label}' in vector '{vector.id}'",
                )
            )
            continue
        try:
            resolved = run_engine(spec, vector, config)
        except EngineError as exc:
            checks.append(EngineCheck(engine=label, status=ERROR, kind="engine", detail=exc.detail))
            continue
        except RenderError as exc:
            checks.append(EngineCheck(engine=label, status=ERROR, kind="schema", detail=exc.detail))
            continue
        checks.append(_compare(label, expected.text, expected.token_ids, resolved))
    return VectorCheck(
        id=vector.id,
        path=str(vector.path or ""),
        checks=tuple(checks),
        warnings=tuple(env_mismatches(vector)),
    )


def _compare(
    label: str,
    expected_text: str | None,
    expected_ids: tuple[int, ...] | None,
    result: RenderResult,
) -> EngineCheck:
    details: list[str] = []
    if expected_text is not None:
        if result.text is None:
            details.append("engine returned no text")
        elif result.text != expected_text:
            details.append(_text_detail(expected_text, result.text))
    if expected_ids is not None:
        if result.token_ids is None:
            details.append("engine returned no token ids")
        elif result.token_ids != expected_ids:
            details.append(_token_detail(expected_ids, result.token_ids))
    status = MISMATCH if details else MATCH
    return EngineCheck(
        engine=label,
        status=status,
        detail="; ".join(details),
        expected_text=expected_text,
        actual_text=result.text,
    )


def load_vectors(directory: str | Path) -> tuple[list[Vector], list[tuple[str, str]]]:
    base = Path(directory)
    if not base.is_dir():
        raise FileNotFoundError(f"vector directory not found: {base}")
    vectors: list[Vector] = []
    failures: list[tuple[str, str]] = []
    for path in sorted(base.glob("*.json")):
        try:
            vectors.append(load_vector(path))
        except ValueError as exc:
            failures.append((str(path), str(exc)))
    return vectors, failures


def validate_vectors(
    vectors: list[Vector], engines: list[str], config: CommandConfig | None
) -> Report:
    report = Report()
    for vector in vectors:
        report.vectors.append(check_vector(vector, engines, config))
    return report


def validate_directory(
    directory: str | Path, engines: list[str], config: CommandConfig | None
) -> Report:
    vectors, failures = load_vectors(directory)
    report = validate_vectors(vectors, engines, config)
    for path, detail in failures:
        report.vectors.append(
            VectorCheck(
                id=Path(path).stem,
                path=path,
                checks=(EngineCheck(engine="schema", status=ERROR, kind="schema", detail=detail),),
            )
        )
    return report
