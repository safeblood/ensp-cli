"""Configuration exporter service for device configurations."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ensp_cli.commands.exec import execute_command
from ensp_cli.models import Device, Topology


console = Console()


class ConfigExporter:
    """Service for exporting device configurations to files."""

    SUPPORTED_FORMATS = {"txt", "json", "md"}

    def __init__(self, topology: Topology, topology_path: Optional[Path] = None):
        """Initialize the config exporter.
        
        Args:
            topology: The topology containing devices to export.
            topology_path: Optional path to the topology file for metadata.
        """
        self.topology = topology
        self.topology_path = topology_path

    async def export_device_config(
        self,
        device: Device,
        output_path: Path,
        fmt: str = "txt",
        timeout: float = 10.0,
    ) -> dict:
        """Export a single device configuration to file.
        
        Args:
            device: The device to export configuration from.
            output_path: Path where the configuration will be saved.
            fmt: Export format (txt, json, md).
            timeout: Command timeout in seconds.
            
        Returns:
            Dictionary with export result information.
            
        Raises:
            ValueError: If format is not supported.
            ConnectionError: If connection to device fails.
            asyncio.TimeoutError: If command times out.
        """
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {fmt}. Supported: {self.SUPPORTED_FORMATS}")

        # Fetch configuration from device
        config_output = await execute_command(device, "display current-configuration", timeout)

        # Prepare metadata
        metadata = self._create_metadata(device)

        # Format content based on format
        content = self._format_config(config_output, metadata, fmt)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        output_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "device": device.name,
            "output_path": str(output_path),
            "format": fmt,
            "metadata": metadata,
        }

    async def export_all_configs(
        self,
        output_dir: Path,
        fmt: str = "txt",
        timeout: float = 10.0,
        parallel: bool = True,
        progress: Optional[Progress] = None,
    ) -> list[dict]:
        """Export all device configurations in the topology.
        
        Args:
            output_dir: Directory where configurations will be saved.
            fmt: Export format (txt, json, md).
            timeout: Command timeout in seconds for each device.
            parallel: If True, fetch configs in parallel.
            progress: Optional Rich Progress instance for tracking.
            
        Returns:
            List of result dictionaries for each device.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        devices = self.topology.devices

        if progress is not None:
            task = progress.add_task(f"Exporting configs ({fmt})", total=len(devices))

        if parallel:
            # Export in parallel using asyncio.gather
            tasks = []
            for device in devices:
                output_path = self._get_output_path(output_dir, device, fmt)
                task_coro = self._export_with_progress(
                    device, output_path, fmt, timeout, progress
                )
                tasks.append(task_coro)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "success": False,
                        "device": devices[i].name,
                        "error": str(result),
                    })
                else:
                    processed_results.append(result)
            results = processed_results
        else:
            # Export sequentially
            for device in devices:
                output_path = self._get_output_path(output_dir, device, fmt)
                try:
                    result = await self._export_with_progress(
                        device, output_path, fmt, timeout, progress
                    )
                    results.append(result)
                except Exception as e:
                    results.append({
                        "success": False,
                        "device": device.name,
                        "error": str(e),
                    })

        return results

    async def _export_with_progress(
        self,
        device: Device,
        output_path: Path,
        fmt: str,
        timeout: float,
        progress: Optional[Progress],
    ) -> dict:
        """Export a device config and update progress if provided."""
        result = await self.export_device_config(device, output_path, fmt, timeout)
        if progress is not None:
            progress.advance(progress.task_ids[-1])
        return result

    def _create_metadata(self, device: Device) -> dict:
        """Create metadata dictionary for export."""
        return {
            "exported_at": datetime.now().isoformat(),
            "topology": str(self.topology_path) if self.topology_path else None,
            "topology_name": self.topology.name,
            "device": device.name,
            "device_type": device.device_type,
            "model": device.model,
        }

    def _format_config(self, config: str, metadata: dict, fmt: str) -> str:
        """Format configuration according to the specified format."""
        if fmt == "txt":
            return self._format_txt(config, metadata)
        elif fmt == "json":
            return self._format_json(config, metadata)
        elif fmt == "md":
            return self._format_markdown(config, metadata)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _format_txt(self, config: str, metadata: dict) -> str:
        """Format as plain text with header comment."""
        header = f"""! Configuration Export
! Device: {metadata['device']}
! Type: {metadata['device_type']}
! Model: {metadata['model']}
! Topology: {metadata['topology_name']}
! Exported at: {metadata['exported_at']}
!

"""
        return header + config

    def _format_json(self, config: str, metadata: dict) -> str:
        """Format as JSON with metadata and configuration."""
        data = {
            "metadata": metadata,
            "configuration": config,
        }
        return json.dumps(data, indent=2)

    def _format_markdown(self, config: str, metadata: dict) -> str:
        """Format as Markdown with syntax highlighting."""
        return f"""# Configuration Export: {metadata['device']}

## Metadata

| Field | Value |
|-------|-------|
| Device | `{metadata['device']}` |
| Type | `{metadata['device_type']}` |
| Model | `{metadata['model']}` |
| Topology | `{metadata['topology_name']}` |
| Exported at | `{metadata['exported_at']}` |

## Configuration

```
{config}
```
"""

    def _get_output_path(self, output_dir: Path, device: Device, fmt: str) -> Path:
        """Get the output file path for a device."""
        extension = fmt if fmt != "md" else "md"
        return output_dir / f"{device.name}.{extension}"


async def export_device_config(
    device: Device,
    output_path: Path,
    topology_path: Optional[Path] = None,
    fmt: str = "txt",
    timeout: float = 10.0,
) -> dict:
    """Export a single device configuration.
    
    Convenience function that creates a temporary ConfigExporter.
    
    Args:
        device: The device to export configuration from.
        output_path: Path where the configuration will be saved.
        topology_path: Optional path to the topology file for metadata.
        fmt: Export format (txt, json, md).
        timeout: Command timeout in seconds.
        
    Returns:
        Dictionary with export result information.
    """
    # Create a minimal topology for the single device
    temp_topology = Topology(name="standalone", devices=[device], connections=[])
    exporter = ConfigExporter(temp_topology, topology_path)
    return await exporter.export_device_config(device, output_path, fmt, timeout)


async def export_all_configs(
    topology: Topology,
    output_dir: Path,
    topology_path: Optional[Path] = None,
    fmt: str = "txt",
    timeout: float = 10.0,
    parallel: bool = True,
) -> list[dict]:
    """Export all device configurations in a topology.
    
    Convenience function that creates a ConfigExporter with progress display.
    
    Args:
        topology: The topology containing devices to export.
        output_dir: Directory where configurations will be saved.
        topology_path: Optional path to the topology file for metadata.
        fmt: Export format (txt, json, md).
        timeout: Command timeout in seconds for each device.
        parallel: If True, fetch configs in parallel.
        
    Returns:
        List of result dictionaries for each device.
    """
    exporter = ConfigExporter(topology, topology_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        return await exporter.export_all_configs(
            output_dir, fmt, timeout, parallel, progress
        )
