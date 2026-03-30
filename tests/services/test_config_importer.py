"""Tests for config importer service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.models.device import Device
from ensp_cli.services.config_importer import (
    ConfigImporter,
    ConfigImportError,
    ImportResult,
)


class TestConfigImporter:
    """Test cases for ConfigImporter."""

    @pytest.fixture
    def importer(self):
        """Create a ConfigImporter instance."""
        return ConfigImporter()

    @pytest.fixture
    def sample_device(self):
        """Create a sample device."""
        return Device(
            name="R1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""sysname Router1
#
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
#
return""")
            path = f.name
        yield Path(path)
        Path(path).unlink()

    def test_parse_config_file_plain_text(self, importer, temp_config_file):
        """Test parsing a plain text config file."""
        commands = importer.parse_config_file(temp_config_file)
        
        assert len(commands) == 4  # including 'return'
        assert "sysname Router1" in commands
        assert any("interface GigabitEthernet0/0/1" in cmd for cmd in commands)
        assert any("ip address" in cmd for cmd in commands)

    def test_parse_config_file_json_format(self, importer):
        """Test parsing a JSON config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "metadata": {"version": "1.0"},
                "commands": [
                    "sysname Router1",
                    "interface GE0/0/1",
                    "ip address 192.168.1.1 24"
                ]
            }, f)
            path = f.name
        
        try:
            commands = importer.parse_config_file(Path(path))
            assert len(commands) == 3
            assert "sysname Router1" in commands
        finally:
            Path(path).unlink()

    def test_parse_config_file_json_list(self, importer):
        """Test parsing a JSON list config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(["command1", "command2", "command3"], f)
            path = f.name
        
        try:
            commands = importer.parse_config_file(Path(path))
            assert len(commands) == 3
            assert commands == ["command1", "command2", "command3"]
        finally:
            Path(path).unlink()

    def test_parse_config_file_not_found(self, importer):
        """Test parsing a non-existent config file."""
        with pytest.raises(ConfigImportError) as exc_info:
            importer.parse_config_file(Path("/nonexistent/file.cfg"))
        
        assert "Failed to read config file" in str(exc_info.value)

    def test_parse_config_file_with_sections(self, importer):
        """Test parsing config file with section filtering."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""sysname Router1
#
interface GigabitEthernet0/0/1
 ip address 192.168.1.1 255.255.255.0
#
ospf 1
 area 0
#
return""")
            path = f.name
        
        try:
            # Test interface section
            commands = importer.parse_config_file(Path(path), sections=["interface"])
            assert len(commands) >= 1
            assert any("interface" in cmd for cmd in commands)
            assert not any("sysname" in cmd for cmd in commands)
            
            # Test system section
            commands = importer.parse_config_file(Path(path), sections=["system"])
            assert any("sysname" in cmd for cmd in commands)
        finally:
            Path(path).unlink()

    def test_validate_commands_safe(self, importer):
        """Test validating safe commands."""
        commands = [
            "sysname Router1",
            "interface GigabitEthernet0/0/1",
            "ip address 192.168.1.1 255.255.255.0",
        ]
        
        is_valid, warnings = importer.validate_commands(commands)
        
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_commands_dangerous(self, importer):
        """Test validating dangerous commands."""
        commands = [
            "sysname Router1",
            "reboot",
            "delete flash:/test.txt",
        ]
        
        is_valid, warnings = importer.validate_commands(commands)
        
        assert is_valid is False
        assert len(warnings) == 2
        assert any("reboot" in w for w in warnings)
        assert any("delete" in w for w in warnings)

    def test_validate_commands_with_whitelist(self, importer):
        """Test validating commands with whitelist."""
        commands = [
            "reboot",
            "delete flash:/test.txt",
        ]
        
        is_valid, warnings = importer.validate_commands(
            commands, 
            whitelist=[r"^reboot"]
        )
        
        # reboot is whitelisted, delete is not
        assert is_valid is False
        assert len(warnings) == 1
        assert "delete" in warnings[0]

    def test_substitute_variables(self, importer):
        """Test variable substitution."""
        commands = [
            "sysname {{hostname}}",
            "interface {{interface_name}}",
            "ip address {{ip}} {{mask}}",
        ]
        
        variables = {
            "hostname": "Router1",
            "interface_name": "GE0/0/1",
            "ip": "192.168.1.1",
            "mask": "255.255.255.0",
        }
        
        result = importer.substitute_variables(commands, variables)
        
        assert result[0] == "sysname Router1"
        assert result[1] == "interface GE0/0/1"
        assert result[2] == "ip address 192.168.1.1 255.255.255.0"

    def test_substitute_variables_with_defaults(self, importer):
        """Test variable substitution with default values."""
        commands = [
            "sysname {{hostname:Router}}",
            "ip address {{ip}} {{mask:255.255.255.0}}",
        ]
        
        variables = {"ip": "192.168.1.1"}  # hostname and mask use defaults
        
        result = importer.substitute_variables(commands, variables)
        
        assert result[0] == "sysname Router"
        assert result[1] == "ip address 192.168.1.1 255.255.255.0"

    def test_substitute_variables_missing(self, importer):
        """Test variable substitution with missing variables."""
        commands = ["sysname {{hostname}}"]
        
        with pytest.raises(ConfigImportError) as exc_info:
            importer.substitute_variables(commands, {})
        
        assert "Variable 'hostname' not provided" in str(exc_info.value)

    def test_generate_rollback_commands(self, importer):
        """Test generating rollback commands."""
        commands = [
            "sysname Router1",
            "interface GE0/0/1",
            "ip address 192.168.1.1 255.255.255.0",
        ]
        
        rollback = importer.generate_rollback_commands(commands)
        
        assert len(rollback) == 3
        assert "undo ip address 192.168.1.1 255.255.255.0" in rollback
        assert "undo interface GE0/0/1" in rollback
        assert "undo sysname Router1" in rollback

    def test_generate_rollback_commands_with_undo(self, importer):
        """Test generating rollback commands for commands that already have undo."""
        commands = [
            "undo ospf 1",
            "undo interface GE0/0/1",
        ]
        
        rollback = importer.generate_rollback_commands(commands)
        
        # undo commands should become normal commands
        assert "ospf 1" in rollback
        assert "interface GE0/0/1" in rollback

    def test_generate_rollback_commands_skip_display(self, importer):
        """Test that display commands are skipped in rollback."""
        commands = [
            "display version",
            "sysname Router1",
            "display ip interface brief",
        ]
        
        rollback = importer.generate_rollback_commands(commands)
        
        # display commands should not appear in rollback
        assert not any("display" in cmd for cmd in rollback)
        assert "undo sysname Router1" in rollback

    @pytest.mark.asyncio
    async def test_import_to_device_dry_run(self, importer, sample_device):
        """Test dry run mode."""
        commands = ["sysname Router1", "interface GE0/0/1"]
        
        result = await importer.import_to_device(
            device=sample_device,
            commands=commands,
            dry_run=True,
        )
        
        assert result.success is True
        assert result.device == "R1"
        assert result.commands_executed == 0
        assert result.rollback_commands == commands

    @pytest.mark.asyncio
    async def test_import_to_device_with_mock(self, importer, sample_device):
        """Test import with mocked execute_batch."""
        commands = ["sysname Router1"]
        
        mock_results = [
            {"command": "system-view", "output": "", "success": True, "error": None},
            {"command": "sysname Router1", "output": "", "success": True, "error": None},
        ]
        
        with patch('ensp_cli.commands.exec.execute_batch', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_results
            
            result = await importer.import_to_device(
                device=sample_device,
                commands=commands,
                dry_run=False,
            )
            
            assert result.success is True
            assert result.commands_executed == 1
            assert result.device == "R1"

    @pytest.mark.asyncio
    async def test_import_to_device_with_errors(self, importer, sample_device):
        """Test import with command failures."""
        commands = ["sysname Router1", "invalid command"]
        
        mock_results = [
            {"command": "system-view", "output": "", "success": True, "error": None},
            {"command": "sysname Router1", "output": "", "success": True, "error": None},
            {"command": "invalid command", "output": "", "success": False, "error": "Invalid command"},
        ]
        
        with patch('ensp_cli.commands.exec.execute_batch', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_results
            
            result = await importer.import_to_device(
                device=sample_device,
                commands=commands,
                dry_run=False,
            )
            
            assert result.success is False
            assert result.commands_failed == 1
            assert len(result.failed_commands) == 1
            assert result.failed_commands[0]["command"] == "invalid command"

    def test_parse_text_config_multiline(self, importer):
        """Test parsing multiline commands."""
        content = """sysname Router1
command with \\
 continuation
interface GE0/0/1"""
        
        commands = importer._parse_text_config(content)
        
        assert "sysname Router1" in commands
        assert "command with continuation" in commands
        assert "interface GE0/0/1" in commands

    def test_parse_text_config_skip_comments(self, importer):
        """Test that comments are skipped."""
        content = """# This is a comment
! This is also a comment
sysname Router1
  
! Another comment
interface GE0/0/1"""
        
        commands = importer._parse_text_config(content)
        
        assert len(commands) == 2
        assert "sysname Router1" in commands
        assert "interface GE0/0/1" in commands
        assert not any(cmd.startswith("#") for cmd in commands)
        assert not any(cmd.startswith("!") for cmd in commands)


class TestImportResult:
    """Test cases for ImportResult dataclass."""

    def test_import_result_creation(self):
        """Test creating ImportResult."""
        result = ImportResult(
            success=True,
            device="R1",
            commands_executed=5,
            commands_failed=0,
        )
        
        assert result.success is True
        assert result.device == "R1"
        assert result.commands_executed == 5
        assert result.commands_failed == 0
        assert result.failed_commands == []
        assert result.rollback_commands == []

    def test_import_result_with_failures(self):
        """Test ImportResult with failures."""
        result = ImportResult(
            success=False,
            device="R1",
            commands_executed=3,
            commands_failed=2,
            failed_commands=[
                {"command": "cmd1", "error": "Error 1"},
                {"command": "cmd2", "error": "Error 2"},
            ],
            error_message="2 command(s) failed",
        )
        
        assert result.success is False
        assert result.error_message == "2 command(s) failed"
        assert len(result.failed_commands) == 2


class TestConfigImportError:
    """Test cases for ConfigImportError."""

    def test_error_creation(self):
        """Test creating ConfigImportError."""
        error = ConfigImportError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Test that ConfigImportError is an Exception."""
        error = ConfigImportError("Test")
        assert isinstance(error, Exception)
