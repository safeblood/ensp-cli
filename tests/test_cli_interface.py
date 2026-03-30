"""Integration tests for CLI interface."""

import pytest
from typer.testing import CliRunner

from ensp_cli import __version__
from ensp_cli.cli.main import app

runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help interface."""

    def test_main_help_returns_exit_code_0(self):
        """Test --help returns exit code 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "CLI tool for managing eNSP topology files" in result.output

    def test_main_help_shows_exit_codes(self):
        """Test main help shows exit codes in epilog."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Exit Codes:" in result.output
        assert "0 - Success" in result.output
        assert "1 - General error" in result.output
        assert "2 - File not found" in result.output

    def test_list_help_shows_exit_codes(self):
        """Test list --help shows exit codes."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "Exit codes:" in result.output
        assert "0: Success" in result.output
        assert "2: File not found" in result.output
        assert "3: Parse error" in result.output
        assert "4: Permission denied" in result.output

    def test_console_help_shows_exit_codes(self):
        """Test console --help shows exit codes."""
        result = runner.invoke(app, ["console", "--help"])
        assert result.exit_code == 0
        assert "Exit codes:" in result.output
        assert "0: Success or user disconnect" in result.output
        assert "1: Connection error or device not found" in result.output
        assert "2: Topology file not found" in result.output

    def test_exec_help_shows_exit_codes(self):
        """Test exec --help shows exit codes."""
        result = runner.invoke(app, ["exec", "--help"])
        assert result.exit_code == 0
        assert "Exit codes:" in result.output
        assert "0: Success" in result.output
        assert "1: General error or device not found" in result.output
        assert "2: Topology file not found" in result.output
        assert "3: Parse error" in result.output
        assert "5: Command timeout" in result.output


class TestCLIVersion:
    """Tests for CLI version flag."""

    def test_version_returns_exit_code_0(self):
        """Test --version returns exit code 0."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_version_prints_version(self):
        """Test --version prints version string."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"ensp-cli version {__version__}" in result.output


class TestExitCodes:
    """Tests for command exit codes on errors."""

    def test_list_nonexistent_file_returns_2(self, tmp_path):
        """Test list with nonexistent file returns exit code 2."""
        nonexistent = tmp_path / "nonexistent.topo"
        result = runner.invoke(app, ["list", str(nonexistent)])
        # Typer validates the file exists before calling our code
        # So this returns error code 2 (usage error)
        assert result.exit_code == 2

    def test_list_invalid_file_returns_2(self, tmp_path):
        """Test list with non-existent path returns error."""
        result = runner.invoke(app, ["list", "/path/that/does/not/exist.topo"])
        assert result.exit_code == 2

    def test_console_nonexistent_device_returns_1(self, tmp_path):
        """Test console with nonexistent device returns exit code 1.
        
        Note: This requires a valid topology file with no matching device.
        """
        # Create a minimal valid topology file
        topo_content = """<?xml version="1.0" encoding="UTF-8"?>
<Topology>
    <DeviceCollection>
        <Device>
            <Name>Router1</Name>
            <Type>Router</Type>
            <Model>AR2220</Model>
            <ConsolePort>2000</ConsolePort>
        </Device>
    </DeviceCollection>
    <ConnectionCollection>
    </ConnectionCollection>
</Topology>
"""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(topo_content)
        
        result = runner.invoke(app, ["console", "NonExistentDevice", "--topology", str(topo_file)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_exec_nonexistent_device_returns_1(self, tmp_path):
        """Test exec with nonexistent device returns exit code 1."""
        # Create a minimal valid topology file
        topo_content = """<?xml version="1.0" encoding="UTF-8"?>
<Topology>
    <DeviceCollection>
        <Device>
            <Name>Router1</Name>
            <Type>Router</Type>
            <Model>AR2220</Model>
            <ConsolePort>2000</ConsolePort>
        </Device>
    </DeviceCollection>
    <ConnectionCollection>
    </ConnectionCollection>
</Topology>
"""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(topo_content)
        
        result = runner.invoke(app, ["exec", "NonExistentDevice", "display version", "--topology", str(topo_file)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output
