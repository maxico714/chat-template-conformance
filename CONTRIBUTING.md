# Contributing

## Setup

```bash
git clone https://github.com/maxico714/chat-template-conformance
cd chat-template-conformance
python -m pip install -e ".[dev]"
```

Python 3.10 or newer. No engine binaries, no network access and no credentials are
needed for the test suite.

## Checks

Run all of these before opening a pull request; CI runs the same commands on Ubuntu and
Windows for Python 3.10, 3.12 and 3.13.

```bash
ruff check .
ruff format --check .
mypy
python -m pytest
```

## Adding a vector

1. Copy a neighbouring file in `vectors/` and give it the next number and a descriptive
   id.
2. Write the template and messages first, then run `ctp render --vector <file>` to see the
   reference output.
3. Put that output in `expected.reference.text` **only if** you have checked it by hand
   against the template — do not paste an output you cannot explain.
4. If the vector targets an external engine, record the engine version in `env` and cite
   the issue or specification in `source`.
5. `ctp validate-dir vectors` must stay green, and the count assertions in
   `tests/integration/test_seed_vectors.py` need updating when the set grows.

Vectors that reproduce a reported bug must say so honestly in `source.note`; write
"pattern-inspired" when you re-create the shape of a bug rather than its exact output.

## Code style

- Keep the schema fail-closed: unknown fields are errors, and a missing expectation is a
  schema error rather than a silent pass.
- Never weaken a test, linter rule or type check to make CI green.
- New behaviour needs a test that fails without the change. For core comparison logic,
  confirm the test fails when the logic is deliberately broken (mutation check) and
  record it in the pull request.
- Keep user-facing errors actionable and free of internal stack traces.

## Commits and pull requests

- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- One logical change per pull request, with the commands you ran in the description.
- By contributing you agree your work is licensed under the MIT license.
