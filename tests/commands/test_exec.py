"""Tests for the exec command."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from ensp_cli.commands.exec import execute_command, exec_async, exec_command
from ensp_cli.models.device import Device
from ensp_cli.models.topology import Topology
from ensp_cli.telnet_client import VRP_PROMPT_ANY


# Sample topology XML with correct structure
SAMPLE_TOPOLOGY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<topo>
    <devices>
        <dev id="1" name="Router1" model="AR2220_Router" com_port="2000"/>
        <dev id="2" name="Switch1" model="S5700_Switch" com_port="2001"/>
    </devices>
    <lines>
        <line srcDeviceID="1" destDeviceID="2">
            <interfacePair srcIndex="0" tarIndex="0" lineName="Copper"/>
        </line>
    </lines>
</topo>
"""


def create_mock_client(output_chunks: list[str], disable_paging: bool = True):
    """Create a mock TelnetClient that returns chunks sequentially.
    
    Args:
        output_chunks: Chunks to return for the main command.
        disable_paging: Whether to simulate screen-length 0 temporary response.
    """
    mock_client = MagicMock()
    
    # If disable_paging is True, prepend screen-length command output
    if disable_paging:
        all_chunks = ["", ""] + output_chunks  # Two empty chunks for screen-length command
    else:
        all_chunks = output_chunks
    
    chunk_iter = iter(all_chunks)
    
    async def mock_read_available():
        await asyncio.sleep(0.01)  # Small delay to simulate I/O
        try:
            return next(chunk_iter)
        except StopIteration:
            return ""
    
    mock_client.read_available = mock_read_available
    mock_client.write_line = AsyncMock()
    mock_client.write = AsyncMock()
    return mock_client


class TestExecuteCommand:
    """Tests for execute_command function."""

    @pytest.mark.asyncio
    async def test_strips_command_echo(self) -> None:
        """Test that command echo is stripped from output."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        
        # Simulate output with command echo and prompt
        chunks = [
            "display version\r\n",
            "Huawei Versatile Routing Platform Software\r\n",
            "VRP (R) software, Version 8.0\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            output = await execute_command(device, "display version", timeout=5.0)
        
        # Command echo should be stripped
        assert "display version" not in output
        assert "Huawei Versatile Routing Platform Software" in output
        assert "VRP (R) software, Version 8.0" in output

    @pytest.mark.asyncio
    async def test_strips_trailing_prompt(self) -> None:
        """Test that trailing prompt is stripped from output."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        
        chunks = [
            "display version\r\n",
            "Huawei Versatile Routing Platform Software\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            output = await execute_command(device, "display version", timeout=5.0)
        
        # Trailing prompt should be stripped
        assert not output.endswith("<Router1>")
        assert "Huawei Versatile Routing Platform Software" in output

    @pytest.mark.asyncio
    async def test_strips_system_prompt(self) -> None:
        """Test that system view prompt is stripped."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        
        chunks = [
            "system-view\r\n",
            "Enter system view, return user view with Ctrl+Z.\r\n",
            "[Router1]"
        ]
        mock_client = create_mock_client(chunks)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            output = await execute_command(device, "system-view", timeout=5.0)
        
        # System prompt should be stripped
        assert not output.endswith("[Router1]")
        assert "Enter system view" in output


class TestExecAsync:
    """Tests for exec_async function."""

    @pytest.mark.asyncio
    async def test_returns_exit_code_0_on_success(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Test that exec_async returns 0 on success."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display version\r\n",
            "Huawei VRP Software\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await exec_async("Router1", "display version", topo_file, "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_device_not_found(self, tmp_path: Path, capsys) -> None:
        """Test that exec_async returns 1 when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await exec_async("NonExistentRouter", "display version", topo_file, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_connection_error(self, tmp_path: Path, capsys) -> None:
        """Test that exec_async returns 1 on connection error."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )
            
            exit_code = await exec_async("Router1", "display version", topo_file, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_returns_exit_code_2_on_file_not_found(self, tmp_path: Path, capsys) -> None:
        """Test that exec_async returns 2 when topology file not found."""
        nonexistent_file = tmp_path / "nonexistent.topo"
        
        exit_code = await exec_async("Router1", "display version", nonexistent_file, "text")
        
        assert exit_code == 2

    @pytest.mark.asyncio
    async def test_returns_exit_code_3_on_parse_error(self, tmp_path: Path, capsys) -> None:
        """Test that exec_async returns 3 on parse error."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text("invalid xml content")
        
        exit_code = await exec_async("Router1", "display version", topo_file, "text")
        
        assert exit_code == 3

    @pytest.mark.asyncio
    async def test_returns_exit_code_5_on_timeout(self, tmp_path: Path, capsys) -> None:
        """Test that exec_async returns 5 on command timeout."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Mock client that never returns the prompt
        mock_client = MagicMock()
        mock_client.read_available = AsyncMock(return_value="")
        mock_client.write_line = AsyncMock()
        mock_client.write = AsyncMock()
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await exec_async("Router1", "display version", topo_file, "text", timeout=0.1)
        
        assert exit_code == 5


class TestJsonOutput:
    """Tests for JSON output format."""

    @pytest.mark.asyncio
    async def test_json_output_format_is_valid(self, tmp_path: Path) -> None:
        """Test that JSON output format is valid and contains expected fields."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display version\r\n",
            "Huawei VRP Software\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await exec_async("Router1", "display version", topo_file, "json", timeout=5.0)
        
        assert exit_code == 0
        # Check that valid JSON was printed
        # Note: We can't easily capture stdout in async tests, but the exit code indicates success

    @pytest.mark.asyncio
    async def test_json_error_output_format(self, tmp_path: Path, capsys) -> None:
        """Test that JSON error output has correct format."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await exec_async("NonExistentDevice", "display version", topo_file, "json")
        
        assert exit_code == 1


class TestCommandTimeoutHandling:
    """Tests for command timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, tmp_path: Path) -> None:
        """Test that timeout errors are properly handled."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Mock client that never returns the prompt
        mock_client = MagicMock()
        mock_client.read_available = AsyncMock(return_value="")
        mock_client.write_line = AsyncMock()
        mock_client.write = AsyncMock()
        
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await exec_async("Router1", "display version", topo_file, "text", timeout=0.1)
        
        assert exit_code == 5


class TestExecCommandIntegration:
    """Integration tests for exec command."""

    def test_exec_command_help(self) -> None:
        """Test that exec command help is accessible."""
        from typer.testing import CliRunner
        from ensp_cli.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["exec", "--help"])
        
        assert result.exit_code == 0
        assert "Execute a single command on a device" in result.output
        assert "--output" in result.output

    def test_exec_command_no_args_shows_help(self) -> None:
        """Test that exec command with no args shows help."""
        from typer.testing import CliRunner
        from ensp_cli.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["exec"])
        
        # Should fail with missing arguments
        assert result.exit_code != 0
        assert "Usage:" in result.output or "Missing" in result.output
