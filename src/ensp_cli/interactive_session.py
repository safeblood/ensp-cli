"""Interactive session for eNSP device console access."""

import asyncio
import sys

from .telnet_client import TelnetClient


class InteractiveSession:
    """Interactive terminal session with an eNSP device.
    
    This class manages the bidirectional data flow between the user
    and the device, handling user input and device output in separate
    async tasks.
    
    Attributes:
        client: The connected TelnetClient instance.
        running: Whether the session is currently active.
    """
    
    def __init__(self, client: TelnetClient) -> None:
        """Initialize interactive session.
        
        Args:
            client: Connected TelnetClient instance.
        """
        self.client = client
        self.running = False
    
    async def start(self) -> None:
        """Start the interactive session.
        
        This method runs two concurrent tasks:
        - One for reading user input and sending to device
        - One for reading device output and displaying to user
        
        The session can be terminated by:
        - Ctrl+] (0x1d) character
        - Ctrl+D (EOF on Unix)
        - KeyboardInterrupt (Ctrl+C)
        """
        self.running = True
        
        try:
            await asyncio.gather(
                self._read_from_user(),
                self._read_from_device(),
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
    
    async def _read_from_user(self) -> None:
        """Read input from user and send to device.
        
        Handles special control characters for session management.
        """
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                # Read a single character from stdin
                char = await loop.run_in_executor(None, sys.stdin.read, 1)
                
                if not char:  # EOF
                    self.running = False
                    break
                
                # Ctrl+] (0x1d) - exit session
                if char == '\x1d':
                    self.running = False
                    break
                
                # Ctrl+D (0x04) - exit session
                if char == '\x04':
                    self.running = False
                    break
                
                # Send character to device
                await self.client.write(char)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception:
                # Ignore other errors during input
                continue
    
    async def _read_from_device(self) -> None:
        """Read output from device and display to user."""
        while self.running:
            try:
                # Read available data from device
                data = await self.client.read_available()
                
                if data:
                    # Print to stdout without buffering
                    sys.stdout.write(data)
                    sys.stdout.flush()
                else:
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.01)
                    
            except ConnectionError:
                # Connection lost
                print("\n[Connection lost]")
                self.running = False
                break
            except Exception:
                # Ignore other errors
                await asyncio.sleep(0.01)
