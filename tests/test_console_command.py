"""Tests for the console command."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from ensp_cli.commands.console import (
    console_async,
    console_command,
    find_topology_file,
    get_device_or_exit,
    parse_topology,
)
from ensp_cli.models import Device, Topology


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


class TestFindTopologyFile:
    """Tests for find_topology_file function."""

    def test_explicit_path_exists(self, tmp_path: Path) -> None:
        """Test explicit path is returned if file exists."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text("<xml></xml>")
        
        result = find_topology_file(topo_file)
        
        assert result == topo_file

    def test_explicit_path_not_found(self, tmp_path: Path) -> None:
        """Test FileNotFoundError when explicit path doesn't exist."""
        topo_file = tmp_path / "nonexistent.topo"
        
        with pytest.raises(FileNotFoundError, match="Topology file not found"):
            find_topology_file(topo_file)

    def test_auto_discover_single_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test auto-discovery finds single .topo file."""
        topo_file = tmp_path / "mylab.topo"
        topo_file.write_text("<xml></xml>")
        
        monkeypatch.chdir(tmp_path)
        
        result = find_topology_file()
        
        assert result == topo_file

    def test_auto_discover_no_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test FileNotFoundError when no .topo files found."""
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(FileNotFoundError, match="No .topo file found"):
            find_topology_file()

    def test_auto_discover_multiple_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test ValueError when multiple .topo files found."""
        (tmp_path / "lab1.topo").write_text("<xml></xml>")
        (tmp_path / "lab2.topo").write_text("<xml></xml>")
        
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(ValueError, match="Multiple .topo files found"):
            find_topology_file()


class TestGetDeviceOrExit:
    """Tests for get_device_or_exit function."""

    def test_device_found(self) -> None:
        """Test device is returned when found."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        topology = Topology(
            name="test",
            devices=[device],
            connections=[],
        )
        
        result = get_device_or_exit(topology, "Router1")
        
        assert result == device

    def test_device_not_found(self, capsys) -> None:
        """Test exit with code 1 when device not found."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        topology = Topology(
            name="test",
            devices=[device],
            connections=[],
        )
        
        with pytest.raises(typer.Exit) as exc_info:
            get_device_or_exit(topology, "UnknownDevice")
        
        assert exc_info.value.exit_code == 1
        
        captured = capsys.readouterr()
        assert "Device 'UnknownDevice' not found" in captured.err
        assert "Available devices: Router1" in captured.err

    def test_device_not_found_shows_all_devices(self, capsys) -> None:
        """Test error message shows all available devices."""
        devices = [
            Device(name=f"Router{i}", device_type="Router", model="AR2220", console_port=2000 + i)
            for i in range(3)
        ]
        topology = Topology(
            name="test",
            devices=devices,
            connections=[],
        )
        
        with pytest.raises(typer.Exit) as exc_info:
            get_device_or_exit(topology, "Switch1")
        
        assert exc_info.value.exit_code == 1
        
        captured = capsys.readouterr()
        assert "Router0, Router1, Router2" in captured.err


class TestParseTopology:
    """Tests for parse_topology function."""

    def test_parse_valid_topology(self, tmp_path: Path) -> None:
        """Test parsing a valid topology file."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        topology = parse_topology(topo_file)
        
        assert topology.name == "test"
        assert len(topology.devices) == 2
        assert topology.devices[0].name == "Router1"
        assert topology.devices[1].name == "Switch1"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """Test FileNotFoundError for nonexistent file."""
        topo_file = tmp_path / "nonexistent.topo"
        
        with pytest.raises(FileNotFoundError):
            parse_topology(topo_file)


class TestConsoleAsync:
    """Tests for console_async function."""

    @pytest.mark.asyncio
    async def test_device_not_found_text_output(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Test error message in text mode when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await console_async("UnknownDevice", topo_file, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Device 'UnknownDevice' not found" in captured.err

    @pytest.mark.asyncio
    async def test_device_not_found_json_output(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Test error message in JSON mode when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await console_async("UnknownDevice", topo_file, "json")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        error_data = json.loads(captured.out)
        assert error_data["status"] == "error"
        assert "UnknownDevice" in error_data["error"]

    @pytest.mark.asyncio
    async def test_topology_file_not_found_text(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Test error message when topology file not found."""
        monkeypatch.chdir(tmp_path)
        
        exit_code = await console_async("Router1", None, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No .topo file found" in captured.err

    @pytest.mark.asyncio
    async def test_topology_file_not_found_json(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Test JSON error when topology file not found."""
        monkeypatch.chdir(tmp_path)
        
        exit_code = await console_async("Router1", None, "json")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        error_data = json.loads(captured.out)
        assert error_data["status"] == "error"

    @pytest.mark.asyncio
    async def test_keyboard_interrupt(self, tmp_path: Path, capsys) -> None:
        """Test graceful handling of KeyboardInterrupt."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        with patch("ensp_cli.commands.console.device_session") as mock:
            mock.return_value.__aenter__ = AsyncMock(side_effect=KeyboardInterrupt())
            mock.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topo_file, "text")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Disconnected" in captured.out

    @pytest.mark.asyncio
    async def test_connection_error_text(self, tmp_path: Path, capsys) -> None:
        """Test connection error in text mode."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        with patch("ensp_cli.commands.console.device_session") as mock:
            mock.return_value.__aenter__ = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topo_file, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Connection refused" in captured.err

    @pytest.mark.asyncio
    async def test_connection_error_json(self, tmp_path: Path, capsys) -> None:
        """Test connection error in JSON mode."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        with patch("ensp_cli.commands.console.device_session") as mock:
            mock.return_value.__aenter__ = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topo_file, "json")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        error_data = json.loads(captured.out)
        assert error_data["status"] == "error"
        assert "Connection refused" in error_data["error"]

    @pytest.mark.asyncio
    async def test_successful_connection_text_output(self, tmp_path: Path, capsys) -> None:
        """Test successful connection shows text output."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Router1", topo_file, "text")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Connected to Router1" in captured.out
        assert "127.0.0.1:2000" in captured.out
        assert "Press Ctrl+] or Ctrl+D to exit" in captured.out

    @pytest.mark.asyncio
    async def test_successful_connection_json_output(self, tmp_path: Path, capsys) -> None:
        """Test successful connection shows JSON output."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Router1", topo_file, "json")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        output_data = json.loads(captured.out)
        assert output_data["status"] == "connected"
        assert output_data["device"] == "Router1"
        assert output_data["device_type"] == "Router"
        assert output_data["model"] == "AR2220_Router"
        assert "127.0.0.1:2000" in output_data["address"]


class TestConsoleCommandIntegration:
    """Integration-style tests using Typer's test runner."""

    def test_console_command_help(self) -> None:
        """Test console command --help shows proper help."""
        from typer.testing import CliRunner
        from ensp_cli.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["console", "--help"])
        
        assert result.exit_code == 0
        assert "DEVICE_NAME" in result.output
        assert "--topology" in result.output
        assert "--output" in result.output

    def test_console_command_no_args_shows_help(self) -> None:
        """Test console command without args shows help."""
        from typer.testing import CliRunner
        from ensp_cli.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["console"])
        
        # Should show error about missing argument
        assert result.exit_code != 0
        assert "DEVICE_NAME" in result.output or "Usage:" in result.output
