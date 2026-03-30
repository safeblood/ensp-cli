"""Tests for ConnectionManager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.connection_manager import (
    connect_to_device,
    device_session,
    get_device_by_name,
)
from ensp_cli.models.device import Device
from ensp_cli.models.topology import Topology


class TestGetDeviceByName:
    """Tests for get_device_by_name function."""
    
    @pytest.mark.asyncio
    async def test_find_existing_device(self):
        """Test finding a device that exists in the topology."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        topology = Topology(
            name="test",
            devices=[device]
        )
        
        result = await get_device_by_name(topology, "Router1")
        assert result is not None
        assert result.name == "Router1"
    
    @pytest.mark.asyncio
    async def test_find_nonexistent_device(self):
        """Test finding a device that doesn't exist."""
        topology = Topology(
            name="test",
            devices=[
                Device(name="Router1", device_type="Router", model="AR2220", console_port=5000)
            ]
        )
        
        result = await get_device_by_name(topology, "NonExistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_empty_topology(self):
        """Test finding in empty topology."""
        topology = Topology(name="empty", devices=[])
        
        result = await get_device_by_name(topology, "AnyDevice")
        assert result is None


class TestConnectToDevice:
    """Tests for connect_to_device function."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful device connection."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.drain = AsyncMock()
        
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = await connect_to_device(device)
            
            assert client.is_connected
            assert client.host == "127.0.0.1"
            assert client.port == 5000
    
    @pytest.mark.asyncio
    async def test_connect_failure_raises_connection_error(self):
        """Test connection failure raises ConnectionError."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   side_effect=OSError("Connection refused")):
            with pytest.raises(ConnectionError, match="Failed to connect to device 'Router1'"):
                await connect_to_device(device)
    
    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test custom timeout is passed to client."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.drain = AsyncMock()
        
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = await connect_to_device(device, timeout=30.0)
            assert client.timeout == 30.0


class TestDeviceSession:
    """Tests for device_session context manager."""
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test device_session context manager establishes connection."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.wait_closed = AsyncMock()
        mock_writer.drain = AsyncMock()
        
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            async with device_session(device) as client:
                assert client.is_connected
            
            # After exiting context, connection should be closed
            assert not client.is_connected
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_exception(self):
        """Test connection is closed even when exception occurs."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.wait_closed = AsyncMock()
        mock_writer.drain = AsyncMock()
        
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            with pytest.raises(ValueError, match="Test error"):
                async with device_session(device) as client:
                    assert client.is_connected
                    raise ValueError("Test error")
            
            # Connection should still be cleaned up
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_session_with_custom_timeout(self):
        """Test device_session with custom timeout."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.wait_closed = AsyncMock()
        mock_writer.drain = AsyncMock()
        
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            async with device_session(device, timeout=5.0) as client:
                assert client.timeout == 5.0
    
    @pytest.mark.asyncio
    async def test_session_connection_error_propagated(self):
        """Test connection errors are properly raised."""
        device = Device(
            name="Router1",
            device_type="Router",
            model="AR2220",
            console_port=5000
        )
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   side_effect=OSError("Connection refused")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                async with device_session(device) as client:
                    pass  # Should not reach here
