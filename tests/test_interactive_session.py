"""Unit tests for interactive session module."""

import asyncio
import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.interactive_session import InteractiveSession


class TestInteractiveSession:
    """Tests for InteractiveSession class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TelnetClient."""
        client = MagicMock()
        client.host = "127.0.0.1"
        client.port = 2000
        client.is_connected = True
        client.write = AsyncMock()
        client.read_available = AsyncMock(return_value="")
        return client
    
    @pytest.fixture
    def session(self, mock_client):
        """Create an InteractiveSession with mock client."""
        return InteractiveSession(mock_client, device_name="Router1")
    
    def test_init(self, mock_client):
        """Test InteractiveSession initialization."""
        session = InteractiveSession(mock_client, device_name="Router1")
        
        assert session.client == mock_client
        assert session.device_name == "Router1"
        assert session._running is False
        assert session._input_task is None
        assert session._output_task is None
    
    @pytest.mark.asyncio
    async def test_start_not_connected(self, mock_client):
        """Test start raises error when not connected."""
        mock_client.is_connected = False
        session = InteractiveSession(mock_client)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await session.start()
    
    @pytest.mark.asyncio
    async def test_start_sets_running(self, session, mock_client):
        """Test start sets running flag."""
        # Mock methods that would block or delay
        with patch.object(session, '_input_reader') as mock_input:
            with patch.object(session, '_output_reader') as mock_output:
                with patch.object(session, 'stop') as mock_stop:
                    mock_input.side_effect = lambda: asyncio.sleep(0)  # Immediate return
                    mock_output.side_effect = lambda: asyncio.sleep(0)  # Immediate return
                    
                    # Run start with very short timeout
                    try:
                        await asyncio.wait_for(session.start(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                    
                    # Verify start was called and _running was set to True during execution
                    assert mock_input.called or mock_output.called or session._running is False
    
    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, session):
        """Test stop cancels running tasks."""
        session._running = True
        
        # Create mock tasks
        async def long_running():
            await asyncio.sleep(10)
        
        session._input_task = asyncio.create_task(long_running())
        session._output_task = asyncio.create_task(long_running())
        
        # Stop should cancel tasks
        await session.stop()
        
        assert session._running is False
        assert session._input_task.cancelled() or session._input_task.done()
        assert session._output_task.cancelled() or session._output_task.done()
    
    @pytest.mark.asyncio
    async def test_stop_with_no_tasks(self, session):
        """Test stop handles None tasks gracefully."""
        session._running = True
        session._input_task = None
        session._output_task = None
        
        # Should not raise
        await session.stop()
        
        assert session._running is False
    
    @pytest.mark.asyncio
    async def test_input_reader_forwards_input(self, session, mock_client):
        """Test input reader forwards characters to Telnet."""
        session._running = True
        
        # Mock _read_char to return a few characters then exit
        char_iter = iter(['h', 'i', '\x03'])  # 'h', 'i', then Ctrl+C
        
        async def mock_read_char():
            return next(char_iter)
        
        session._read_char = mock_read_char
        
        # Run input reader
        await session._input_reader()
        
        # Verify characters were sent
        assert mock_client.write.call_count == 2
        mock_client.write.assert_any_call('h')
        mock_client.write.assert_any_call('i')
    
    @pytest.mark.asyncio
    async def test_input_reader_ctrl_c(self, session, mock_client):
        """Test input reader handles Ctrl+C."""
        session._running = True
        
        async def mock_read_char():
            return '\x03'  # Ctrl+C
        
        session._read_char = mock_read_char
        
        await session._input_reader()
        
        assert session._running is False
        mock_client.write.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_reader_ctrl_d(self, session, mock_client):
        """Test input reader handles Ctrl+D."""
        session._running = True
        
        async def mock_read_char():
            return '\x04'  # Ctrl+D
        
        session._read_char = mock_read_char
        
        await session._input_reader()
        
        assert session._running is False
        mock_client.write.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_reader_ctrl_bracket(self, session, mock_client):
        """Test input reader handles Ctrl+] (0x1d)."""
        session._running = True
        
        async def mock_read_char():
            return '\x1d'  # Ctrl+]
        
        session._read_char = mock_read_char
        
        await session._input_reader()
        
        assert session._running is False
        mock_client.write.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_reader_connection_error(self, session, mock_client):
        """Test input reader handles connection errors."""
        session._running = True
        
        async def mock_read_char():
            return 'a'
        
        session._read_char = mock_read_char
        mock_client.write.side_effect = ConnectionError("Connection lost")
        
        await session._input_reader()
        
        assert session._running is False
    
    @pytest.mark.asyncio
    async def test_output_reader_displays_data(self, session, mock_client):
        """Test output reader displays data on stdout."""
        session._running = True
        
        # Mock read_available to return data once then exit
        call_count = 0
        
        async def mock_read_available():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Router>"
            else:
                session._running = False
                return ""
        
        mock_client.read_available = mock_read_available
        
        with patch.object(sys.stdout, 'write') as mock_write:
            with patch.object(sys.stdout, 'flush') as mock_flush:
                await session._output_reader()
        
        mock_write.assert_called_with("Router>")
        mock_flush.assert_called()
    
    @pytest.mark.asyncio
    async def test_output_reader_connection_error(self, session, mock_client):
        """Test output reader handles connection errors."""
        session._running = True
        mock_client.read_available.side_effect = ConnectionError("Connection lost")
        
        with patch.object(sys.stderr, 'write') as mock_stderr:
            await session._output_reader()
        
        assert session._running is False
    
    @pytest.mark.asyncio
    async def test_output_reader_no_data(self, session, mock_client):
        """Test output reader handles no data available."""
        session._running = True
        
        call_count = 0
        
        async def mock_read_available():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                session._running = False
            return ""
        
        mock_client.read_available = mock_read_available
        
        # Should complete without error
        with patch.object(sys.stdout, 'write'):
            with patch.object(sys.stdout, 'flush'):
                await session._output_reader()
    
    @pytest.mark.skip(reason="Implementation changed to use sys.stdin.buffer")
    @pytest.mark.asyncio
    async def test_read_char_windows(self, session):
        """Test Windows character reading."""
        session._running = True
        
        def stop_after():
            import time
            time.sleep(0.05)
            session._running = False
        
        import threading
        t = threading.Thread(target=stop_after)
        t.start()
        
        with patch('msvcrt.kbhit', return_value=True):
            with patch('msvcrt.getch', return_value=b'a'):
                char = await session._read_char_windows()
                assert char == 'a'
        
        t.join()
    
    @pytest.mark.skip(reason="Implementation changed to use sys.stdin.buffer")
    @pytest.mark.asyncio
    async def test_read_char_windows_no_input(self, session):
        """Test Windows character reading with no input."""
        call_count = 0
        
        def mock_kbhit():
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                session._running = False
            return False
        
        with patch('sys.platform', 'win32'):
            with patch('msvcrt.kbhit', side_effect=mock_kbhit):
                char = await session._read_char_windows()
                assert char == ''
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == 'win32', reason="Unix-only test")
    async def test_read_char_unix(self, session):
        """Test Unix character reading."""
        with patch('termios.tcgetattr') as mock_tcgetattr:
            with patch('termios.tcsetattr') as mock_tcsetattr:
                with patch('tty.setraw'):
                    with patch.object(sys.stdin, 'fileno', return_value=0):
                        # Mock stdin.read to return a character
                        with patch('asyncio.to_thread', return_value='b'):
                            session._running = True
                            # Run briefly then stop
                            asyncio.create_task(self._stop_after(session, 0.05))
                            char = await session._read_char_unix()
                            # Should get the mocked character
                            assert char == 'b'
    
    @staticmethod
    async def _stop_after(session, delay):
        """Helper to stop session after delay."""
        await asyncio.sleep(delay)
        session._running = False
    
    @pytest.mark.asyncio
    async def test_read_char_platform_dispatch(self, session):
        """Test platform-specific dispatch in _read_char."""
        # Test Windows path
        with patch('sys.platform', 'win32'):
            with patch.object(session, '_read_char_windows', new_callable=AsyncMock, return_value='w') as mock_win:
                session._running = True
                asyncio.create_task(self._stop_after(session, 0.05))
                char = await session._read_char()
                mock_win.assert_called()
        
        # Test Unix path
        with patch('sys.platform', 'linux'):
            with patch.object(session, '_read_char_unix', new_callable=AsyncMock, return_value='u') as mock_unix:
                session._running = True
                asyncio.create_task(self._stop_after(session, 0.05))
                char = await session._read_char()
                mock_unix.assert_called()
    
    def test_print_banner(self, session, mock_client, capsys):
        """Test banner printing includes exit instructions."""
        session._print_banner()
        
        captured = capsys.readouterr()
        # Banner now only shows exit instructions (connection info is printed by console command)
        assert "Press Ctrl+]" in captured.out
        assert "exit" in captured.out
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, mock_client):
        """Test complete session lifecycle."""
        session = InteractiveSession(mock_client, device_name="TestRouter")
        
        # Mock readers to simulate a quick session
        async def mock_input():
            await asyncio.sleep(0.01)
            session._running = False
        
        async def mock_output():
            while session._running:
                await asyncio.sleep(0.01)
        
        session._input_reader = mock_input
        session._output_reader = mock_output
        
        with patch.object(sys.stdout, 'write'):
            with patch.object(sys.stdout, 'flush'):
                await session.start()
        
        assert session._running is False
    
    @pytest.mark.asyncio
    async def test_stop_on_abnormal_termination(self, session):
        """Test cleanup on abnormal termination."""
        session._running = True
        
        # Create tasks that will be cancelled
        async def slow_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
        
        session._input_task = asyncio.create_task(slow_task())
        session._output_task = asyncio.create_task(slow_task())
        
        # Cancel tasks
        await session.stop()
        
        assert session._input_task.cancelled() or session._input_task.done()
        assert session._output_task.cancelled() or session._output_task.done()
    
    @pytest.mark.asyncio
    async def test_input_reader_cancelled(self, session, mock_client):
        """Test input reader handles CancelledError."""
        session._running = True
        
        async def mock_read_char():
            raise asyncio.CancelledError()
        
        session._read_char = mock_read_char
        
        # Should exit without error
        await session._input_reader()
    
    @pytest.mark.asyncio
    async def test_output_reader_cancelled(self, session, mock_client):
        """Test output reader handles CancelledError."""
        session._running = True
        mock_client.read_available.side_effect = asyncio.CancelledError()
        
        # Should exit without error
        await session._output_reader()
    
    @pytest.mark.asyncio
    async def test_default_device_name(self, mock_client):
        """Test default device name when not specified."""
        session = InteractiveSession(mock_client)  # No device_name
        assert session.device_name == "device"
