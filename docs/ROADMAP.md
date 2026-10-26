# ROADMAP — chat-template-conformance

SemVer; Keep a Changelog. Cite and extend neighbouring tools; do not clone them.

## v0.1 — Walking skeleton (released 2026-10-26)

- [x] Vector schema with fail-closed validation and explicit limits.
- [x] Reference renderer with Transformers-compatible Jinja settings, `raise_exception`
      and `{% generation %}` handling.
- [x] Deterministic mock renderer for CI token checks.
- [x] `command:NAME` engine adapter (stdin/stdout JSON) instead of unverified built-in
      engine adapters.
- [x] Text and token-ID diffs, exit codes 0–4, JSON and SARIF 2.1.0 output.
- [x] Environment fingerprint warnings.
- [x] 13 seed vectors, including two pattern-inspired by llama.cpp#13404.
- [x] `doctor`, README quickstart, CI matrix (Ubuntu/Windows × 3.10/3.12/3.13).

**Riskiest assumption, resolved:** byte-level reproducibility across environments. It is
not guaranteed, so vectors record an environment fingerprint and the harness warns on
drift instead of pretending output is universal.

## v0.5 — Core value

- [ ] `ctp record` pipeline: fetch a template from the Hugging Face Hub, render with the
      reference engine, snapshot the template text, and append `expected` entries
      (binding condition for v1).
- [ ] First-party adapters that ship with tests run in CI against pinned engine versions:
      Transformers (`apply_chat_template`), llama.cpp (`llama-cli` or server), vLLM.
      Each adapter must be covered by a version-pinned job; no adapter without a run.
- [ ] Vector contribution guide and a template for community vectors.
- [ ] Validate SARIF against GitHub code-scanning schema in CI.

## v1.0 — Production-ready

- [ ] Conformance badge for repositories whose vectors pass on every declared engine.
- [ ] PR diff mode: validate only vectors touched by a change.
- [ ] Signed vector bundles; SBOM; reproducible release artifacts.
- [ ] Registry publication (requires G3 approval and a name-availability check).

## Post-1.0 (parked, not promised)

- TGI and exllama adapters; quality and latency benchmarking; model routing; GUI;
  Prometheus metrics.

## Maintenance cadence

- Engine or Jinja2 release changes: refresh `env` fingerprints and re-record affected
  expectations (patch release).
- Vector schema change: major version.
