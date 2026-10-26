# EVIDENCE — chat-template-conformance

Research summary from the selection round (access date 2026-10-12), plus build-time
verification on 2026-10-26 and the decisions taken when the scaffold met reality.

## Gap class

Occupied but incomplete (F-adjacent). The niche exists, but the tooling is thin:

- Hugging Face's 2026 chat-template handbook and `template-studio` (0 stars, MIT at
  review time) cover authoring and documentation, not cross-engine conformance vectors.
- `jinja-compat-tests` (2016) tests generic Jinja2 behaviour, not chat templates.
- llama.cpp's `minja` engine carries template-related open issues and TODOs.
- No reviewed project shipped engine-neutral vectors, an automated recording pipeline and
  multi-engine adapters together.

## Demand evidence (3/5, deliberately capped)

- Real artefacts: llama.cpp issues about template semantics; minja TODO items; repeated
  production reports of template/tokenizer divergence across engines.
- Cap reason: niche intersection (chat templates × multiple engines × conformance). No
  single viral discussion, and `template-studio`'s low traction shows limited demand for
  template tooling generally.

## Build-time verification (2026-10-26)

Claims that were checked against the live issue tracker before being cited:

| Claim from scaffold | Verified fact | Consequence |
|---|---|---|
| llama.cpp #27131 is a template divergence bug | Open **pull request** "Fix Jinja strict template parsing for system messages" | Cited as a PR about strict parsing; no vector claims to reproduce it |
| llama.cpp #13404 is a template divergence bug | Open issue about Qwen3 multi-turn reasoning rendering | Vectors 011/012 model the conditional shape and say "pattern-inspired, not byte-level" |
| Transformers / llama.cpp / vLLM can be exercised here | No engine binaries or tokenizers on the build host; installing them was not feasible within the run | v0.1 ships a tested `command:` protocol instead of unverifiable adapters |
| Vectors are engine-neutral by default | False; rendered bytes depend on the Jinja2 environment | `env` fingerprint recorded; drift produces warnings, never silent passes |

## Corrections carried forward

| Earlier claim | Correction |
|---|---|
| "No chat-template tools exist" | False — template-studio and jinja-compat-tests exist; this is F-adjacent, not a pure gap |
| "Engines are fully compatible" | False — open issues document divergence |
| "Vectors are reproducible everywhere" | False — reproducibility is conditional on environment; the schema records it |
| "Expected outputs can be recorded from Transformers in this run" | Not achieved; recording from real engines requires them installed, which is v0.5 work |

## Score (selection round 4, 60/105; survived with conditions)

Demand 3×5 | Gap 2×4 | Feasibility 3×4 | Value 3×3 | Maintenance 3×2 | Distribution 2×2 |
Fit 3×1.

Conditions and how v0.1 addresses them:

| Condition | Status |
|---|---|
| Engine-neutral JSON vectors | Met — schema is engine-agnostic; expectations are per engine label |
| Automated hub→render→record pipeline as v1 condition | Not met in 0.1; explicitly scheduled for 0.5 |
| Differentiate from template-studio | Met — README and PRODUCT cite it and state the difference |
| Scope pinned to (template, messages, env, engine version) → exact bytes | Met — fingerprint stored, warnings on drift, exact comparison |

## Known weaknesses, stated plainly

- CI exercises the reference, mock and command engines; it does not exercise a real
  llama.cpp or vLLM build. Divergence between those engines is the motivation for the
  tool, not something this repository has reproduced.
- The mock tokenizer is a deterministic stub; token expectations from real engines must be
  recorded by the user via `command:`.
- 13 seed vectors are a starting suite, not coverage of the long tail of community
  templates.
