# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Open a private report through GitHub's "Report a vulnerability" form on the repository's
Security tab. Please do not open a public issue for anything that could execute code,
escape the template sandbox, or read files outside the working directory.

Include the version (`ctp --version`), the platform, the vector or template involved, and
a minimal reproduction. You can expect an acknowledgement within seven days and a
remediation plan or a reasoned decision within thirty days.

## Threat model in brief

- Vectors are untrusted input. They are schema-validated with hard limits before any
  rendering: 2 MB per file, 1,000 messages, 100,000 token IDs per engine.
- Templates render in `jinja2.sandbox.ImmutableSandboxedEnvironment`; attribute access
  that reaches Python internals is rejected. No vector can execute arbitrary code through
  the reference renderer.
- The `command:` adapter runs an executable **you** specify with a fixed argument list,
  `shell=False`, a timeout, and JSON over stdin/stdout. It does not sandbox that
  executable: only point it at engines you trust.
- The tool makes no network requests. There is no telemetry.
- Reports are written to the paths you specify; SARIF URIs are relative to the working
  directory where possible.
