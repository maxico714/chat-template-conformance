# Third-party notices

This project contains no vendored third-party source code.

## Runtime dependencies

| Package | Version constraint | License | Purpose |
|---|---|---|---|
| [Jinja2](https://pypi.org/project/Jinja2/) | `>=3.1,<4` | BSD-3-Clause | Render chat templates |
| [MarkupSafe](https://pypi.org/project/MarkupSafe/) | transitively via Jinja2 | BSD-3-Clause | String escaping used by Jinja2 |

## Development-only dependencies

Installed via the `dev` extra; not required at runtime.

| Package | Version constraint | License | Purpose |
|---|---|---|---|
| [pytest](https://pypi.org/project/pytest/) | `>=8` | MIT | Test runner |
| [ruff](https://pypi.org/project/ruff/) | `>=0.6` | MIT | Linter and formatter |
| [mypy](https://pypi.org/project/mypy/) | `>=1.10` | MIT | Static type checking |
| [setuptools](https://pypi.org/project/setuptools/) | `>=77` | MIT | Build backend and editable installs |

## References, not copied code

- Template syntax in the seed vectors is written from public documentation of the
  ChatML and Llama 3 chat formats. No model files, tokenizer files or template text
  are redistributed here.
- Vectors `011` and `012` are pattern-inspired by behaviours reported in
  [llama.cpp#13404](https://github.com/ggml-org/llama.cpp/issues/13404). They do not
  copy engine code and are not byte-level reproductions of that report.
- `huggingface/transformers` is referenced as the reference semantics for
  `{% generation %}` markers and the `raise_exception` template global. No
  Transformers code or license text is redistributed; Transformers is Apache-2.0.

## Names and trademarks

Llama, ChatML and Hugging Face are names of their respective owners. This project
is not affiliated with or endorsed by any of them; the names appear only to describe
the template formats the vectors exercise.
