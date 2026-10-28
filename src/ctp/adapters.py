from __future__ import annotations

import json
import math
import platform
import subprocess
from dataclasses import dataclass

import jinja2

from .render import RenderError, render
from .schema import Vector


class ConfigError(ValueError):
    code = "E_CONFIG"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class EngineError(RuntimeError):
    code = "E_ENGINE"
    unavailable = False

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class EngineUnavailable(EngineError):
    unavailable = True


@dataclass(frozen=True)
class RenderResult:
    engine: str
    text: str | None
    token_ids: tuple[int, ...] | None


@dataclass(frozen=True)
class CommandConfig:
    exe: str
    args: tuple[str, ...] = ()
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.exe:
            raise ConfigError("command executable must not be empty")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ConfigError("command timeout must be positive and finite")


def reference(vector: Vector) -> RenderResult:
    return RenderResult(engine="reference", text=render(vector), token_ids=None)


def mock(vector: Vector) -> RenderResult:
    text = render(vector)
    token_ids = tuple(1000 + byte for byte in text.encode("utf-8"))
    return RenderResult(engine="mock", text=text, token_ids=token_ids)


def _parse_command_output(stdout: str, label: str) -> RenderResult:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise EngineError(f"engine '{label}' wrote invalid JSON: {exc.msg}") from None
    if not isinstance(payload, dict):
        raise EngineError(f"engine '{label}' must write a JSON object")
    text = payload.get("text")
    token_ids = payload.get("token_ids")
    if text is None and token_ids is None:
        raise EngineError(f"engine '{label}' must return 'text' and/or 'token_ids'")
    if text is not None and not isinstance(text, str):
        raise EngineError(f"engine '{label}' returned a non-string text")
    parsed_ids: tuple[int, ...] | None = None
    if token_ids is not None:
        if not isinstance(token_ids, list) or any(
            isinstance(item, bool) or not isinstance(item, int) for item in token_ids
        ):
            raise EngineError(f"engine '{label}' returned invalid token_ids")
        parsed_ids = tuple(token_ids)
    return RenderResult(engine=label, text=text, token_ids=parsed_ids)


def command(config: CommandConfig, vector: Vector, label: str) -> RenderResult:
    payload = json.dumps(vector.payload(), ensure_ascii=False)
    try:
        completed = subprocess.run(
            [config.exe, *config.args],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=config.timeout,
            shell=False,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise EngineUnavailable(f"cannot run engine '{label}': {exc}") from None
    except subprocess.TimeoutExpired:
        raise EngineError(f"engine '{label}' timed out after {config.timeout:g}s") from None
    except OSError as exc:
        raise EngineUnavailable(f"cannot run engine '{label}': {exc}") from None
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()[:300]
        raise EngineError(
            f"engine '{label}' exited with {completed.returncode}: {stderr or 'no stderr'}"
        )
    return _parse_command_output(completed.stdout, label)


def ensure_engine_spec(spec: str, config: CommandConfig | None) -> None:
    """Reject unusable engine specs before any vector is inspected."""
    if spec in {"reference", "mock"}:
        return
    if spec.startswith("command:"):
        if not spec.partition(":")[2]:
            raise ConfigError("engine 'command:' needs a name, e.g. command:llama_cpp")
        if config is None:
            raise ConfigError(f"engine '{spec}' needs --command and --command-arg")
        return
    raise ConfigError(f"unknown engine '{spec}' (use reference, mock, or command:NAME)")


def run_engine(spec: str, vector: Vector, config: CommandConfig | None = None) -> RenderResult:
    ensure_engine_spec(spec, config)
    if spec == "reference":
        return reference(vector)
    if spec == "mock":
        return mock(vector)
    label = spec.partition(":")[2]
    assert config is not None
    result = command(config, vector, label)
    return RenderResult(engine=label, text=result.text, token_ids=result.token_ids)


def available_engines(config: CommandConfig | None) -> list[str]:
    engines = ["reference", "mock"]
    if config is not None:
        engines.append("command")
    return engines


def environment_fingerprint() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "jinja2": jinja2.__version__,
    }


def _same_version(key: str, recorded: str, running: str) -> bool:
    if key == "python":
        return ".".join(recorded.split(".")[:2]) == ".".join(running.split(".")[:2])
    return recorded == running


def env_mismatches(vector: Vector) -> list[str]:
    """Warn when the environment recorded in a vector differs from the running one."""
    running = environment_fingerprint()
    warnings: list[str] = []
    for key in ("python", "jinja2"):
        if key not in vector.env:
            continue
        recorded = vector.env[key]
        if not isinstance(recorded, str):
            warnings.append(f"env.{key} must be a string recording the version")
            continue
        if not _same_version(key, recorded, running[key]):
            warnings.append(f"env.{key}: vector recorded {recorded}, running {running[key]}")
    return warnings


__all__ = [
    "CommandConfig",
    "ConfigError",
    "EngineError",
    "EngineUnavailable",
    "RenderError",
    "RenderResult",
    "available_engines",
    "command",
    "ensure_engine_spec",
    "env_mismatches",
    "environment_fingerprint",
    "mock",
    "reference",
    "run_engine",
]
