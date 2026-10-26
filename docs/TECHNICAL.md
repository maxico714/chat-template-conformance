# TECHNICAL — chat-template-conformance

Status: v0.1.0 (2026-10-26). Python >= 3.10, one runtime dependency (Jinja2).

## Architecture

```text
 vector.json
    │
    ▼
 schema.load_vector ──► VectorError (E_SCHEMA, path-qualified)
    │
    ▼
 validate.check_vector ──► ensure_engine_spec (E_CONFIG)
    │
    ├── reference ──► render.render ──► text
    ├── mock ───────► render.render ──► text + token_ids (1000 + UTF-8 byte)
    └── command:NAME ► subprocess: payload JSON → stdout JSON
    │
    ▼
 _compare(expected, actual) ──► EngineCheck (match | mismatch | error)
    │
    ▼
 Report ──► text | JSON | SARIF 2.1.0 ──► exit code 0/1/2/3/4
```

No services, no database, no network access.

## Modules

| Module | Responsibility |
|---|---|
| `ctp.schema` | Parse and validate vectors; limits; typed `Vector` model |
| `ctp.render` | Sandboxed Jinja2 rendering; generation-marker stripping; `RenderError` |
| `ctp.adapters` | reference/mock renderers, command protocol, config and engine errors, env fingerprint |
| `ctp.validate` | Engine checks, exact diffs, report aggregation, exit-code precedence |
| `ctp.report` | Human-readable report and SARIF 2.1.0 |
| `ctp.cli` | argparse CLI, UTF-8 stream setup, error-to-exit-code mapping |

## Vector model

`Vector` is immutable and carries `id`, `messages`, `template`, `expected`, `tools`,
`bos_token`, `eos_token`, `options`, `context`, `env`, `source`, `description` and the
source `path`. `payload()` produces the exact render/engine input; `expected` and `env`
stay local to the harness. See [VECTOR_SCHEMA.md](VECTOR_SCHEMA.md).

## Rendering

`render()` builds `ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True,
autoescape=False)`, registers `raise_exception` as a global, and supplies `messages`,
`tools`, `bos_token` (default `""`), `eos_token` (default `""`),
`add_generation_prompt`, plus `context`. `{% generation %}`/`{% endgeneration %}` tags are
removed before parsing because they are not plain Jinja2 syntax. Any exception becomes
`RenderError` (`E_RENDER`), which the validator classifies as a schema-level error
(exit 2).

Optional `strict_undefined=True` switches to `StrictUndefined` for library users; the CLI
keeps the permissive default because real templates probe for optional variables.

## Comparison

- Text: exact equality; the report names the first differing character and shows
  snippets.
- Token IDs: exact tuple equality; the report names the first differing index or the
  length difference.
- A requested engine without an `expected` entry is a schema error, never a silent skip.
- One engine failing does not stop the others; the exit code takes the most severe kind
  present: config (4) → schema (2) → engine (3) → mismatch (1) → match (0).

## Command adapter

`subprocess.run([exe, *args], input=json, capture_output=True, text=True,
encoding="utf-8", timeout=..., shell=False)`. Payload and response shapes are documented
in VECTOR_SCHEMA.md. Failure mapping: missing executable/permission → `EngineUnavailable`
(engine error, exit 3); timeout → engine error; non-zero exit → engine error with up to
300 characters of stderr; unparsable or invalid JSON → engine error.

## Environment fingerprint

`environment_fingerprint()` returns `python` and `jinja2` versions. `env_mismatches()`
compares recorded values: Jinja2 exactly, Python by major.minor. Results are warnings on
the vector check (text report `WARN` line, `warnings` in JSON) and never affect the exit
code.

## Outputs

- Text: `PASS`/`FAIL`/`ERROR` per engine, optional `WARN`, summary line, `OK`/`FAILED`.
- JSON: vectors → checks → status/detail/kind, plus counts.
- SARIF 2.1.0: `CTP001` for mismatches, `CTP002` for engine/vector errors, `level: error`,
  one location per result (artifact URI, line 1). Matches are not reported.

## Threat model (STRIDE-lite)

| Threat | Mitigation |
|---|---|
| Malicious vector executes code | Schema limits; `ImmutableSandboxedEnvironment`; no `eval`; unknown fields rejected |
| Resource exhaustion | 2 MB file cap, 1,000 messages, 100,000 token IDs, 100 context keys, per-engine timeout |
| Command injection | Fixed argv list, `shell=False`, no shell interpolation |
| Untrusted engine output | Strict JSON shape checks; bounded stderr in errors |
| Secret leakage | No network, no telemetry, no environment dumping; `doctor` prints versions only |
| Supply chain | One runtime dependency (Jinja2) pinned by range; lock-free build with hash-pinned CI actions |

## Performance

Validation is linear in vector count. The 13 seed vectors validate in well under a
second; the 150-test suite runs in roughly 12 seconds on the build host, dominated by
subprocess tests. Memory is bounded by the file cap and token limits.

## Testing

| Level | Coverage |
|---|---|
| L0 | ruff (E,F,I,B,UP,SIM), `ruff format --check`, strict mypy on `src` |
| L1 | schema accept/reject matrix, renderer semantics, sandbox escape, adapter protocol, diff and exit-code units |
| L2 | CLI subprocess runs: match/mismatch/schema/engine/config paths, JSON, SARIF, Unicode |
| L3 | README quickstart commands and the runnable `examples/echo-engine` adapter |
| L4 | fresh clone, editable install, full suite, CLI smoke |
| L5 | 2 MB file, 100,001 token IDs, 1,001 messages, non-UTF-8, malformed JSON, engine crash, garbage output, timeout, sandbox escape |
| Mutation | env comparison removed; diff status forced to match; generation stripping disabled — each caused failures before being restored |

CI runs the matrix on Ubuntu and Windows for Python 3.10, 3.12 and 3.13.

## Packaging

Pure-Python wheel and sdist via setuptools. Console script `ctp = ctp.cli:main`. Registry
publication is gated (G3) and not performed by this build.

## Repository layout

```text
chat-template-conformance/
  src/ctp/{schema,render,adapters,validate,report,cli,__init__,__main__}.py
  vectors/                     13 seed vectors
  examples/echo-engine/        runnable command-engine example
  tests/{unit,integration,adversarial}/
  docs/{PRODUCT,TECHNICAL,ROADMAP,EVIDENCE,VECTOR_SCHEMA}.md
```
