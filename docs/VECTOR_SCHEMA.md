# Vector schema (v0.1)

A vector is one JSON file that records a template, its inputs, and the exact output at
least one engine produced. Files are validated before anything is rendered; the first
error stops parsing for that file with an `E_SCHEMA` message that names the failing
path (for example `messages[0].role`).

## Top-level fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | 1–200 characters, unique within a directory |
| `messages` | array | yes | 1–1000 message objects; see below |
| `template` | string | yes | at most 200,000 characters of Jinja2 |
| `expected` | object | yes | engine label → `{text?, token_ids?}` |
| `tools` | array | no | up to 1000 objects, passed through unchanged |
| `bos_token` | string | no | available to the template; defaults to `""` |
| `eos_token` | string | no | available to the template; defaults to `""` |
| `options.add_generation_prompt` | boolean | no | defaults to `false` |
| `context` | object | no | up to 100 extra template variables; reserved names rejected |
| `env` | object | no | environment fingerprint; see below |
| `source` | object | no | free-form provenance (issue URL, note) |
| `description` | string | no | human-readable summary |

Unknown top-level keys are rejected so a typo cannot silently disable an expectation.

## Messages

Each message is an object with:

- `role` (required, non-empty string)
- `content` (optional): string, array, object, or `null`
- `tool_calls` (optional): array or `null`
- any additional keys (for example `tool_call_id`) are preserved and passed to the
  template

The harness does not interpret message semantics; it only validates shapes, so vectors
can cover engine-specific extras without schema changes.

## Expected outputs

```json
"expected": {
  "reference": {"text": "<|im_start|>user\nhi<|im_end|>\n"},
  "mock": {"text": "hi", "token_ids": [1104, 1105]},
  "llama_cpp": {"token_ids": [1, 2, 3]}
}
```

- Keys are engine labels: `[A-Za-z][A-Za-z0-9_.-]*`.
- Each entry must contain `text`, `token_ids`, or both; unknown entry keys are rejected.
- Token IDs are integers in `0 .. 2^63-1`; booleans are rejected; at most 100,000 IDs per
  engine.
- `text` is compared exactly (including newlines and Unicode).
- When a requested engine has no entry, the vector is reported as a schema error rather
  than silently skipped.

## Environment fingerprint

```json
"env": {"jinja2": "3.1.6", "python": "3.12.10"}
```

| Key | Comparison |
|---|---|
| `jinja2` | exact string match against the running version |
| `python` | major.minor match (`3.12.10` matches `3.12.x`) |
| other keys | recorded, not compared |

Differences are warnings (`WARN` line, `warnings` array in `--json`). They never change
the exit code. A non-string version value is also a warning.

## Reference renderer semantics

The `reference` engine renders with `jinja2.sandbox.ImmutableSandboxedEnvironment`:

- `trim_blocks=True`, `lstrip_blocks=True`, `autoescape=False`
- `{% generation %}` / `{% endgeneration %}` tags are removed before parsing
- `raise_exception(message)` is available as a global
- `messages`, `tools`, `bos_token`, `eos_token`, `add_generation_prompt` and `context`
  are the only inputs
- undefined variables render as empty text by default; the library API can enable
  `StrictUndefined`
- Jinja2's default trailing-newline behaviour applies (one trailing newline in the
  template source is dropped)

## Mock renderer

`mock` renders with the reference engine and derives token IDs as `1000 + byte` for each
UTF-8 byte of the rendered text. It exists so CI can exercise token comparison without a
tokenizer; it is not a model tokenizer and must not be used as one.

## Command engine protocol

`command:NAME` starts a process once per vector:

- stdin: one UTF-8 JSON object — `id`, `messages`, `tools`, `template`, `bos_token`,
  `eos_token`, `options`, `context` (`bos_token`/`eos_token` may be `null`)
- stdout: one UTF-8 JSON object with `text` (string) and/or `token_ids` (array of
  integers)
- exit code: `0` on success; any non-zero exit is an engine error and stderr is included
  in the message (truncated to 300 characters)
- timeout: `--timeout`, default 30 seconds
- no shell: the executable and arguments are passed as a list with `shell=False`

The label after `command:` (for example `command:llama_cpp` → `llama_cpp`) selects the
`expected` entry.

## Limits

| Limit | Value |
|---|---|
| Vector file size | 2,000,000 bytes |
| Template length | 200,000 characters |
| Messages | 1,000 |
| Tools | 1,000 |
| Token IDs per engine | 100,000 |
| Context keys | 100 |
| `id` length | 200 characters |

Exceeding a limit is an `E_SCHEMA` error before rendering, so a hostile or accidental
large file cannot force unbounded work.
