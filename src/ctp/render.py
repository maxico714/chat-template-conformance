from __future__ import annotations

import re
from typing import Any, NoReturn

from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateRuntimeError
from jinja2.sandbox import ImmutableSandboxedEnvironment

from .schema import Vector

_GENERATION_TAG = re.compile(r"\{%-?\s*(?:end)?generation\s*-?%\}")


class RenderError(ValueError):
    code = "E_RENDER"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def _raise_exception(message: str) -> NoReturn:
    raise TemplateRuntimeError(str(message))


def _environment(strict_undefined: bool) -> ImmutableSandboxedEnvironment:
    options: dict[str, Any] = {
        "trim_blocks": True,
        "lstrip_blocks": True,
        "autoescape": False,
    }
    if strict_undefined:
        options["undefined"] = StrictUndefined
    return ImmutableSandboxedEnvironment(**options)


def strip_generation_tags(template: str) -> str:
    """Drop `{% generation %}` markers, which Transformers supports but plain Jinja does not.

    The markers only delimit assistant spans for token masks; rendering text with them
    present would be a syntax error, so removing the tags keeps the visible output.
    """
    return _GENERATION_TAG.sub("", template)


def render(vector: Vector, *, strict_undefined: bool = False) -> str:
    source = strip_generation_tags(vector.template)
    environment = _environment(strict_undefined)
    environment.globals["raise_exception"] = _raise_exception
    context: dict[str, Any] = {
        "messages": [dict(message) for message in vector.messages],
        "tools": [dict(tool) for tool in vector.tools],
        "bos_token": vector.bos_token or "",
        "eos_token": vector.eos_token or "",
        "add_generation_prompt": vector.options.add_generation_prompt,
    }
    context.update(vector.context)
    try:
        template = environment.from_string(source)
        return template.render(context)
    except Exception as exc:
        raise RenderError(f"{type(exc).__name__}: {exc}") from None
