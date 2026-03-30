"""Integration tests for console command flow."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.commands.console import console_async, find_topology_file
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


@pytest.fixture
def topology_file(tmp_path: Path) -> Path:
    """Create a temporary topology file."""
    topo_file = tmp_path / "test_lab.topo"
    topo_file.write_text(SAMPLE_TOPOLOGY_XML)
    return topo_file


class TestConsoleFlow:
    """Integration tests for the full console flow."""

    @pytest.mark.asyncio
    async def test_full_flow_device_found_and_connect(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test full flow: find topology, find device, connect."""
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Router1", topology_file, "text")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Connected to Router1" in captured.out

    @pytest.mark.asyncio
    async def test_full_flow_switch_device(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test connecting to a switch device."""
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Switch1", topology_file, "text")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Connected to Switch1" in captured.out
        assert "2001" in captured.out


class TestAutoDiscoveryFlow:
    """Tests for topology auto-discovery in console flow."""

    @pytest.mark.asyncio
    async def test_auto_discovery_in_flow(
        self,
        tmp_path: Path,
        monkeypatch,
        capsys,
    ) -> None:
        """Test auto-discovery works within the console flow."""
        # Create topology file in temp directory
        topo_file = tmp_path / "lab.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        monkeypatch.chdir(tmp_path)
        
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Don't specify topology path - should auto-discover
            exit_code = await console_async("Router1", None, "text")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Connected to Router1" in captured.out

    @pytest.mark.asyncio
    async def test_auto_discovery_multiple_files_error(
        self,
        tmp_path: Path,
        monkeypatch,
        capsys,
    ) -> None:
        """Test error when multiple .topo files exist."""
        # Create multiple topology files
        (tmp_path / "lab1.topo").write_text(SAMPLE_TOPOLOGY_XML)
        (tmp_path / "lab2.topo").write_text(SAMPLE_TOPOLOGY_XML)
        monkeypatch.chdir(tmp_path)
        
        exit_code = await console_async("Router1", None, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Multiple .topo files found" in captured.err


class TestJsonOutputFlow:
    """Tests for JSON output in console flow."""

    @pytest.mark.asyncio
    async def test_json_output_success(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test JSON output on successful connection."""
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Router1", topology_file, "json")
        
        assert exit_code == 0
        captured = capsys.readouterr()
        
        output = json.loads(captured.out)
        assert output["status"] == "connected"
        assert output["device"] == "Router1"
        assert output["device_type"] == "Router"
        assert output["model"] == "AR2220_Router"
        assert "127.0.0.1:2000" == output["address"]

    @pytest.mark.asyncio
    async def test_json_output_device_not_found(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test JSON output when device not found."""
        exit_code = await console_async("NonExistentDevice", topology_file, "json")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "NonExistentDevice" in output["error"]

    @pytest.mark.asyncio
    async def test_json_output_connection_error(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test JSON output on connection error."""
        with patch("ensp_cli.commands.console.device_session") as mock_device_session:
            mock_device_session.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topology_file, "json")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "Connection refused" in output["error"]


class TestExitCodes:
    """Tests verifying exit codes."""

    @pytest.mark.asyncio
    async def test_exit_code_0_on_success(
        self,
        topology_file: Path,
    ) -> None:
        """Test exit code 0 on successful connection."""
        mock_client = MagicMock()
        
        with patch("ensp_cli.commands.console.device_session") as mock_device_session, \
             patch("ensp_cli.commands.console.InteractiveSession") as mock_session_class:
            
            mock_device_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = MagicMock()
            mock_session.start = AsyncMock()
            mock_session_class.return_value = mock_session
            
            exit_code = await console_async("Router1", topology_file, "text")
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_exit_code_0_on_keyboard_interrupt(
        self,
        topology_file: Path,
    ) -> None:
        """Test exit code 0 on keyboard interrupt."""
        with patch("ensp_cli.commands.console.device_session") as mock_device_session:
            mock_device_session.return_value.__aenter__ = AsyncMock(side_effect=KeyboardInterrupt())
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topology_file, "text")
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_exit_code_1_on_device_not_found(
        self,
        topology_file: Path,
    ) -> None:
        """Test exit code 1 when device not found."""
        exit_code = await console_async("UnknownDevice", topology_file, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_exit_code_1_on_connection_error(
        self,
        topology_file: Path,
    ) -> None:
        """Test exit code 1 on connection error."""
        with patch("ensp_cli.commands.console.device_session") as mock_device_session:
            mock_device_session.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("Failed to connect")
            )
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topology_file, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_exit_code_1_on_file_not_found(
        self,
    ) -> None:
        """Test exit code 1 when topology file not found."""
        exit_code = await console_async("Router1", Path("/nonexistent/path.topo"), "text")
        
        assert exit_code == 1


class TestErrorHandling:
    """Tests for error handling in console flow."""

    @pytest.mark.asyncio
    async def test_connection_error_shows_actionable_message(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test connection error shows actionable message."""
        with patch("ensp_cli.commands.console.device_session") as mock_device_session:
            mock_device_session.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("Failed to connect to device 'Router1' at port 2000")
            )
            mock_device_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await console_async("Router1", topology_file, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Failed to connect" in captured.err
        assert "Router1" in captured.err
        assert "2000" in captured.err

    @pytest.mark.asyncio
    async def test_device_not_found_shows_available_devices(
        self,
        topology_file: Path,
        capsys,
    ) -> None:
        """Test device not found shows list of available devices."""
        exit_code = await console_async("UnknownRouter", topology_file, "text")
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Available devices:" in captured.err
        assert "Router1" in captured.err
        assert "Switch1" in captured.err
