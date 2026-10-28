from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

MAX_VECTOR_BYTES = 2_000_000
MAX_TEMPLATE_CHARS = 200_000
MAX_MESSAGES = 1_000
MAX_TOOLS = 1_000
MAX_TOKEN_IDS = 100_000
MAX_CONTEXT_KEYS = 100

RESERVED_CONTEXT = {"messages", "tools", "bos_token", "eos_token", "add_generation_prompt"}
_ENGINE_LABEL = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_TOP_LEVEL = {
    "id",
    "description",
    "messages",
    "tools",
    "template",
    "bos_token",
    "eos_token",
    "options",
    "context",
    "env",
    "source",
    "expected",
}


class VectorError(ValueError):
    code = "E_SCHEMA"

    def __init__(self, detail: str, path: str = "") -> None:
        super().__init__(detail)
        self.detail = detail
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"{self.code}: {self.path}: {self.detail}"
        return f"{self.code}: {self.detail}"


@dataclass(frozen=True)
class Expected:
    text: str | None = None
    token_ids: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Options:
    add_generation_prompt: bool = False


@dataclass(frozen=True)
class Vector:
    id: str
    messages: tuple[dict[str, Any], ...]
    template: str
    expected: dict[str, Expected]
    tools: tuple[dict[str, Any], ...] = ()
    bos_token: str | None = None
    eos_token: str | None = None
    options: Options = Options()
    context: dict[str, Any] = field(default_factory=dict)
    env: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    path: Path | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "messages": [dict(message) for message in self.messages],
            "tools": [dict(tool) for tool in self.tools],
            "template": self.template,
            "bos_token": self.bos_token,
            "eos_token": self.eos_token,
            "options": {"add_generation_prompt": self.options.add_generation_prompt},
            "context": dict(self.context),
        }


def _fail(detail: str, path: str) -> NoReturn:
    raise VectorError(detail, path)


def _mapping(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("must be an object", where)
    return {str(key): item for key, item in value.items()}


def _string(value: object, where: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        _fail("must be a string", where)
    if not allow_empty and not value:
        _fail("must not be empty", where)
    return value


def _positive_int(value: object, where: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("must be an integer", where)
    if value < 0 or value > maximum:
        _fail(f"must be between 0 and {maximum}", where)
    return value


def _messages(data: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(data, list):
        _fail("must be a list", "messages")
    if not data:
        _fail("must contain at least one message", "messages")
    if len(data) > MAX_MESSAGES:
        _fail(f"must contain at most {MAX_MESSAGES} messages", "messages")
    messages: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        where = f"messages[{index}]"
        message = _mapping(item, where)
        role = _string(message.get("role"), f"{where}.role", allow_empty=False)
        message["role"] = role
        content = message.get("content")
        if content is not None and not isinstance(content, (str, list, dict)):
            _fail("must be a string, list, object, or null", f"{where}.content")
        if (
            "tool_calls" in message
            and message["tool_calls"] is not None
            and not isinstance(message["tool_calls"], list)
        ):
            _fail("must be a list", f"{where}.tool_calls")
        messages.append(message)
    return tuple(messages)


def _tools(data: object) -> tuple[dict[str, Any], ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        _fail("must be a list", "tools")
    if len(data) > MAX_TOOLS:
        _fail(f"must contain at most {MAX_TOOLS} tools", "tools")
    tools: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        tools.append(_mapping(item, f"tools[{index}]"))
    return tuple(tools)


def _token_ids(data: object, where: str) -> tuple[int, ...]:
    if not isinstance(data, list):
        _fail("must be a list of integers", where)
    if len(data) > MAX_TOKEN_IDS:
        _fail(f"must contain at most {MAX_TOKEN_IDS} token ids", where)
    ids: list[int] = []
    for index, item in enumerate(data):
        ids.append(_positive_int(item, f"{where}[{index}]", 2**63 - 1))
    return tuple(ids)


def _expected(data: object) -> dict[str, Expected]:
    if not isinstance(data, dict):
        _fail("must be an object keyed by engine name", "expected")
    if not data:
        _fail("must contain at least one engine", "expected")
    result: dict[str, Expected] = {}
    for name, entry in data.items():
        where = f"expected.{name}"
        label = _string(name, where, allow_empty=False)
        if not _ENGINE_LABEL.match(label):
            _fail("engine name must match [A-Za-z][A-Za-z0-9_.-]*", where)
        if label in result:
            _fail("duplicate engine name", where)
        body = _mapping(entry, where)
        unknown = set(body) - {"text", "token_ids"}
        if unknown:
            _fail(f"unknown keys {sorted(unknown)}", where)
        if not body:
            _fail("must contain 'text' and/or 'token_ids'", where)
        text = body.get("text")
        if "text" in body and not isinstance(text, str):
            _fail("must be a string", f"{where}.text")
        token_ids = body.get("token_ids")
        parsed_ids = _token_ids(token_ids, f"{where}.token_ids") if "token_ids" in body else None
        result[label] = Expected(text=text, token_ids=parsed_ids)
    return result


def _options(data: object) -> Options:
    if data is None:
        return Options()
    body = _mapping(data, "options")
    unknown = set(body) - {"add_generation_prompt"}
    if unknown:
        _fail(f"unknown keys {sorted(unknown)}", "options")
    flag = body.get("add_generation_prompt", False)
    if not isinstance(flag, bool):
        _fail("must be a boolean", "options.add_generation_prompt")
    return Options(add_generation_prompt=flag)


def _context(data: object) -> dict[str, Any]:
    if data is None:
        return {}
    body = _mapping(data, "context")
    if len(body) > MAX_CONTEXT_KEYS:
        _fail(f"must contain at most {MAX_CONTEXT_KEYS} keys", "context")
    clash = set(body) & RESERVED_CONTEXT
    if clash:
        _fail(f"reserved names {sorted(clash)} cannot be overridden", "context")
    for key in body:
        if not key:
            _fail("keys must not be empty", "context")
    return body


def _free_mapping(data: object, where: str) -> dict[str, Any]:
    if data is None:
        return {}
    return _mapping(data, where)


def parse_vector(data: object, *, path: Path | None = None) -> Vector:
    body = _mapping(data, "vector")
    unknown = set(body) - _TOP_LEVEL
    if unknown:
        _fail(f"unknown keys {sorted(unknown)}", "vector")
    identifier = _string(body.get("id"), "id", allow_empty=False)
    if len(identifier) > 200:
        _fail("must be at most 200 characters", "id")
    template = _string(body.get("template"), "template", allow_empty=False)
    if len(template) > MAX_TEMPLATE_CHARS:
        _fail(f"must be at most {MAX_TEMPLATE_CHARS} characters", "template")
    description = body.get("description")
    if description is not None:
        description = _string(description, "description")
    bos_token = body.get("bos_token")
    if bos_token is not None:
        bos_token = _string(bos_token, "bos_token")
    eos_token = body.get("eos_token")
    if eos_token is not None:
        eos_token = _string(eos_token, "eos_token")
    return Vector(
        id=identifier,
        messages=_messages(body.get("messages")),
        template=template,
        expected=_expected(body.get("expected")),
        tools=_tools(body.get("tools")),
        bos_token=bos_token,
        eos_token=eos_token,
        options=_options(body.get("options")),
        context=_context(body.get("context")),
        env=_free_mapping(body.get("env"), "env"),
        source=_free_mapping(body.get("source"), "source"),
        description=description,
        path=path,
    )


def load_vector(path: str | Path) -> Vector:
    target = Path(path)
    try:
        info = target.stat()
    except FileNotFoundError:
        raise VectorError("vector file does not exist", str(target)) from None
    except OSError as exc:
        raise VectorError(str(exc), str(target)) from None
    if not stat.S_ISREG(info.st_mode):
        raise VectorError("vector path is not a regular file", str(target))
    if info.st_size > MAX_VECTOR_BYTES:
        raise VectorError(
            f"vector file is {info.st_size} bytes (max {MAX_VECTOR_BYTES})", str(target)
        )
    try:
        with target.open("rb") as handle:
            raw_bytes = handle.read(MAX_VECTOR_BYTES + 1)
    except FileNotFoundError:
        raise VectorError("vector file does not exist", str(target)) from None
    except OSError as exc:
        raise VectorError(str(exc), str(target)) from None
    if len(raw_bytes) > MAX_VECTOR_BYTES:
        raise VectorError(
            f"vector file exceeds {MAX_VECTOR_BYTES} bytes (size changed while reading)",
            str(target),
        )
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VectorError(str(exc), str(target)) from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VectorError(f"invalid JSON: {exc.msg} at line {exc.lineno}", str(target)) from None
    return parse_vector(data, path=target)
