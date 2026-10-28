# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Vector files must be regular files. Directories, devices, and pipes are rejected with
  `E_SCHEMA` instead of being read, and the 2 MB cap is enforced while reading as well
  as from `stat`.
- `--timeout` rejects non-finite values. `nan` and `inf` no longer silently disable the
  command-engine timeout.

## [0.1.0] - 2026-10-26

### Added

- JSON vector schema with fail-closed validation: messages, tools, options, context,
  expected text/token IDs, provenance, and explicit limits (2 MB file, 1,000 messages,
  100,000 token IDs, 100 context keys).
- Reference renderer on `ImmutableSandboxedEnvironment` with `trim_blocks`,
  `lstrip_blocks`, `raise_exception` as a global, and `{% generation %}` marker
  stripping.
- Deterministic mock renderer (`token_ids = 1000 + UTF-8 byte`) for CI token checks.
- `command:NAME` engine adapter: one process per vector, JSON over stdin/stdout, fixed
  argument list, UTF-8, configurable timeout, no shell.
- Text and token-ID diffs with first-difference positions; per-engine error kinds.
- CLI: `validate`, `validate-dir`, `render`, `doctor`; `--json`, `--sarif`, `--timeout`;
  exit codes 0 (match), 1 (mismatch), 2 (schema or render), 3 (engine), 4 (config).
- SARIF 2.1.0 output with rules `CTP001` and `CTP002`.
- Environment fingerprint warnings for Jinja2 (exact) and Python (major.minor).
- 13 seed vectors covering ChatML-style turns, generation prompts, Llama-3-style headers
  with `bos_token`, tool definitions, tool calls with null content, tool results,
  `{% generation %}` markers, Unicode, structured content, and two reasoning-conditional
  vectors inspired by llama.cpp#13404.
- 150 tests across unit, integration and adversarial suites, plus three recorded
  mutation checks (env comparison, diff status, generation-tag stripping).

### Notes

- Pre-built Transformers, llama.cpp and vLLM adapters are not included; engines are wired
  through the documented `command:` protocol.
- The hub→render→record pipeline (`ctp record`) is planned for v0.5.
