# PRODUCT — chat-template-conformance

Status: v0.1.0 built and verified (2026-10-26). Date of scaffold: 2026-10-12.

## Problem

Chat templates (Jinja2 snippets in Hugging Face `tokenizer_config.json`) control how
multi-turn messages, tool calls and system prompts become model input. Each inference
stack evaluates the same template with its own Jinja environment and defaults, so a
template can render different bytes — and therefore different tokens — across engines.
The failure is silent: wrong special tokens, missed tool-call markers, shifted multi-turn
boundaries, and quality degradation that looks like a model problem.

Open reports that motivated this work include llama.cpp
[#13404](https://github.com/ggml-org/llama.cpp/issues/13404) (Qwen3 multi-turn reasoning
rendering) and [#27131](https://github.com/ggml-org/llama.cpp/pull/27131) (strict template
parsing for system messages). There is no widely adopted, engine-neutral conformance
suite for chat templates.

## Target users

1. **LLM platform engineer (primary):** runs several inference stacks and needs to prove
   that a template produces identical input before deploying.
2. **Model author / template designer (secondary):** ships a template and wants it tested
   against engines with recorded expectations instead of ad-hoc scripts.
3. **Inference-engine contributor (tertiary):** wants a regression vector for a template
   bug that survives review.

## Jobs-to-be-done

- "Check that this template renders exactly this text, and tell me the first character
  where an engine disagrees."
- "Record a token-level expectation from a real engine and replay it in CI."
- "Add a regression vector for the tool-call or reasoning-marker bug we just fixed."

## Value proposition

Engine-neutral chat-template conformance vectors plus a validator: replay a template
through each engine, diff text and token IDs exactly, and fail CI before the divergence
reaches production.

## Non-goals (explicit)

- Not a template editor or IDE (template-studio's niche; we cite it, do not clone it).
- Not a quality or latency benchmark, model router, or serving layer.
- Not a tokenizer or an inference engine.
- No telemetry, no network calls at validation time.

## Delivered scope (v0.1)

**Shipped**

- Vector schema with fail-closed validation and explicit limits.
- Reference renderer: `ImmutableSandboxedEnvironment`, `trim_blocks`/`lstrip_blocks`,
  `raise_exception` global, `{% generation %}` marker stripping.
- Deterministic mock renderer for CI token checks.
- `command:NAME` adapter: any external engine over stdin/stdout JSON, fixed argv,
  `shell=False`, timeout.
- Exact text and token-ID diffs; JSON report; SARIF 2.1.0 (`CTP001`, `CTP002`).
- Exit codes 0/1/2/3/4 with documented precedence.
- Environment fingerprint warnings (Jinja2 exact, Python major.minor).
- 13 seed vectors and 150 tests, including adversarial and mutation checks.

**Deliberately deferred**

- Built-in Transformers, llama.cpp and vLLM adapters. None of those engines can be
  installed and verified on the build host, and shipping an adapter that has never run
  against the engine would be an unverified claim. v0.1 instead ships a documented,
  tested protocol (`command:NAME`) that connects any of them, with a runnable example.
- `ctp record --hub` pipeline (v0.5, binding condition for v1).

## Success criteria

| Criterion | Measure | Status |
|---|---|---|
| L0 static | ruff, format, strict mypy clean | met |
| L1 units | schema, renderer, adapters, diff units green | met |
| L2 integration | mock and command engines end to end, exit codes correct | met |
| L3 end to end | CLI quickstart and example adapter run verbatim | met |
| L4 clean environment | fresh clone + editable install + suite green | met |
| L5 adversarial | malformed, oversized, Unicode, sandbox escape, timeout, crash | met |
| Honesty | scope limits and deferred adapters documented; no compatibility claim | met |
| Differentiation | cites template-studio; bug-inspired vectors labeled pattern-inspired | met |

## Honest comparison

| Project | What it does | Where it differs |
|---|---|---|
| template-studio | Interactive template editing | We do not edit templates; we record and compare renderings |
| jinja-compat-tests | Generic Jinja2 compatibility (2016) | Not chat-template or engine specific |
| llama.cpp `minja` | The engine under test | We provide vectors and a harness, not an engine |
| Ad-hoc `apply_chat_template` scripts | One-off checks | We keep expectations as data, diff exactly, and fail CI |

## Naming and license

- Name: `chat-template-conformance`; CLI: `ctp`. Registry availability is checked only at
  the release gate (G3), since v0.1 is distributed from source.
- License: MIT. Jinja2 and MarkupSafe are BSD-3-Clause (compatible).

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Engine version drift changes output | High | Env fingerprint warnings; expectations are per engine and environment |
| Mock-only CI hides real-engine divergence | Medium | Command protocol is tested end to end; real-engine runs are a release step |
| Scope creep toward a template editor | Medium | Non-goals and comparison table |
| Hub templates change under users | Medium | v0.1 has no hub fetch; vectors snapshot the template text |
