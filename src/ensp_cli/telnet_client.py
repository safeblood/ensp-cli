"""Async Telnet client for eNSP device connections."""

import asyncio
import re
from typing import Pattern, Union

import telnetlib3

# VRP prompt patterns
VRP_PROMPT_USER = re.compile(r"^<[\w\-]+>$", re.MULTILINE)
VRP_PROMPT_SYSTEM = re.compile(r"^\[[\w\-]+(?:-[\w\/\-]+)*\]$", re.MULTILINE)
VRP_PROMPT_ANY = re.compile(r"(?:<[\w\-]+>|\[[\w\-]+(?:-[\w\/\-]+)*\])$", re.MULTILINE)


class TelnetClient:
    """Async Telnet client for connecting to eNSP devices.
    
    This client provides async read/write operations with timeout support
    and VRP prompt detection for Huawei network devices.
    
    Attributes:
        host: Target host address (typically 127.0.0.1 for eNSP).
        port: Telnet port number.
        timeout: Default timeout for operations in seconds.
    """
    
    def __init__(self, host: str, port: int, timeout: float = 10.0) -> None:
        """Initialize Telnet client.
        
        Args:
            host: Target host address.
            port: Telnet port number.
            timeout: Default timeout for operations in seconds.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader: telnetlib3.TelnetReader | None = None
        self._writer: telnetlib3.TelnetWriter | None = None
        self._buffer: str = ""
    
    async def connect(self) -> None:
        """Establish Telnet connection to the device.
        
        Raises:
            ConnectionError: If connection fails.
            asyncio.TimeoutError: If connection times out.
        """
        try:
            self._reader, self._writer = await telnetlib3.open_connection(
                self.host,
                self.port,
                connect_minwait=0.0,
            )
        except OSError as e:
            raise ConnectionError(
                f"Failed to connect to {self.host}:{self.port}: {e}"
            ) from e
    
    async def read_until(
        self, 
        pattern: Union[str, Pattern[str]], 
        timeout: float | None = None
    ) -> str:
        """Read data until pattern is found or timeout.
        
        Args:
            pattern: String or regex pattern to match.
            timeout: Timeout in seconds (uses default if None).
        
        Returns:
            Data read from the connection.
        
        Raises:
            ConnectionError: If not connected.
            asyncio.TimeoutError: If pattern not found within timeout.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
        
        timeout = timeout if timeout is not None else self.timeout
        
        # Convert string pattern to regex
        if isinstance(pattern, str):
            pattern = re.compile(re.escape(pattern))
        
        # Check existing buffer first
        if pattern.search(self._buffer):
            match = pattern.search(self._buffer)
            assert match is not None
            result = self._buffer[:match.end()]
            self._buffer = self._buffer[match.end():]
            return result
        
        # Read until pattern found or timeout
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = timeout - elapsed
            
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"Pattern not found within {timeout} seconds"
                )
            
            try:
                # Read available data with timeout
                data = await asyncio.wait_for(
                    self._reader.read(4096),  # type: ignore
                    timeout=min(0.1, remaining)
                )
                
                if data:
                    # Decode using ascii with replace for VRP compatibility
                    decoded = data.decode("ascii", errors="replace")
                    self._buffer += decoded
                    
                    # Check if pattern matches
                    match = pattern.search(self._buffer)
                    if match:
                        result = self._buffer[:match.end()]
                        self._buffer = self._buffer[match.end():]
                        return result
            except asyncio.TimeoutError:
                # Check if overall timeout expired
                if asyncio.get_event_loop().time() - start_time >= timeout:
                    raise asyncio.TimeoutError(
                        f"Pattern not found within {timeout} seconds"
                    )
                continue
    
    async def read_available(self) -> str:
        """Read all currently available data without blocking.
        
        Returns:
            Data available in the buffer and from the connection.
        
        Raises:
            ConnectionError: If not connected.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
        
        result = self._buffer
        self._buffer = ""
        
        # Try to read any available data without blocking
        try:
            while True:
                data = await asyncio.wait_for(
                    self._reader.read(4096),  # type: ignore
                    timeout=0.01
                )
                if not data:
                    break
                # telnetlib3 returns strings, not bytes
                if isinstance(data, bytes):
                    result += data.decode("ascii", errors="replace")
                else:
                    result += data
        except asyncio.TimeoutError:
            pass
        
        return result
    
    async def write(self, data: str) -> None:
        """Write data to the connection.
        
        Args:
            data: String data to write.
        
        Raises:
            ConnectionError: If not connected.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
        
        if not data:
            return
        
        # telnetlib3 handles encoding, pass string directly
        self._writer.write(data)  # type: ignore
        await self._writer.drain()  # type: ignore
    
    async def write_line(self, data: str) -> None:
        """Write data followed by newline to the connection.
        
        Args:
            data: String data to write.
        
        Raises:
            ConnectionError: If not connected.
        """
        await self.write(data + "\n")
    
    async def close(self) -> None:
        """Close the Telnet connection and clean up resources."""
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
            self._buffer = ""
    
    @property
    def is_connected(self) -> bool:
        """Check if the connection is active.
        
        Returns:
            True if connected, False otherwise.
        """
        return (
            self._reader is not None 
            and self._writer is not None 
            and not self._writer.is_closing()
        )
    
    async def __aenter__(self) -> "TelnetClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
