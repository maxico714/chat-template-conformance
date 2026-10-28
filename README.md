# chat-template-conformance

[![CI](https://github.com/maxico714/chat-template-conformance/actions/workflows/ci.yml/badge.svg)](https://github.com/maxico714/chat-template-conformance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Chat templates are the Jinja2 snippets in a model's `tokenizer_config.json` that turn a
message list, tool definitions and a generation flag into model input. The template text
travels with the model, but each inference stack evaluates it with its own Jinja
environment and defaults. A template that looks correct in one stack can emit different
bytes in another — extra or missing newlines, dropped markers, a generation prompt that
does not match — and the divergence surfaces as degraded output instead of an error.

`ctp` stores the exact expected rendering as JSON "conformance vectors", replays each
vector through one or more engines, and diffs text and token IDs. A mismatch is a
non-zero exit code, a readable diff, a JSON report, or SARIF for code scanning.

## Scope, honestly

v0.1 is a **conformance harness**, not a bundle of engine integrations:

| Piece | Status in 0.1 |
|---|---|
| Vector schema, limits and validation | shipped |
| Reference renderer (Jinja2, Transformers-compatible settings) | shipped |
| Deterministic mock renderer for CI | shipped |
| `command:NAME` engine adapter (any external engine over stdin/stdout JSON) | shipped |
| Text and token-ID diffs, exit codes, JSON report, SARIF 2.1.0 | shipped |
| Environment fingerprint warnings | shipped |
| Pre-built Transformers / llama.cpp / vLLM adapters | **not shipped** — wire your engine as a `command:` adapter (see below); built-in adapters are v0.5 work |
| Hub fetch + record pipeline (`ctp record`) | not shipped (v0.5) |

There is no "universal compatibility" claim here: a vector records what one engine
produced in one environment, and the harness tells you when another engine or another
environment disagrees.

## Install

```bash
python -m pip install -e ".[dev]"
ctp doctor
```

`ctp doctor` prints the package version, the interpreter, the Jinja2 version and the
engines available in this process; it makes no network calls.

## Quickstart

The seed vectors are conformance fixtures, not runtime package data. They are
included in the GitHub source and source distribution, but not inside the
wheel; from another directory, pass your own vector directory.

```bash
ctp validate-dir vectors
```

```text
PASS 001-chatml-basic [reference]
PASS 002-chatml-multi-turn [reference]
PASS 003-chatml-no-generation-prompt [reference]
PASS 004-llama3-style-bos [reference]
PASS 005-tools-block [reference]
PASS 006-assistant-tool-call [reference]
PASS 007-tool-result-turn [reference]
PASS 008-generation-markers [reference]
PASS 009-unicode-content [reference]
PASS 010-list-content [reference]
PASS 011-reasoning-after-last-user [reference]
PASS 012-reasoning-no-trailing-assistant [reference]
PASS 013-mock-token-ids [reference]
13 vectors, 13 engine checks: 13 matched, 0 mismatched, 0 errors
OK
```

Token-level expectations use the mock engine, which derives token IDs from the rendered
UTF-8 bytes (`1000 + byte`) so CI can exercise the token-diff path without a tokenizer:

```bash
ctp validate --vector vectors/013-mock-token-ids.json --engine mock
```

```text
PASS 013-mock-token-ids [mock]
1 vectors, 1 engine checks: 1 matched, 0 mismatched, 0 errors
OK
```

## A vector

```json
{
  "id": "001-chatml-basic",
  "messages": [{"role": "user", "content": "hi"}],
  "template": "{% for message in messages %}<|im_start|>{{ message['role'] }}\n{{ message['content'] }}<|im_end|>\n{% endfor %}{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}",
  "options": {"add_generation_prompt": true},
  "expected": {
    "reference": {"text": "<|im_start|>user\nhi<|im_end|>\n<|im_start|>assistant\n"}
  },
  "env": {"jinja2": "3.1.6"}
}
```

`expected` is keyed by engine label. Each entry may carry `text`, `token_ids`, or both.
The full field reference, limits and comparison rules are in
[docs/VECTOR_SCHEMA.md](docs/VECTOR_SCHEMA.md).

## Engine protocol

Any renderer can be compared if it speaks one small protocol:

1. `ctp` writes one JSON object to the engine's stdin: the vector payload with `id`,
   `messages`, `tools`, `template`, `bos_token`, `eos_token`, `options` and `context`.
2. The engine writes one JSON object to stdout: `{"text": "..."}` and/or
   `{"token_ids": [1, 2, 3]}`.
3. A non-zero exit code, a timeout, or unparsable output is reported as an engine error.

A runnable example lives in [examples/echo-engine](examples/echo-engine):

```bash
ctp validate --vector examples/echo-engine/vector.json --engine command:echo --command python --command-arg examples/echo-engine/engine.py
```

```text
PASS echo-example [echo]
1 vectors, 1 engine checks: 1 matched, 0 mismatched, 0 errors
OK
```

The adapter always uses a fixed argument list with `shell=False`, passes stdin as UTF-8,
and enforces `--timeout` (default 30 s). No template is executed by the engine wrapper
unless you start an engine that executes it.

## CLI

```text
ctp validate --vector FILE [--engine SPEC ...] [--json] [--sarif FILE]
ctp validate-dir DIR [--engine SPEC ...] [--json] [--sarif FILE]
ctp render --vector FILE
ctp doctor
```

- `--engine SPEC` is `reference`, `mock`, or `command:NAME`; repeatable, default
  `reference`. `command:NAME` requires `--command` and optional `--command-arg`.
- `--json` prints the machine-readable report; `--sarif` additionally writes a
  SARIF 2.1.0 file with rule `CTP001` (output mismatch) and `CTP002` (engine or vector
  error).
- `--timeout SECONDS` applies to every command-engine invocation.
- `ctp render` prints the reference rendering, which is handy when authoring a vector.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | every checked engine matched its expectation |
| 1 | at least one output mismatch |
| 2 | vector is invalid, or the template failed to render |
| 3 | an engine failed, timed out, or could not be started |
| 4 | configuration or usage error (unknown engine, missing `--command`, bad flag) |

Precedence is 4 → 2 → 3 → 1 → 0, so a broken invocation is never reported as a clean
run.

## Environment fingerprint

Rendered bytes depend on the Jinja2 version, so vectors may record one:

```json
"env": {"jinja2": "3.1.6", "python": "3.12.10"}
```

At validation time `jinja2` is compared exactly and `python` by major.minor. A
difference produces a `WARN` line and never changes the exit code — the seed vectors
were recorded on Jinja2 3.1.6, and a newer patch release should be visible, not fatal.
Warnings are also present in `--json` output.

## Templates from the wild

- `{% generation %}` / `{% endgeneration %}` markers are removed before rendering. They
  only delimit assistant spans for token masks and are not valid plain Jinja2 syntax.
- `raise_exception` is available as a template global, as in Transformers.
- Rendering uses `ImmutableSandboxedEnvironment` with `trim_blocks=True`,
  `lstrip_blocks=True` and autoescaping off. Attribute access that would reach Python
  internals is blocked, so a vector cannot execute code.
- Jinja2's default `keep_trailing_newline=False` applies: one trailing newline in the
  template source is not rendered.

## What this is not

- Not a template editor or IDE — see [template-studio](https://github.com/cyanheads/template-studio)
  for interactive editing; `ctp` complements it with conformance data.
- Not a quality or latency benchmark, not a model router, not a serving layer.
- Not a tokenizer: expectations are recorded from an engine you trust, which for v0.1
  means the reference renderer for text and a real engine via `command:` for token IDs.

## Prior art and citations

- `template-studio` (MIT, 0 stars when reviewed on 2026-10-12) edits chat templates; it
  does not ship cross-engine conformance vectors.
- `jinja-compat-tests` (2016) tests generic Jinja2 compatibility, not chat templates.
- llama.cpp's `minja` engine has open template issues — for example
  [#13404](https://github.com/ggml-org/llama.cpp/issues/13404) (Qwen3 multi-turn
  reasoning rendering) and [#27131](https://github.com/ggml-org/llama.cpp/pull/27131)
  (strict template parsing for system messages). Vectors `011` and `012` are
  **pattern-inspired** by the first and record our own expected output; they are not
  byte-level reproductions of the reported engine output.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
python -m pytest
```

The suite covers schema limits, sandbox behaviour, the command protocol, exit-code
precedence, SARIF shape, Unicode output and every seed vector. Each behavioural unit was
also mutation-checked: breaking the env comparison, the diff status, or the
`{% generation %}` stripping makes tests fail.

## License

MIT — see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
