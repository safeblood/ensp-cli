"""Connection manager for eNSP device Telnet sessions."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .models.device import Device
from .models.topology import Topology
from .telnet_client import TelnetClient


async def get_device_by_name(topology: Topology, name: str) -> Device | None:
    """Find a device by name in the topology.
    
    Args:
        topology: The topology to search in.
        name: The device name to search for.
        
    Returns:
        The Device if found, None otherwise.
    """
    return topology.get_device(name)


async def connect_to_device(device: Device, timeout: float = 10.0) -> TelnetClient:
    """Create and establish a Telnet connection to a device.
    
    Args:
        device: The device to connect to.
        timeout: Connection timeout in seconds.
        
    Returns:
        Connected TelnetClient instance.
        
    Raises:
        ConnectionError: If connection fails.
        ValueError: If device console port is invalid.
    """
    if device.console_port < 1 or device.console_port > 65535:
        raise ValueError(
            f"Invalid console port {device.console_port} for device '{device.name}'"
        )
    
    client = TelnetClient(
        host="127.0.0.1",  # eNSP devices are always on localhost
        port=device.console_port,
        timeout=timeout,
    )
    
    try:
        await client.connect()
    except Exception as e:
        # Ensure client is closed if connection fails
        await client.close()
        raise ConnectionError(
            f"Failed to connect to device '{device.name}' "
            f"at port {device.console_port}: {e}"
        ) from e
    
    return client


@asynccontextmanager
async def device_session(
    device: Device, 
    timeout: float = 10.0
) -> AsyncGenerator[TelnetClient, None]:
    """Context manager for device Telnet session.
    
    This context manager establishes a Telnet connection to the device
    and ensures proper cleanup when exiting the context, even if an
    exception occurs.
    
    Args:
        device: The device to connect to.
        timeout: Connection and operation timeout in seconds.
        
    Yields:
        Connected TelnetClient instance.
        
    Raises:
        ConnectionError: If connection fails.
        ValueError: If device console port is invalid.
        
    Example:
        ```python
        topology = parse_topology("topology.topo")
        device = topology.get_device("Router1")
        
        async with device_session(device) as client:
            await client.write_line("display version")
            output = await client.read_until("<Router1>")
            print(output)
        # Connection automatically closed here
        ```
    """
    client: TelnetClient | None = None
    
    try:
        client = await connect_to_device(device, timeout)
        yield client
    finally:
        if client is not None:
            await client.close()
