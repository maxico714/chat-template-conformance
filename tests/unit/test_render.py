from __future__ import annotations

from typing import Any

import pytest
from helpers import make_vector

from ctp.render import RenderError, render, strip_generation_tags
from ctp.schema import Vector, parse_vector


def build(**overrides: Any) -> Vector:
    return parse_vector(make_vector(**overrides))


def test_renders_message_content() -> None:
    assert render(build()) == "hi"


def test_block_directives_trim_their_own_lines() -> None:
    vector = build(
        template="{% if add_generation_prompt %}\nA\n{% endif %}\nB\n",
        options={"add_generation_prompt": True},
    )
    assert render(vector) == "A\nB"


def test_single_trailing_newline_is_stripped() -> None:
    assert render(build(template="x\n")) == "x"
    assert render(build(template="x\n\n")) == "x\n"


def test_generation_prompt_branch() -> None:
    template = "{% if add_generation_prompt %}<assistant>{% endif %}"
    enabled = build(template=template, options={"add_generation_prompt": True})
    assert render(enabled) == "<assistant>"
    assert render(build(template=template)) == ""


def test_bos_and_eos_default_to_empty_strings() -> None:
    assert render(build(template="{{ bos_token }}|{{ eos_token }}")) == "|"
    assert render(build(template="{{ bos_token }}", bos_token="<s>")) == "<s>"


def test_context_values_are_available() -> None:
    assert render(build(template="{{ custom }}", context={"custom": 42})) == "42"


def test_strip_generation_tags_handles_whitespace_control() -> None:
    assert strip_generation_tags("a{%- generation -%}b{%- endgeneration -%}c") == "abc"
    assert strip_generation_tags("plain") == "plain"


def test_generation_markers_render_like_plain_text() -> None:
    template = "<|im_start|>{% generation %}{{ messages[0]['content'] }}{% endgeneration %}|im_end|"
    assert render(build(template=template)) == "<|im_start|>hi|im_end|"


def test_missing_variable_is_empty_by_default_and_strict_mode_raises() -> None:
    vector = build(template="{{ undefined_name }}")
    assert render(vector) == ""
    with pytest.raises(RenderError):
        render(vector, strict_undefined=True)


def test_template_syntax_error_becomes_render_error() -> None:
    with pytest.raises(RenderError) as excinfo:
        render(build(template="{% if %}"))
    assert excinfo.value.code == "E_RENDER"


@pytest.mark.parametrize(
    "template",
    [
        "{{ ''.__class__.__mro__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ ''.__class__.__base__.__subclasses__()[0].__init__.__globals__ }}",
    ],
)
def test_sandbox_blocks_python_introspection(template: str) -> None:
    with pytest.raises(RenderError):
        render(build(template=template))


def test_raise_exception_filter_surfaces_the_message() -> None:
    with pytest.raises(RenderError) as excinfo:
        render(build(template="{{ raise_exception('boom') }}"))
    assert "boom" in excinfo.value.detail
