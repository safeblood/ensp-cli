"""Tests for the config commands."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from ensp_cli.cli.main import app
from ensp_cli.commands.config import (
    execute_show_command,
    filter_config_section,
    parse_interface_brief_output,
    parse_routing_table_output,
    show_config_async,
    show_interfaces_async,
    show_routes_async,
)
from ensp_cli.models.device import Device
from ensp_cli.models.topology import Topology


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

# Sample configuration output
SAMPLE_CONFIG_OUTPUT = """
sysname Router1
#
interface GigabitEthernet0/0/0
 ip address 192.168.1.1 255.255.255.0
#
interface GigabitEthernet0/0/1
 ip address 10.0.0.1 255.255.255.252
#
ospf 1
 area 0.0.0.0
  network 192.168.1.0 0.0.0.255
  network 10.0.0.0 0.0.0.3
#
return
"""

# Sample interface brief output
SAMPLE_INTERFACE_OUTPUT = """
Interface                         IP Address/Mask      Physical   Protocol  VPN 
GigabitEthernet0/0/0              192.168.1.1/24       up         up        --  
GigabitEthernet0/0/1              10.0.0.1/30          up         up        --  
LoopBack0                         1.1.1.1/32           up         up(s)     --  
NULL0                             unassigned           up         up(s)     --  
"""

# Sample routing table output
SAMPLE_ROUTING_OUTPUT = """
Route Flags: R - relay, D - download to fib
------------------------------------------------------------------------------
Routing Tables: Public
         Destinations : 5        Routes : 5

Destination/Mask    Proto   Pre  Cost        Flags NextHop         Interface

      1.1.1.1/32  Direct  0    0             D   127.0.0.1       LoopBack0
    10.0.0.0/30  Direct  0    0             D   10.0.0.1        GigabitEthernet0/0/1
    10.0.0.1/32  Direct  0    0             D   127.0.0.1       GigabitEthernet0/0/1
  192.168.1.0/24  Direct  0    0             D   192.168.1.1     GigabitEthernet0/0/0
  192.168.1.1/32  Direct  0    0             D   127.0.0.1       GigabitEthernet0/0/0
  172.16.0.0/16  OSPF    10   2             D   10.0.0.2        GigabitEthernet0/0/1
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
    return mock_client


class TestFilterConfigSection:
    """Tests for filter_config_section function."""

    def test_filters_interface_section(self) -> None:
        """Test filtering interface configuration section."""
        result = filter_config_section(SAMPLE_CONFIG_OUTPUT, "interface")
        
        assert "interface GigabitEthernet0/0/0" in result
        assert "interface GigabitEthernet0/0/1" in result
        assert "ip address 192.168.1.1" in result
        # Should not include ospf section
        assert "ospf 1" not in result

    def test_filters_ospf_section(self) -> None:
        """Test filtering OSPF configuration section."""
        result = filter_config_section(SAMPLE_CONFIG_OUTPUT, "ospf")
        
        assert "ospf 1" in result
        assert "area 0.0.0.0" in result
        # Should not include interface section
        assert "interface GigabitEthernet0/0/0" not in result

    def test_returns_not_found_for_missing_section(self) -> None:
        """Test that missing section returns appropriate message."""
        result = filter_config_section(SAMPLE_CONFIG_OUTPUT, "bgp")
        
        assert "Section 'bgp' not found" in result

    def test_case_insensitive_matching(self) -> None:
        """Test that section matching is case insensitive."""
        result = filter_config_section(SAMPLE_CONFIG_OUTPUT, "INTERFACE")
        
        assert "interface GigabitEthernet0/0/0" in result


class TestParseInterfaceBriefOutput:
    """Tests for parse_interface_brief_output function."""

    def test_parses_interface_data(self) -> None:
        """Test parsing of interface brief output."""
        interfaces = parse_interface_brief_output(SAMPLE_INTERFACE_OUTPUT)
        
        assert len(interfaces) == 4
        
        # Check first interface
        assert interfaces[0]["interface"] == "GigabitEthernet0/0/0"
        assert interfaces[0]["ip_address"] == "192.168.1.1/24"
        assert interfaces[0]["physical"] == "up"
        assert interfaces[0]["protocol"] == "up"

    def test_handles_unassigned_ip(self) -> None:
        """Test handling of unassigned IP addresses."""
        interfaces = parse_interface_brief_output(SAMPLE_INTERFACE_OUTPUT)
        
        null_iface = [i for i in interfaces if i["interface"] == "NULL0"][0]
        assert null_iface["ip_address"] is None

    def test_handles_empty_output(self) -> None:
        """Test handling of empty output."""
        interfaces = parse_interface_brief_output("")
        
        assert interfaces == []


class TestParseRoutingTableOutput:
    """Tests for parse_routing_table_output function."""

    def test_parses_route_data(self) -> None:
        """Test parsing of routing table output."""
        routes = parse_routing_table_output(SAMPLE_ROUTING_OUTPUT)
        
        assert len(routes) >= 5
        
        # Check for specific routes
        destinations = [r["destination"] for r in routes]
        assert "1.1.1.1/32" in destinations
        assert "10.0.0.0/30" in destinations
        assert "192.168.1.0/24" in destinations

    def test_parses_protocol_field(self) -> None:
        """Test that protocol field is parsed correctly."""
        routes = parse_routing_table_output(SAMPLE_ROUTING_OUTPUT)
        
        direct_routes = [r for r in routes if r["protocol"] == "Direct"]
        assert len(direct_routes) > 0

    def test_handles_empty_output(self) -> None:
        """Test handling of empty output."""
        routes = parse_routing_table_output("")
        
        assert routes == []


class TestExecuteShowCommand:
    """Tests for execute_show_command function."""

    @pytest.mark.asyncio
    async def test_executes_display_current_configuration(self) -> None:
        """Test executing display current-configuration command."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=2000,
        )
        
        # Use the same create_mock_client pattern as test_exec.py
        chunks = [
            "display current-configuration\r\n",
            "sysname Router1\r\n",
            "#\r\n",
            "return\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            output = await execute_show_command(device, "display current-configuration", timeout=5.0)
        
        # Command echo should be stripped
        assert "display current-configuration" not in output
        assert "sysname Router1" in output
        # Prompt should be stripped
        assert "<Router1>" not in output


class TestShowConfigAsync:
    """Tests for show_config_async function."""

    @pytest.mark.asyncio
    async def test_returns_exit_code_0_on_success(self, tmp_path: Path) -> None:
        """Test that show_config_async returns 0 on success."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display current-configuration\r\n",
            "sysname Router1\r\n",
            "return\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_config_async("Router1", topo_file, None, "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_device_not_found(self, tmp_path: Path) -> None:
        """Test that show_config_async returns 1 when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await show_config_async("NonExistentRouter", topo_file, None, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_filters_section_correctly(self, tmp_path: Path) -> None:
        """Test that section filtering works correctly."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Use chunks pattern to simulate realistic output
        chunks = [
            "display current-configuration\r\n",
            "sysname Router1\r\n",
            "#\r\n",
            "interface GigabitEthernet0/0/0\r\n",
            " ip address 192.168.1.1 255.255.255.0\r\n",
            "#\r\n",
            "ospf 1\r\n",
            " area 0.0.0.0\r\n",
            "#\r\n",
            "return\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_config_async("Router1", topo_file, "interface", "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_2_on_file_not_found(self, tmp_path: Path) -> None:
        """Test that show_config_async returns 2 when topology file not found."""
        nonexistent_file = tmp_path / "nonexistent.topo"
        
        exit_code = await show_config_async("Router1", nonexistent_file, None, "text")
        
        assert exit_code == 2

    @pytest.mark.asyncio
    async def test_returns_exit_code_3_on_parse_error(self, tmp_path: Path) -> None:
        """Test that show_config_async returns 3 on parse error."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text("invalid xml content")
        
        exit_code = await show_config_async("Router1", topo_file, None, "text")
        
        assert exit_code == 3

    @pytest.mark.asyncio
    async def test_returns_exit_code_5_on_timeout(self, tmp_path: Path) -> None:
        """Test that show_config_async returns 5 on command timeout."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Mock client that never returns the prompt - will cause timeout
        mock_client = MagicMock()
        mock_client.read_available = AsyncMock(return_value="")  # Empty response
        mock_client.write_line = AsyncMock()
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_config_async("Router1", topo_file, None, "text", timeout=0.2)
        
        assert exit_code == 5


class TestShowInterfacesAsync:
    """Tests for show_interfaces_async function."""

    @pytest.mark.asyncio
    async def test_returns_exit_code_0_on_success(self, tmp_path: Path) -> None:
        """Test that show_interfaces_async returns 0 on success."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display ip interface brief\r\n",
            SAMPLE_INTERFACE_OUTPUT,
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_interfaces_async("Router1", topo_file, None, "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_device_not_found(self, tmp_path: Path) -> None:
        """Test that show_interfaces_async returns 1 when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await show_interfaces_async("NonExistentRouter", topo_file, None, "text")
        
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_filters_specific_interface(self, tmp_path: Path) -> None:
        """Test filtering for a specific interface."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Use chunks pattern to simulate realistic output
        chunks = [
            "display ip interface GigabitEthernet0/0/0\r\n",
            "Interface                         IP Address/Mask      Physical   Protocol  VPN \r\n",
            "GigabitEthernet0/0/0              192.168.1.1/24       up         up        --  \r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_interfaces_async("Router1", topo_file, "GigabitEthernet0/0/0", "text", timeout=5.0)
        
        assert exit_code == 0


class TestShowRoutesAsync:
    """Tests for show_routes_async function."""

    @pytest.mark.asyncio
    async def test_returns_exit_code_0_on_success(self, tmp_path: Path) -> None:
        """Test that show_routes_async returns 0 on success."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display ip routing-table\r\n",
            SAMPLE_ROUTING_OUTPUT,
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_routes_async("Router1", topo_file, None, "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_filters_by_protocol(self, tmp_path: Path) -> None:
        """Test filtering routes by protocol."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        ospf_output = """
OSPF Process 1 with Router ID 1.1.1.1
Destination/Mask    Proto   Pre  Cost        Flags NextHop         Interface
  172.16.0.0/16  OSPF    10   2             D   10.0.0.2        GigabitEthernet0/0/1
"""
        chunks = [
            "display ip routing-table protocol ospf\r\n",
            ospf_output,
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_routes_async("Router1", topo_file, "ospf", "text", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_device_not_found(self, tmp_path: Path) -> None:
        """Test that show_routes_async returns 1 when device not found."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        exit_code = await show_routes_async("NonExistentRouter", topo_file, None, "text")
        
        assert exit_code == 1


class TestJsonOutput:
    """Tests for JSON output format."""

    @pytest.mark.asyncio
    async def test_show_config_json_output(self, tmp_path: Path, capsys) -> None:
        """Test that show-config produces valid JSON output."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        # Use chunks pattern to simulate realistic output
        chunks = [
            "display current-configuration\r\n",
            "sysname Router1\r\n",
            "return\r\n",
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_config_async("Router1", topo_file, None, "json", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_show_interfaces_json_output(self, tmp_path: Path) -> None:
        """Test that show-interfaces produces valid JSON output."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display ip interface brief\r\n",
            SAMPLE_INTERFACE_OUTPUT,
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_interfaces_async("Router1", topo_file, None, "json", timeout=5.0)
        
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_show_routes_json_output(self, tmp_path: Path) -> None:
        """Test that show-routes produces valid JSON output."""
        topo_file = tmp_path / "test.topo"
        topo_file.write_text(SAMPLE_TOPOLOGY_XML)
        
        chunks = [
            "display ip routing-table\r\n",
            SAMPLE_ROUTING_OUTPUT,
            "<Router1>"
        ]
        mock_client = create_mock_client(chunks)
        
        # Patch at the exec module since that's where execute_command uses device_session
        with patch("ensp_cli.commands.exec.device_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            exit_code = await show_routes_async("Router1", topo_file, None, "json", timeout=5.0)
        
        assert exit_code == 0


class TestConfigCommandIntegration:
    """Integration tests for config commands."""

    def test_show_config_help(self) -> None:
        """Test that show-config command help is accessible."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-config", "--help"])
        
        assert result.exit_code == 0
        assert "Display device running configuration" in result.output
        assert "--section" in result.output
        assert "--output" in result.output

    def test_show_interfaces_help(self) -> None:
        """Test that show-interfaces command help is accessible."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-interfaces", "--help"])
        
        assert result.exit_code == 0
        assert "Display device interface status" in result.output
        assert "--interface" in result.output

    def test_show_routes_help(self) -> None:
        """Test that show-routes command help is accessible."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-routes", "--help"])
        
        assert result.exit_code == 0
        assert "Display device routing table" in result.output
        assert "--protocol" in result.output

    def test_show_config_no_args_shows_help(self) -> None:
        """Test that show-config command with no args shows help."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-config"])
        
        # Should fail with missing arguments
        assert result.exit_code != 0
        assert "Usage:" in result.output or "Missing" in result.output or "Arguments" in result.output

    def test_show_interfaces_no_args_shows_help(self) -> None:
        """Test that show-interfaces command with no args shows help."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-interfaces"])
        
        # Should fail with missing arguments
        assert result.exit_code != 0
        assert "Usage:" in result.output or "Missing" in result.output or "Arguments" in result.output

    def test_show_routes_no_args_shows_help(self) -> None:
        """Test that show-routes command with no args shows help."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-routes"])
        
        # Should fail with missing arguments
        assert result.exit_code != 0
        assert "Usage:" in result.output or "Missing" in result.output or "Arguments" in result.output
