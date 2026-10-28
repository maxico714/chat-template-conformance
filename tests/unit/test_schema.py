from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from helpers import make_vector

from ctp.schema import (
    MAX_CONTEXT_KEYS,
    MAX_MESSAGES,
    MAX_TEMPLATE_CHARS,
    MAX_TOKEN_IDS,
    MAX_VECTOR_BYTES,
    VectorError,
    load_vector,
    parse_vector,
)


def test_minimal_vector_parses() -> None:
    vector = parse_vector(make_vector())
    assert vector.id == "unit-vector"
    assert vector.template == "{{ messages[0]['content'] }}"
    assert vector.expected["reference"].text == "hi"
    assert vector.expected["reference"].token_ids is None
    assert vector.tools == ()
    assert vector.bos_token is None
    assert vector.eos_token is None
    assert vector.options.add_generation_prompt is False
    assert vector.context == {}
    assert vector.env == {}
    assert vector.source == {}
    assert vector.description is None
    assert vector.path is None


def test_optional_fields_parse() -> None:
    vector = parse_vector(
        make_vector(
            description="desc",
            tools=[{"type": "function"}],
            bos_token="<s>",
            eos_token="</s>",
            options={"add_generation_prompt": True},
            context={"custom": 1},
            env={"jinja2": "3.1.6"},
            source={"issue": "x"},
            expected={"reference": {"text": "hi", "token_ids": [1, 2]}},
        )
    )
    assert vector.description == "desc"
    assert vector.tools == ({"type": "function"},)
    assert vector.bos_token == "<s>"
    assert vector.eos_token == "</s>"
    assert vector.options.add_generation_prompt is True
    assert vector.context == {"custom": 1}
    assert vector.env == {"jinja2": "3.1.6"}
    assert vector.source == {"issue": "x"}
    assert vector.expected["reference"].token_ids == (1, 2)


def test_payload_contains_render_inputs_only() -> None:
    vector = parse_vector(
        make_vector(
            options={"add_generation_prompt": True},
            context={"custom": 1},
            env={"jinja2": "3.1.6"},
        )
    )
    payload = vector.payload()
    assert payload["options"] == {"add_generation_prompt": True}
    assert payload["context"] == {"custom": 1}
    assert "env" not in payload
    assert "expected" not in payload


@pytest.mark.parametrize(
    ("overrides", "expected_path"),
    [
        ({"id": None}, "id"),
        ({"id": ""}, "id"),
        ({"id": 5}, "id"),
        ({"id": "x" * 201}, "id"),
        ({"template": None}, "template"),
        ({"template": ""}, "template"),
        ({"template": "x" * (MAX_TEMPLATE_CHARS + 1)}, "template"),
        ({"messages": []}, "messages"),
        ({"messages": "hi"}, "messages"),
        ({"messages": [{"content": "hi"}]}, "messages[0].role"),
        ({"messages": [{"role": "", "content": "hi"}]}, "messages[0].role"),
        ({"messages": [{"role": "user", "content": 7}]}, "messages[0].content"),
        ({"messages": [{"role": "user", "tool_calls": "x"}]}, "messages[0].tool_calls"),
        ({"messages": [{"role": "user"}] * (MAX_MESSAGES + 1)}, "messages"),
        ({"tools": "x"}, "tools"),
        ({"tools": [1]}, "tools[0]"),
        ({"expected": {}}, "expected"),
        ({"expected": {"reference": {}}}, "expected.reference"),
        ({"expected": {"reference": {"nope": 1}}}, "expected.reference"),
        ({"expected": {"reference": {"text": 1}}}, "expected.reference.text"),
        ({"expected": {"reference": {"token_ids": [True]}}}, "expected.reference.token_ids[0]"),
        ({"expected": {"reference": {"token_ids": [-1]}}}, "expected.reference.token_ids[0]"),
        ({"expected": {"reference": {"token_ids": [2**63]}}}, "expected.reference.token_ids[0]"),
        (
            {"expected": {"reference": {"token_ids": [0] * (MAX_TOKEN_IDS + 1)}}},
            "expected.reference.token_ids",
        ),
        ({"expected": {"bad name": {"text": "x"}}}, "expected.bad name"),
        ({"expected": {"1bad": {"text": "x"}}}, "expected.1bad"),
        ({"options": {"unknown": True}}, "options"),
        ({"options": {"add_generation_prompt": "yes"}}, "options.add_generation_prompt"),
        ({"context": {"messages": []}}, "context"),
        ({"env": []}, "env"),
        ({"source": "x"}, "source"),
        ({"unexpected": 1}, "vector"),
    ],
)
def test_invalid_vectors_are_rejected(overrides: dict[str, Any], expected_path: str) -> None:
    with pytest.raises(VectorError) as excinfo:
        parse_vector(make_vector(**overrides))
    assert excinfo.value.code == "E_SCHEMA"
    assert excinfo.value.path == expected_path


def test_null_and_structured_content_is_allowed() -> None:
    vector = parse_vector(
        make_vector(
            messages=[
                {"role": "assistant", "content": None, "tool_calls": None},
                {"role": "user", "content": [{"type": "text", "text": "x"}]},
                {"role": "user", "content": {"parts": []}},
            ]
        )
    )
    assert vector.messages[0]["content"] is None
    assert isinstance(vector.messages[1]["content"], list)
    assert isinstance(vector.messages[2]["content"], dict)


def test_context_key_limit_is_inclusive() -> None:
    parse_vector(make_vector(context={f"key{i}": i for i in range(MAX_CONTEXT_KEYS)}))
    with pytest.raises(VectorError):
        parse_vector(make_vector(context={f"key{i}": i for i in range(MAX_CONTEXT_KEYS + 1)}))


def test_token_id_bounds_are_inclusive() -> None:
    vector = parse_vector(make_vector(expected={"reference": {"token_ids": [0, 2**63 - 1]}}))
    assert vector.expected["reference"].token_ids == (0, 2**63 - 1)


def test_engine_labels_allow_dots_and_dashes() -> None:
    vector = parse_vector(make_vector(expected={"cmd.stub-1": {"text": "hi"}}))
    assert set(vector.expected) == {"cmd.stub-1"}


def test_extra_message_fields_are_preserved() -> None:
    vector = parse_vector(
        make_vector(messages=[{"role": "tool", "tool_call_id": "call_1", "content": "ok"}])
    )
    assert vector.messages[0]["tool_call_id"] == "call_1"


def test_load_vector_attaches_the_path(write_vector: Callable[..., Path]) -> None:
    path = write_vector(make_vector())
    vector = load_vector(path)
    assert vector.path == path
    assert vector.id == "unit-vector"


def test_load_vector_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VectorError) as excinfo:
        load_vector(tmp_path / "missing.json")
    assert "does not exist" in excinfo.value.detail


def test_load_vector_reports_json_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{\n  "id": oops\n}\n', encoding="utf-8")
    with pytest.raises(VectorError) as excinfo:
        load_vector(path)
    assert "invalid JSON" in excinfo.value.detail
    assert "line 2" in excinfo.value.detail


def test_load_vector_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "binary.json"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(VectorError) as excinfo:
        load_vector(path)
    assert excinfo.value.code == "E_SCHEMA"


def test_load_vector_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_bytes(b" " * 2_000_001)
    with pytest.raises(VectorError) as excinfo:
        load_vector(path)
    assert "max" in excinfo.value.detail


def test_load_vector_rejects_a_directory(tmp_path: Path) -> None:
    with pytest.raises(VectorError) as excinfo:
        load_vector(tmp_path)
    assert "not a regular file" in excinfo.value.detail


def test_size_cap_is_enforced_while_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "growing.json"
    path.write_bytes(b" " * (MAX_VECTOR_BYTES + 1))
    real_stat = Path.stat

    def small_stat(self: Path, *args: object, **kwargs: object) -> os.stat_result:
        info = real_stat(self, *args, **kwargs)  # type: ignore[arg-type]
        if self == path:
            return os.stat_result(
                (
                    info.st_mode,
                    info.st_ino,
                    info.st_dev,
                    info.st_nlink,
                    info.st_uid,
                    info.st_gid,
                    1,
                    info.st_atime,
                    info.st_mtime,
                    info.st_ctime,
                )
            )
        return info

    monkeypatch.setattr(Path, "stat", small_stat)
    with pytest.raises(VectorError) as excinfo:
        load_vector(path)
    assert "exceeds" in excinfo.value.detail
