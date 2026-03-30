# Stack Research

**Domain:** Python CLI tools for network device automation via Telnet
**Researched:** 2025-03-30
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Python 3.11+ provides significant performance improvements and is required by modern dependencies. Python 3.13 removed deprecated `telnetlib`, making `telnetlib3` essential. Windows-native development aligns with eNSP's Windows-only requirement. |
| Typer | 0.15.x | CLI Framework | Built on proven Click foundation with native Python type hint support. Auto-generates help, validation, and shell completion. Zero boilerplate for simple commands, scales to complex subcommand hierarchies. "FastAPI of CLIs" design philosophy. |
| telnetlib3 | 2.0.x | Telnet Protocol | Official successor to Python's deprecated `telnetlib` (removed in Python 3.13). Provides both async and blocking APIs. Includes backported `telnetlib` for migration compatibility. Supports RFC-compliant Telnet option negotiation essential for network device consoles. |
| Pydantic | 2.12.x | Data Modeling | Rust-core validation engine provides 10-100x performance over v1. Native JSON serialization via `model_dump_json()`. Type-safe data structures for device output parsing. Essential for producing structured LLM-consumable JSON output. |
| Rich | 14.x | Terminal UI | Industry standard for Python terminal formatting. Tables, progress bars, syntax highlighting, and console markup. Cross-platform Windows support (16 colors in classic terminal, Truecolor in Windows Terminal). Zero-config beautiful output. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| defusedxml | 0.7.x | XML Parsing | **Required** for parsing eNSP `.topo` files. Prevents XML entity expansion attacks vs standard library `xml.etree`. Safer drop-in replacement. |
| Netmiko | 4.5.x | Network Automation | Consider for production multi-vendor support. Abstracts SSH/Telnet with 50+ vendor drivers including Huawei VRP. May be overkill for eNSP's simple Telnet console access. |
| Textual | 2.0.x | Interactive TUI | Upgrade path if CLI evolves to full TUI. Widget-based reactive framework. Overkill for current command-output model but excellent for future interactive device explorer. |
| asyncio | stdlib | Concurrency | Use with `telnetlib3` async API for concurrent device operations. Essential for parallel configuration of multiple simulated devices. |
| pathlib | stdlib | Path Handling | Modern path manipulation (Python 3.4+). Replaces error-prone `os.path` string manipulation for `.topo` file discovery. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package Management | Modern Python package manager (Rust-based). 10-100x faster than pip. Handles resolution and virtual environments. Recommended by Typer/Pydantic ecosystem. |
| ruff | Linting/Formatting | Drop-in replacement for flake8 + black + isort. Rust-based, 10-100x faster. Native pyproject.toml support. |
| mypy | Type Checking | Static analysis for Python type hints. Catches runtime errors before execution. Essential for CLI argument validation logic. |
| pytest | Testing | Industry standard. Rich integration via `pytest-rich` plugin for beautiful test output. |
| pytest-asyncio | Async Testing | Required for testing `telnetlib3` async code patterns. |

## Installation

```bash
# Core dependencies (production)
pip install "typer>=0.15.0" "telnetlib3>=2.0.0" "pydantic>=2.12.0" "rich>=14.0.0" "defusedxml>=0.7.0"

# Alternative: With uv (recommended)
uv add typer telnetlib3 pydantic rich defusedxml

# Development dependencies
pip install "textual>=2.0.0" "netmiko>=4.5.0" --optional
pip install ruff mypy pytest pytest-asyncio --dev

# Windows-specific: Ensure Windows Terminal for Truecolor support
# Classic conhost.exe limited to 16 colors
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer | Click 8.1.x | When explicit decorator control needed or Typer's type inference is limiting. Click has larger ecosystem (38.7% vs 24.1% adoption). |
| Typer | argparse (stdlib) | For zero-dependency deployment or constrained embedded environments. Argparse is verbose for complex subcommands but requires no install. |
| telnetlib3 | Exscript | When scripting-focused workflow preferred. Exscript has closer API to original `telnetlib` but less async support. telnetlib3 is more actively maintained (2025). |
| telnetlib3 | telnetlib-313-and-up | Drop-in compatibility shim for legacy code. Not recommended for new projects—use telnetlib3's proper API. |
| Rich | Textual | When building full-screen interactive TUI vs command-output CLI. Textual is overkill for tables/progress bars alone. |
| Pydantic | msgspec | For ultra-high-performance JSON serialization (10x faster than Pydantic). msgspec is lighter but lacks Pydantic's validation ecosystem and FastAPI integration. |
| Netmiko | Paramiko + custom | When Netmiko's abstraction layer causes issues. Paramiko is lower-level SSH library; requires manual Telnet handling since it's SSH-focused. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `telnetlib` (stdlib) | **Removed in Python 3.13** (PEP 594). Deprecated since 3.11. No security updates. | telnetlib3 |
| `xml.etree.ElementTree` (stdlib) | Vulnerable to XML entity expansion (XXE) attacks when parsing untrusted `.topo` files. | defusedxml |
| `colorama` + manual ANSI | Rich handles Windows color compatibility natively. Manual ANSI codes break in classic Windows terminal. | Rich Console |
| `tabulate` / `prettytable` | Rich's Table class provides superior formatting, colors, and Windows compatibility. | Rich Table |
| `tqdm` | Rich's Progress provides better integration with other Rich renderables and Windows support. | Rich Progress |
| NAPALM | Overkill for eNSP simulation. Designed for production multi-vendor abstraction. Adds complexity without benefit for lab automation. | Direct telnetlib3 or Netmiko |

## Stack Patterns by Variant

**If targeting Python 3.10 only:**
- Use Python 3.10+ union syntax (`str | int` vs `Union[str, int]`)
- Note: telnetlib3 requires Python 3.9+; Pydantic v2 requires 3.9+

**If offline/air-gapped environment:**
- Pre-download wheels with `pip download`
- Use `telnetlib-313-and-up` shim if telnetlib3 unavailable (not recommended)

**If future TUI mode planned:**
- Structure CLI with Typer subcommands that can be wrapped by Textual widgets
- Separate "business logic" from "presentation layer" from day one

**If LLM integration deepens:**
- Pydantic models enable automatic JSON Schema generation for OpenAI function calling
- Structured output parsing via Pydantic validators

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| typer@0.15.x | click@8.x | Typer pins Click dependency; avoid direct Click usage to prevent version conflicts |
| pydantic@2.12.x | telnetlib3@2.x | No direct conflicts; both modern Python 3.9+ libraries |
| rich@14.x | typer@0.15.x | Typer depends on Rich for error formatting; versions compatible |
| telnetlib3@2.x | python@3.9-3.14 | Python 3.13+ removes stdlib telnetlib; telnetlib3 provides compatibility layer |
| netmiko@4.5.x | python@3.9-3.13 | Netmiko 4.5 adds Python 3.13 support and vendors telnetlib internally |

## Architecture Recommendations

### Project Structure
```
ensp-cli/
├── pyproject.toml          # Modern Python packaging
├── src/
│   └── ensp_cli/
│       ├── __init__.py
│       ├── cli.py           # Typer app definition
│       ├── models/          # Pydantic models
│       │   ├── topology.py  # .topo file parsing
│       │   └── device.py    # Device state/output
│       ├── console/         # Telnet connection handling
│       │   └── client.py    # telnetlib3 wrapper
│       └── output/          # Rich formatters
│           └── tables.py
└── tests/
```

### Key Design Patterns

1. **Pydantic for LLM Interface**
   ```python
   from pydantic import BaseModel
   
   class DeviceOutput(BaseModel):
       device_name: str
       command: str
       output: str
       timestamp: datetime
       
       def to_llm_json(self) -> str:
           return self.model_dump_json(indent=2)
   ```

2. **Typer for Command Structure**
   ```python
   import typer
   
   app = typer.Typer()
   
   @app.command()
   def exec(
       topology: Path = typer.Argument(..., help="Path to .topo file"),
       command: str = typer.Option(..., "-c", "--command", help="Command to execute"),
       json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
   ):
       pass
   ```

3. **telnetlib3 for Console Access**
   ```python
   import telnetlib3
   
   async def send_command(host: str, port: int, cmd: str) -> str:
       reader, writer = await telnetlib3.open_connection(host, port)
       writer.write(cmd + "\n")
       output = await reader.readuntil(b"#")  # Prompt detection
       return output.decode()
   ```

## Sources

- [Typer Official Docs](https://typer.tiangolo.com) — Version 0.15.x verification, dependency info (Click + Rich)
- [Rich PyPI](https://pypi.org/project/rich/) — Version 14.3.3, Windows compatibility notes
- [telnetlib3 GitHub](https://github.com/jquast/telnetlib3) — Python 3.9+ requirement, RFC compliance, blocking/async APIs
- [Python telnetlib deprecation](https://docs.python.org/3/library/telnetlib.html) — Removed in Python 3.13 per PEP 594
- [Pydantic Official Docs](https://docs.pydantic.dev) — Version 2.12.5, Rust core performance, V2 migration guide
- [Netmiko GitHub](https://github.com/ktbyers/netmiko) — Version 4.5.0, Huawei VRP support, Python 3.13 compatibility
- [defusedxml PyPI](https://pypi.org/project/defusedxml/) — XML security best practices
- [CLI Framework Comparison 2025](https://dasroot.net/posts/2025/12/building-cli-tools-python-click-typer-argparse/) — Click vs Typer vs argparse benchmarks

---
*Stack research for: ensp-cli — Huawei eNSP network simulation automation*
*Researched: 2025-03-30*
