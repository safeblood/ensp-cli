"""Configuration importer service for eNSP CLI."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ensp_cli.models.device import Device


class ConfigImportError(Exception):
    """Exception raised for configuration import errors."""
    pass


class DangerousCommandError(ConfigImportError):
    """Exception raised when dangerous commands are detected."""
    pass


@dataclass
class ImportResult:
    """Result of a configuration import operation."""
    success: bool
    device: str
    commands_executed: int
    commands_failed: int
    failed_commands: list[dict] = field(default_factory=list)
    error_message: Optional[str] = None
    rollback_commands: list[str] = field(default_factory=list)


class ConfigImporter:
    """Service for importing configuration to eNSP devices."""

    # Dangerous commands that require explicit confirmation
    DANGEROUS_COMMANDS = [
        r"^reboot",
        r"^reset\s+saved-configuration",
        r"^delete",
        r"^format",
        r"^undo\s+.*password",
        r"^undo\s+.*aaa",
        r"^undo\s+.*ssh",
        r"^clear\s+configuration",
        r"^startup\s+saved-configuration",
        r"^restore\s+factory-default",
    ]

    # Section markers for configuration parsing
    SECTION_MARKERS = {
        "system": [
            r"^sysname\s+",
            r"^clock\s+",
            r"^header\s+",
            r"^command\s+",
            r"^hotkey\s+",
        ],
        "interface": [
            r"^interface\s+",
        ],
        "routing": [
            r"^ip\s+route-",
            r"^ospf\s+\d",
            r"^bgp\s+\d",
            r"^rip\s+\d",
            r"^isis\s+\d",
            r"^static-route",
        ],
        "acl": [
            r"^acl\s+(number|name)",
            r"^traffic-filter",
            r"^traffic-policy",
            r"^rule\s+",
        ],
        "user": [
            r"^aaa\s*",
            r"^local-user\s+",
            r"^user-group\s+",
            r"^authentication-",
            r"^authorization-",
            r"^accounting-",
        ],
        "vlan": [
            r"^vlan\s+(batch\s+)?\d",
            r"^vlan\s+if",
        ],
        "stp": [
            r"^stp\s+",
            r"^bpdu-",
        ],
    }

    def __init__(self):
        """Initialize the config importer."""
        self.dangerous_patterns = [re.compile(pattern, re.IGNORECASE) 
                                   for pattern in self.DANGEROUS_COMMANDS]
        self.section_patterns = {
            section: [re.compile(pattern, re.IGNORECASE) 
                     for pattern in patterns]
            for section, patterns in self.SECTION_MARKERS.items()
        }

    def parse_config_file(
        self, 
        file_path: Path,
        sections: Optional[list[str]] = None,
    ) -> list[str]:
        """Parse configuration file and extract commands.
        
        Args:
            file_path: Path to the configuration file.
            sections: Optional list of sections to extract.
                     If None, all commands are returned.
        
        Returns:
            List of configuration commands.
        
        Raises:
            ConfigImportError: If file cannot be read.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ConfigImportError(f"Failed to read config file: {e}")

        # Try to parse as JSON first (for metadata format)
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "commands" in data:
                commands = data["commands"]
            else:
                commands = data if isinstance(data, list) else [str(data)]
        except json.JSONDecodeError:
            # Parse as plain text
            commands = self._parse_text_config(content)

        # Filter by sections if specified
        if sections:
            commands = self._filter_by_sections(commands, sections)

        return commands

    def _parse_text_config(self, content: str) -> list[str]:
        """Parse plain text configuration into commands.
        
        Args:
            content: Raw configuration text.
        
        Returns:
            List of parsed commands.
        """
        commands = []
        current_multiline = []
        
        for line in content.splitlines():
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                continue
            
            # Handle multiline commands (ending with backslash)
            if stripped.endswith("\\"):
                current_multiline.append(stripped[:-1].rstrip())
                continue
            
            if current_multiline:
                current_multiline.append(stripped)
                command = " ".join(current_multiline)
                current_multiline = []
            else:
                command = stripped
            
            # Clean up the command
            command = command.strip()
            if command:
                commands.append(command)
        
        return commands

    def _filter_by_sections(
        self, 
        commands: list[str], 
        sections: list[str],
    ) -> list[str]:
        """Filter commands by specified sections.
        
        Args:
            commands: List of all commands.
            sections: Sections to include.
        
        Returns:
            Filtered commands.
        """
        filtered = []
        current_section = None
        in_interface_block = False
        interface_block_commands = []
        
        for command in commands:
            command_lower = command.lower().strip()
            
            # Check if this command starts a new section
            matched_section = None
            for section, patterns in self.section_patterns.items():
                if section in [s.lower() for s in sections]:
                    for pattern in patterns:
                        if pattern.match(command_lower):
                            matched_section = section
                            break
                if matched_section:
                    break
            
            # Handle interface blocks specially
            if "interface" in [s.lower() for s in sections]:
                if re.match(r"^interface\s+", command_lower):
                    in_interface_block = True
                    interface_block_commands = [command]
                    continue
                elif in_interface_block:
                    # Check if this is still in the interface block
                    if command_lower.startswith("interface "):
                        # New interface block, save previous
                        filtered.extend(interface_block_commands)
                        interface_block_commands = [command]
                    elif re.match(r"^\s+", command) or command_lower.startswith("undo "):
                        # Indented command or undo - part of interface block
                        interface_block_commands.append(command)
                    else:
                        # End of interface block
                        filtered.extend(interface_block_commands)
                        interface_block_commands = []
                        in_interface_block = False
                    continue
            
            if matched_section:
                current_section = matched_section
                filtered.append(command)
            elif current_section:
                # Check if we're still in the same section context
                if command.startswith(" ") or command.startswith("\t"):
                    filtered.append(command)
                else:
                    current_section = None
        
        # Add any remaining interface block commands
        if in_interface_block and interface_block_commands:
            filtered.extend(interface_block_commands)
        
        return filtered

    def validate_commands(
        self, 
        commands: list[str],
        whitelist: Optional[list[str]] = None,
    ) -> tuple[bool, list[str]]:
        """Validate commands and check for dangerous patterns.
        
        Args:
            commands: List of commands to validate.
            whitelist: Optional list of command patterns to whitelist.
        
        Returns:
            Tuple of (is_valid, list_of_warnings).
        """
        warnings = []
        whitelist_patterns = []
        
        if whitelist:
            whitelist_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in whitelist]
        
        for cmd in commands:
            cmd_stripped = cmd.strip().lower()
            
            # Check against dangerous patterns
            for pattern in self.dangerous_patterns:
                if pattern.search(cmd_stripped):
                    # Check if whitelisted
                    is_whitelisted = any(wp.search(cmd_stripped) 
                                        for wp in whitelist_patterns)
                    if not is_whitelisted:
                        warnings.append(f"Dangerous command detected: '{cmd}'")
        
        return len(warnings) == 0, warnings

    def substitute_variables(
        self, 
        commands: list[str], 
        variables: dict[str, str],
    ) -> list[str]:
        """Substitute template variables in commands.
        
        Template syntax:
        - {{variable_name}} - simple substitution
        - {{variable_name:default}} - substitution with default value
        
        Args:
            commands: List of commands with template variables.
            variables: Dictionary of variable values.
        
        Returns:
            Commands with variables substituted.
        """
        result = []
        
        for command in commands:
            processed = command
            
            # Find all variable placeholders
            pattern = r"\{\{(\w+)(?::([^}]+))?\}\}"
            matches = re.findall(pattern, command)
            
            for var_name, default_value in matches:
                placeholder = f"{{{{{var_name}{':' + default_value if default_value else ''}}}}}"
                
                if var_name in variables:
                    processed = processed.replace(placeholder, variables[var_name])
                elif default_value:
                    processed = processed.replace(placeholder, default_value)
                else:
                    raise ConfigImportError(
                        f"Variable '{var_name}' not provided and has no default"
                    )
            
            result.append(processed)
        
        return result

    def generate_rollback_commands(self, commands: list[str]) -> list[str]:
        """Generate rollback commands for a list of configuration commands.
        
        Args:
            commands: List of commands that were applied.
        
        Returns:
            List of rollback commands.
        """
        rollback = []
        
        for cmd in reversed(commands):
            cmd_stripped = cmd.strip()
            cmd_lower = cmd_stripped.lower()
            
            # Skip certain commands that don't have undo equivalents
            if any(cmd_lower.startswith(skip) for skip in ["display", "ping", "tracert"]):
                continue
            
            # Generate undo command
            if cmd_lower.startswith("undo "):
                # Remove "undo " prefix to get the original command
                rollback.append(cmd_stripped[5:].strip())
            else:
                # Add "undo " prefix
                rollback.append(f"undo {cmd_stripped}")
        
        return rollback

    async def import_to_device(
        self,
        device: Device,
        commands: list[str],
        dry_run: bool = False,
        timeout: float = 10.0,
        stop_on_error: bool = True,
        save_config: bool = True,
    ) -> ImportResult:
        """Import configuration to a device.
        
        Args:
            device: Device to import configuration to.
            commands: List of configuration commands.
            dry_run: If True, only preview without executing.
            timeout: Command timeout in seconds.
            stop_on_error: Stop execution on first error.
            save_config: Save configuration after import.
        
        Returns:
            ImportResult with execution details.
        """
        from ensp_cli.commands.exec import execute_batch
        
        if dry_run:
            return ImportResult(
                success=True,
                device=device.name,
                commands_executed=0,
                commands_failed=0,
                failed_commands=[],
                rollback_commands=commands,
            )

        # Prepare commands: enter system-view first
        exec_commands = ["system-view"]
        exec_commands.extend(commands)
        
        # Execute commands
        try:
            results = await execute_batch(
                device=device,
                commands=exec_commands,
                timeout=timeout,
                stop_on_error=stop_on_error,
            )
        except Exception as e:
            return ImportResult(
                success=False,
                device=device.name,
                commands_executed=0,
                commands_failed=len(commands),
                failed_commands=[{"command": "batch", "error": str(e)}],
                error_message=str(e),
                rollback_commands=[],
            )

        # Process results (skip system-view command)
        successful_commands = []
        failed_commands = []
        
        for i, result in enumerate(results):
            if i == 0 and result["command"] == "system-view":
                continue  # Skip system-view in reporting
            
            if result["success"]:
                successful_commands.append(result["command"])
            else:
                failed_commands.append({
                    "command": result["command"],
                    "error": result["error"],
                })
        
        # Save configuration if requested and all succeeded
        if save_config and len(failed_commands) == 0:
            try:
                save_results = await execute_batch(
                    device=device,
                    commands=["return", "save"],
                    timeout=timeout,
                    stop_on_error=True,
                )
                # Check if save was successful
                if not all(r["success"] for r in save_results):
                    failed_commands.append({
                        "command": "save",
                        "error": "Failed to save configuration",
                    })
            except Exception as e:
                failed_commands.append({
                    "command": "save",
                    "error": str(e),
                })

        # Generate rollback commands
        rollback = self.generate_rollback_commands(successful_commands)

        success = len(failed_commands) == 0
        
        return ImportResult(
            success=success,
            device=device.name,
            commands_executed=len(successful_commands),
            commands_failed=len(failed_commands),
            failed_commands=failed_commands,
            error_message=None if success else f"{len(failed_commands)} command(s) failed",
            rollback_commands=rollback,
        )
