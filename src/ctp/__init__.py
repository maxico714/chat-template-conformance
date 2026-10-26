"""Engine-neutral conformance vectors and validator for chat templates."""

from .adapters import (
    CommandConfig,
    ConfigError,
    EngineError,
    EngineUnavailable,
    RenderResult,
    env_mismatches,
    environment_fingerprint,
)
from .render import RenderError, render
from .report import format_text, to_sarif
from .schema import Expected, Options, Vector, VectorError, load_vector, parse_vector
from .validate import Report, check_vector, validate_directory, validate_vectors

__version__ = "0.1.0"

__all__ = [
    "CommandConfig",
    "ConfigError",
    "EngineError",
    "EngineUnavailable",
    "Expected",
    "Options",
    "RenderError",
    "RenderResult",
    "Report",
    "Vector",
    "VectorError",
    "__version__",
    "check_vector",
    "env_mismatches",
    "environment_fingerprint",
    "format_text",
    "load_vector",
    "parse_vector",
    "render",
    "to_sarif",
    "validate_directory",
    "validate_vectors",
]
