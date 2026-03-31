"""Tests for TelnetClient."""

import asyncio
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.telnet_client import (
    TelnetClient,
    VRP_PROMPT_ANY,
    VRP_PROMPT_SYSTEM,
    VRP_PROMPT_USER,
)


class TestTelnetClient:
    """Tests for TelnetClient class."""
    
    def test_client_creation(self):
        """Test creating a TelnetClient with default timeout."""
        client = TelnetClient("127.0.0.1", 5000)
        assert client.host == "127.0.0.1"
        assert client.port == 5000
        assert client.timeout == 10.0
        assert not client.is_connected
    
    def test_client_creation_custom_timeout(self):
        """Test creating a TelnetClient with custom timeout."""
        client = TelnetClient("192.168.1.1", 5000, timeout=5.0)
        assert client.host == "192.168.1.1"
        assert client.port == 5000
        assert client.timeout == 5.0
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection", 
                   return_value=(mock_reader, mock_writer)) as mock_open:
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            assert client.is_connected
            mock_open.assert_called_once_with(
                "127.0.0.1", 5000, connect_minwait=0.0,
                encoding='utf-8', force_binary=False
            )
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure raises ConnectionError."""
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   side_effect=OSError("Connection refused")):
            client = TelnetClient("127.0.0.1", 5000)
            
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()
            
            assert not client.is_connected
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing connection."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.wait_closed = AsyncMock()
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            assert client.is_connected
            
            await client.close()
            assert not client.is_connected
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_write_not_connected(self):
        """Test write raises ConnectionError when not connected."""
        client = TelnetClient("127.0.0.1", 5000)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await client.write("test")
    
    @pytest.mark.asyncio
    async def test_write_success(self):
        """Test successful write operation."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.drain = AsyncMock()
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            await client.write("display version")
            mock_writer.write.assert_called_once_with("display version")
            mock_writer.drain.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_write_line(self):
        """Test write_line adds newline."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.drain = AsyncMock()
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            await client.write_line("display version")
            mock_writer.write.assert_called_once_with("display version\n")
    
    @pytest.mark.asyncio
    async def test_read_until_not_connected(self):
        """Test read_until raises ConnectionError when not connected."""
        client = TelnetClient("127.0.0.1", 5000)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await client.read_until("prompt")
    
    @pytest.mark.asyncio
    async def test_read_until_pattern_found_in_buffer(self):
        """Test read_until finds pattern in existing buffer."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            # Pre-populate buffer
            client._buffer = "some output<Huawei>"
            
            result = await client.read_until("<Huawei>")
            assert "<Huawei>" in result
            assert client._buffer == ""  # Buffer should be cleared after match
    
    @pytest.mark.asyncio
    async def test_read_until_reads_data(self):
        """Test read_until reads data from connection."""
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"<Huawei>")
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            result = await client.read_until("<Huawei>")
            assert "<Huawei>" in result
    
    @pytest.mark.asyncio
    async def test_read_until_timeout(self):
        """Test read_until raises TimeoutError."""
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000, timeout=0.01)
            await client.connect()
            
            with pytest.raises(asyncio.TimeoutError):
                await client.read_until("never-match")
    
    @pytest.mark.asyncio
    async def test_read_until_with_regex_pattern(self):
        """Test read_until with regex pattern."""
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"[Huawei]")
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            pattern = re.compile(r"\[Huawei\]")
            result = await client.read_until(pattern)
            assert "[Huawei]" in result
    
    @pytest.mark.asyncio
    async def test_read_available_not_connected(self):
        """Test read_available raises ConnectionError when not connected."""
        client = TelnetClient("127.0.0.1", 5000)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await client.read_available()
    
    @pytest.mark.asyncio
    async def test_read_available_returns_buffer(self):
        """Test read_available returns buffer contents."""
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            client = TelnetClient("127.0.0.1", 5000)
            await client.connect()
            
            client._buffer = "cached data"
            result = await client.read_available()
            assert result == "cached data"
            assert client._buffer == ""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.wait_closed = AsyncMock()
        
        with patch("ensp_cli.telnet_client.telnetlib3.open_connection",
                   return_value=(mock_reader, mock_writer)):
            async with TelnetClient("127.0.0.1", 5000) as client:
                assert client.is_connected
            
            assert not client.is_connected
            mock_writer.close.assert_called_once()


class TestVRPPromptPatterns:
    """Tests for VRP prompt detection patterns."""
    
    def test_user_mode_pattern_matches(self):
        """Test VRP_PROMPT_USER matches user mode prompts."""
        assert VRP_PROMPT_USER.search("<Huawei>")
        assert VRP_PROMPT_USER.search("<Router1>")
        assert VRP_PROMPT_USER.search("<SW-Core-01>")
        assert VRP_PROMPT_USER.search("Before\n<Huawei>\nAfter")
    
    def test_user_mode_pattern_no_false_positives(self):
        """Test VRP_PROMPT_USER doesn't match non-prompts."""
        assert not VRP_PROMPT_USER.search("Not <Huawei> prompt")
        assert not VRP_PROMPT_USER.search("Missing bracket <Huawei")
        assert not VRP_PROMPT_USER.search("Huawei>")
    
    def test_system_mode_pattern_matches(self):
        """Test VRP_PROMPT_SYSTEM matches system mode prompts."""
        assert VRP_PROMPT_SYSTEM.search("[Huawei]")
        assert VRP_PROMPT_SYSTEM.search("[Huawei-GigabitEthernet0/0/1]")
        assert VRP_PROMPT_SYSTEM.search("[Router1-Ethernet0/0/0]")
        assert VRP_PROMPT_SYSTEM.search("[SW-Core-01-Vlanif100]")
    
    def test_system_mode_pattern_no_false_positives(self):
        """Test VRP_PROMPT_SYSTEM doesn't match non-prompts."""
        assert not VRP_PROMPT_SYSTEM.search("Not [Huawei] prompt")
        assert not VRP_PROMPT_SYSTEM.search("Missing bracket [Huawei")
        assert not VRP_PROMPT_SYSTEM.search("Huawei]")
    
    def test_any_prompt_pattern_matches(self):
        """Test VRP_PROMPT_ANY matches both user and system mode."""
        assert VRP_PROMPT_ANY.search("<Huawei>")
        assert VRP_PROMPT_ANY.search("[Huawei]")
        assert VRP_PROMPT_ANY.search("[Huawei-GigabitEthernet0/0/1]")
    
    def test_any_prompt_pattern_at_line_end(self):
        """Test VRP_PROMPT_ANY matches at end of line."""
        text = "some output here\n<Huawei>"
        match = VRP_PROMPT_ANY.search(text)
        assert match
        assert match.group().endswith(">") or match.group().endswith("]")
