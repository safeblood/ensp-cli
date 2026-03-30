"""Output formatting utilities for CLI commands."""

import json
import sys
from enum import Enum
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

console = Console()


class OutputFormat(str, Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


def output_json(data: dict[str, Any]) -> None:
    """Output data as JSON."""
    print(json.dumps(data, indent=2))


def output_text(data: str, lexer: str = "cisco") -> None:
    """Output text with syntax highlighting."""
    try:
        syntax = Syntax(
            data,
            lexer,
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )
        console.print(syntax)
    except Exception:
        # Fallback to plain text
        print(data)


def output_error(message: str, output_format: OutputFormat) -> None:
    """Output error message."""
    if output_format == OutputFormat.JSON:
        print(json.dumps({"status": "error", "error": message}))
    else:
        console.print(f"[red]Error: {message}[/red]")
