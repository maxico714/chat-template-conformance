# BUILD CHECKLIST — chat-template-conformance

Status: v0.1.0 built, tested and ready for publication (2026-10-26). Every gate below
shows the command that was run and its real result on the build host
(Windows 10.0.26200, Python 3.12.10, Jinja2 3.1.6).

## Gate 0 — Reproducibility spike

- [x] Established that exact output depends on the Jinja2 environment, not on the vector
      alone. Decision: record an optional `env` fingerprint and compare it at validation
      time (`jinja2` exact, `python` major.minor).
- [x] Fixed the seed fingerprint to Jinja2 3.1.6, the version the vectors were rendered
      with, and documented the rule in `docs/VECTOR_SCHEMA.md`.
- [x] No Transformers/llama.cpp/vLLM binaries are available on the host, so no expected
      output in this repository is attributed to them. Bug-inspired vectors carry
      `source.note = "pattern-inspired regression, not a byte-level reproduction"`.
- [x] Documented the deviation: the scaffold planned built-in engine adapters; shipping
      them without ever running the engines would be an unverified claim.

## Gate 1 — L0 static (every commit)

- [x] `ruff check .` → `All checks passed!`
- [x] `ruff format --check .` → all files formatted
- [x] `mypy src` → `Success: no issues found in 8 source files`
- [x] `python -m pytest --collect-only -q` → collection succeeds; full run 150 passed

## Gate 2 — L1 units (schema + adapters)

- [x] Vector schema: 32-case reject matrix (missing fields, wrong types, bad engine
      labels, bool/negative/oversized token IDs, unknown keys, limits) plus accept cases.
- [x] `load_vector`: missing file, malformed JSON with line number, non-UTF-8 file,
      oversized file.
- [x] Renderer: trim/lstrip semantics, trailing-newline behaviour, `bos_token`/`eos_token`
      defaults, context variables, `{% generation %}` stripping, strict-undefined mode,
      syntax errors mapped to `E_RENDER`.
- [x] Sandbox: three `__class__`/`__subclasses__` escape attempts raise `RenderError`.
- [x] Command adapter: text-only, tokens-only, both, invalid JSON, non-object JSON, empty
      object, bad text, bad token IDs, non-zero exit with stderr, timeout, missing binary.
- [x] Env fingerprint: match, patch-only difference, minor mismatch, non-string value.
- [x] **Mutation sanity:** removing the env comparison → 3 tests fail; restoring → green.
- [x] **Mutation sanity:** forcing diff status to `match` → 3 tests fail; restoring → green.
- [x] **Mutation sanity:** disabling `{% generation %}` stripping → 2 tests fail;
      restoring → green.

## Gate 3 — L2 integration

- [x] CLI subprocess: match → 0, mismatch → 1, schema error → 2, engine error → 3,
      configuration/usage error → 4; precedence verified in unit and CLI tests.
- [x] `ctp validate-dir vectors` → `13 vectors, 13 engine checks: 13 matched, 0
      mismatched, 0 errors`, `OK`.
- [x] `ctp validate --vector vectors/013-mock-token-ids.json --engine mock` → pass with
      hand-computed IDs `[1104, 1105]`.
- [x] SARIF 2.1.0: schema URL, version, rules `CTP001`/`CTP002`, `level: error`, relative
      POSIX URI, `startLine: 1`; green runs produce no results. JSON output summary
      verified.
- [x] Unicode path: `ctp render` of `009-unicode-content` returns
      `héllo 世界 🙂` byte-for-byte through a Windows pipe (streams forced to UTF-8).

## Gate 4 — L3 end to end (revised)

- [x] Readme quickstart commands run verbatim against the installed package.
- [x] `examples/echo-engine` exercises the full command protocol from the README, and the
      same command is a test and a CI step.
- [ ] Real Transformers adapter — deferred to v0.5 (engine not installable/verifiable
      here; recorded in `docs/EVIDENCE.md`).
- [ ] Real llama.cpp / vLLM adapters — deferred to v0.5 for the same reason.
- [x] Exit codes 0/1/2/3/4 verified by subprocess tests.

## Gate 5 — L5 adversarial

- [x] Malformed JSON → clean `E_SCHEMA` with line number.
- [x] 2,000,001-byte file → rejected before parsing.
- [x] 100,001 token IDs → rejected before rendering.
- [x] 1,001 messages → rejected.
- [x] Non-UTF-8 file → `E_SCHEMA`.
- [x] Engine version mismatch → `WARN`, exit stays 0.
- [x] Jinja2 sandbox escape attempt → blocked, exit 2, no code execution.
- [x] Engine hangs → timeout → exit 3; engine exits non-zero → exit 3 with stderr;
      engine writes garbage → exit 3.

## Gate 6 — Differentiation and honesty audit

- [x] README states the scope table (no built-in engine adapters in 0.1), cites
      template-studio, and labels bug-inspired vectors as pattern-inspired.
- [x] `template-studio` is not cloned; no code or assets copied. Dependencies: Jinja2 and
      MarkupSafe only (BSD-3-Clause), listed in `THIRD_PARTY_NOTICES.md`.
- [x] Env fingerprint recorded; reproducibility conditional and documented; no
      "universal compatibility" claim.
- [x] No `TODO`/`FIXME` in `src/`.
- [x] Secrets scan: no credentials, no `.env`, `.gitignore` excludes `.agent/` and the
      root `AGENTS.md`.

## Gate 7 — L4 clean environment

- [x] Fresh copy without caches or virtualenv → `python -m venv` → `pip install -e
      ".[dev]"` → `ruff`, `mypy`, `150 passed`.
- [x] Wheel and sdist build (`python -m build`), `twine check` passes.
- [x] Wheel installs into an empty virtualenv; `ctp doctor`, `ctp validate-dir vectors` and
      the example adapter run from the installed package.

## Gate 8 — Naming and packaging (G3-gated)

- [ ] PyPI name availability for `chat-template-conformance` / `ctp` — **not run**: Gate 8
      requires operator approval (G3). v0.1 is distributed from source and GitHub only.
- [ ] Registry publication — not performed (G3 not granted).

## Definition of done (v0.1)

Gates 0–7 green with evidence above; Gate 8 deliberately not started. The hub→record
pipeline remains the binding v0.5 condition, as recorded in `docs/ROADMAP.md`.
