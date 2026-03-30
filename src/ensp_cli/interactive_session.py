"""Interactive console session for eNSP device connections."""

import asyncio
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .telnet_client import TelnetClient


class InteractiveSession:
    """Interactive console session that pipes user input to Telnet and displays output.
    
    This class provides bidirectional data flow between stdin/stdout and a Telnet
    connection, enabling real-time interaction with eNSP devices. It handles
    special keys for graceful exit and provides user-friendly session messages.
    
    Attributes:
        client: The TelnetClient instance to use for communication.
        device_name: Name of the device for display purposes.
        _running: Flag indicating if the session is active.
        _input_task: Task for the input reader coroutine.
        _output_task: Task for the output reader coroutine.
    """
    
    def __init__(self, client: "TelnetClient", device_name: str = "device") -> None:
        """Initialize interactive session.
        
        Args:
            client: The TelnetClient instance to use for communication.
            device_name: Name of the device for display purposes.
        """
        self.client = client
        self.device_name = device_name
        self._running = False
        self._input_task: asyncio.Task | None = None
        self._output_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Start the interactive session.
        
        Displays connection banner and begins bidirectional communication
        between stdin/stdout and the Telnet connection.
        
        Raises:
            ConnectionError: If not connected to the device.
        """
        if not self.client.is_connected:
            raise ConnectionError("Not connected to device")
        
        self._running = True
        
        # Display session banner
        self._print_banner()
        
        # Start input and output readers concurrently
        self._input_task = asyncio.create_task(self._input_reader())
        self._output_task = asyncio.create_task(self._output_reader())
        
        # Wait for both tasks to complete (one will exit when user disconnects)
        try:
            await asyncio.gather(self._input_task, self._output_task)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the interactive session gracefully.
        
        Cancels running tasks and displays disconnection message.
        """
        self._running = False
        
        # Cancel running tasks
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
            try:
                await self._input_task
            except asyncio.CancelledError:
                pass
        
        if self._output_task and not self._output_task.done():
            self._output_task.cancel()
            try:
                await self._output_task
            except asyncio.CancelledError:
                pass
        
        # Print disconnection message
        print(f"\n[Disconnected from {self.device_name}]")
    
    async def _input_reader(self) -> None:
        """Read from stdin and forward to Telnet.
        
        Continuously reads characters from stdin and sends them to the
        Telnet connection. Handles special keys for session control.
        """
        while self._running:
            try:
                char = await self._read_char()
                
                if char == '\x03':  # Ctrl+C
                    self._running = False
                    break
                elif char == '\x04':  # Ctrl+D
                    self._running = False
                    break
                elif char == '\x1d':  # Ctrl+]
                    self._running = False
                    break
                
                # Forward character to Telnet
                await self.client.write(char)
                
            except asyncio.CancelledError:
                break
            except ConnectionError:
                # Connection lost, exit gracefully
                self._running = False
                break
            except Exception:
                # Other errors, continue if possible
                await asyncio.sleep(0.01)
    
    async def _output_reader(self) -> None:
        """Read from Telnet and display on stdout.
        
        Continuously reads data from the Telnet connection and displays
        it on stdout in real-time.
        """
        while self._running:
            try:
                data = await self.client.read_available()
                if data:
                    sys.stdout.write(data)
                    sys.stdout.flush()
                else:
                    # Small delay to prevent busy-wait
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except ConnectionError:
                print("\n[Connection lost]", file=sys.stderr)
                self._running = False
                break
            except Exception:
                # Other errors, continue if possible
                await asyncio.sleep(0.01)
    
    async def _read_char(self) -> str:
        """Read a single character from stdin.
        
        Uses platform-specific methods for non-blocking character input.
        On Windows, uses msvcrt. On Unix, uses standard stdin.
        
        Returns:
            Single character read from stdin.
        """
        if sys.platform == 'win32':
            return await self._read_char_windows()
        else:
            return await self._read_char_unix()
    
    async def _read_char_windows(self) -> str:
        """Read a character on Windows using sys.stdin.buffer.
        
        Uses sys.stdin.buffer.read() which works better in Windows Terminal
        and PowerShell compared to msvcrt.getch().
        
        Returns:
            Single character read from stdin.
        """
        import sys
        
        while self._running:
            try:
                # Use asyncio.to_thread for non-blocking read
                char = await asyncio.to_thread(sys.stdin.buffer.read, 1)
                if char:
                    try:
                        return char.decode('utf-8')
                    except UnicodeDecodeError:
                        return char.decode('latin-1')
            except (OSError, ValueError):
                # stdin might be closed or not available
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.01)
        
        return ''
    
    async def _read_char_unix(self) -> str:
        """Read a character on Unix-like systems.
        
        Returns:
            Single character read from stdin.
        """
        import termios
        import tty
        
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode for character-by-character input
            tty.setraw(fd)
            
            while self._running:
                # Use asyncio.to_thread for non-blocking read
                char = await asyncio.to_thread(sys.stdin.read, 1)
                if char:
                    return char
                await asyncio.sleep(0.01)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        return ''
    
    def _print_banner(self) -> None:
        """Print session start banner with connection info."""
        print("\nPress Ctrl+] or type 'exit' to exit\n")
