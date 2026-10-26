from __future__ import annotations

import argparse
import json
import platform
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import jinja2

from . import __version__
from .adapters import CommandConfig, ConfigError, available_engines
from .render import RenderError, render
from .report import format_text, to_sarif
from .schema import VectorError, load_vector
from .validate import Report, validate_directory, validate_vectors


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(4, f"error: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="ctp",
        description="Validate chat-template rendering against engine-neutral vectors.",
    )
    parser.add_argument("--version", action="version", version=f"ctp {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def engine_args(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--engine",
            action="append",
            dest="engines",
            help="reference, mock, or command:NAME (repeatable; default reference)",
        )
        target.add_argument(
            "--command",
            dest="engine_command",
            help="executable used by command:NAME engines",
        )
        target.add_argument("--command-arg", action="append", dest="command_args", default=[])
        target.add_argument("--timeout", type=float, default=30.0)

    validate_cmd = sub.add_parser("validate", help="validate one vector file")
    validate_cmd.add_argument("--vector", required=True)
    engine_args(validate_cmd)
    validate_cmd.add_argument("--json", action="store_true")
    validate_cmd.add_argument("--sarif", help="write a SARIF 2.1.0 report to this path")

    dir_cmd = sub.add_parser("validate-dir", help="validate every *.json vector in a directory")
    dir_cmd.add_argument("directory")
    engine_args(dir_cmd)
    dir_cmd.add_argument("--json", action="store_true")
    dir_cmd.add_argument("--sarif", help="write a SARIF 2.1.0 report to this path")

    render_cmd = sub.add_parser("render", help="print the reference rendering of a vector")
    render_cmd.add_argument("--vector", required=True)

    sub.add_parser("doctor", help="show versions and available engines")
    return parser


def _command_config(args: argparse.Namespace) -> CommandConfig | None:
    args_list = tuple(args.command_args or ())
    executable = args.engine_command
    if executable is None:
        if args_list:
            raise ConfigError("--command-arg requires --command")
        return None
    return CommandConfig(exe=executable, args=args_list, timeout=args.timeout)


def _engines(args: argparse.Namespace) -> list[str]:
    return list(args.engines) if args.engines else ["reference"]


def _emit(report: Report, args: argparse.Namespace) -> int:
    if args.sarif:
        payload = to_sarif(report)
        Path(args.sarif).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_text(report))
    return report.exit_code


def _validate(args: argparse.Namespace) -> int:
    vector = load_vector(args.vector)
    config = _command_config(args)
    report = validate_vectors([vector], _engines(args), config)
    return _emit(report, args)


def _validate_dir(args: argparse.Namespace) -> int:
    config = _command_config(args)
    report = validate_directory(args.directory, _engines(args), config)
    return _emit(report, args)


def _render(args: argparse.Namespace) -> int:
    vector = load_vector(args.vector)
    try:
        text = render(vector)
    except RenderError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def _doctor() -> int:
    print(f"ctp {__version__}")
    print(f"python {platform.python_version()} ({sys.executable})")
    print(f"jinja2 {jinja2.__version__}")
    print(f"engines: {', '.join(available_engines(None))}")
    print("command adapter: configure with --command / --command-arg")
    print("network: none")
    return 0


def _configure_streams() -> None:
    """Force UTF-8 output so rendered text survives non-UTF-8 console code pages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_streams()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args)
        if args.command == "validate-dir":
            return _validate_dir(args)
        if args.command == "render":
            return _render(args)
        if args.command == "doctor":
            return _doctor()
    except VectorError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    parser.error(f"unknown command {args.command}")
    return 4


__all__ = ["main"]
