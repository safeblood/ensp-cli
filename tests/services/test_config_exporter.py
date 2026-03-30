"""Tests for the config exporter service."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ensp_cli.models import Device, Topology
from ensp_cli.services.config_exporter import ConfigExporter, export_all_configs, export_device_config


@pytest.fixture
def sample_device():
    """Create a sample device for testing."""
    return Device(
        name="R1",
        device_type="Router",
        model="AR2220",
        console_port=2000,
    )


@pytest.fixture
def sample_topology(sample_device):
    """Create a sample topology for testing."""
    device2 = Device(
        name="R2",
        device_type="Router",
        model="AR2220",
        console_port=2001,
    )
    return Topology(
        name="TestTopology",
        devices=[sample_device, device2],
        connections=[],
    )


@pytest.fixture
def sample_config():
    """Sample configuration output."""
    return """#
sysname R1
#
interface GigabitEthernet0/0/0
 ip address 192.168.1.1 255.255.255.0
#
return"""


class TestConfigExporter:
    """Tests for ConfigExporter class."""

    def test_init(self, sample_topology):
        """Test ConfigExporter initialization."""
        exporter = ConfigExporter(sample_topology)
        assert exporter.topology == sample_topology
        assert exporter.topology_path is None

    def test_init_with_topology_path(self, sample_topology, tmp_path):
        """Test ConfigExporter initialization with topology path."""
        topo_path = tmp_path / "test.topo"
        exporter = ConfigExporter(sample_topology, topo_path)
        assert exporter.topology == sample_topology
        assert exporter.topology_path == topo_path

    def test_supported_formats(self):
        """Test supported formats constant."""
        assert ConfigExporter.SUPPORTED_FORMATS == {"txt", "json", "md"}

    @pytest.mark.asyncio
    async def test_export_device_config_txt(self, sample_device, sample_topology, sample_config, tmp_path):
        """Test exporting device config in txt format."""
        output_path = tmp_path / "r1.cfg"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            result = await exporter.export_device_config(sample_device, output_path, fmt="txt")

        assert result["success"] is True
        assert result["device"] == "R1"
        assert result["format"] == "txt"
        assert output_path.exists()

        content = output_path.read_text()
        assert "Configuration Export" in content
        assert "Device: R1" in content
        assert "sysname R1" in content

    @pytest.mark.asyncio
    async def test_export_device_config_json(self, sample_device, sample_topology, sample_config, tmp_path):
        """Test exporting device config in JSON format."""
        output_path = tmp_path / "r1.json"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            result = await exporter.export_device_config(sample_device, output_path, fmt="json")

        assert result["success"] is True
        assert result["device"] == "R1"
        assert result["format"] == "json"
        assert output_path.exists()

        content = output_path.read_text()
        data = json.loads(content)
        assert "metadata" in data
        assert "configuration" in data
        assert data["metadata"]["device"] == "R1"
        assert data["metadata"]["device_type"] == "Router"
        assert data["metadata"]["model"] == "AR2220"
        assert "exported_at" in data["metadata"]

    @pytest.mark.asyncio
    async def test_export_device_config_markdown(self, sample_device, sample_topology, sample_config, tmp_path):
        """Test exporting device config in Markdown format."""
        output_path = tmp_path / "r1.md"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            result = await exporter.export_device_config(sample_device, output_path, fmt="md")

        assert result["success"] is True
        assert result["device"] == "R1"
        assert result["format"] == "md"
        assert output_path.exists()

        content = output_path.read_text()
        assert "# Configuration Export: R1" in content
        assert "## Metadata" in content
        assert "## Configuration" in content
        assert "```" in content
        assert "sysname R1" in content

    @pytest.mark.asyncio
    async def test_export_device_config_invalid_format(self, sample_device, sample_topology, tmp_path):
        """Test exporting with invalid format raises error."""
        output_path = tmp_path / "r1.invalid"
        exporter = ConfigExporter(sample_topology)

        with pytest.raises(ValueError, match="Unsupported format: invalid"):
            await exporter.export_device_config(sample_device, output_path, fmt="invalid")

    @pytest.mark.asyncio
    async def test_export_device_config_creates_parent_dirs(self, sample_device, sample_topology, sample_config, tmp_path):
        """Test that export creates parent directories."""
        output_path = tmp_path / "nested" / "dir" / "r1.cfg"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            await exporter.export_device_config(sample_device, output_path, fmt="txt")

        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_export_all_configs(self, sample_topology, sample_config, tmp_path):
        """Test exporting all device configs."""
        output_dir = tmp_path / "exports"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            results = await exporter.export_all_configs(output_dir, fmt="txt")

        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert (output_dir / "R1.txt").exists()
        assert (output_dir / "R2.txt").exists()

    @pytest.mark.asyncio
    async def test_export_all_configs_sequential(self, sample_topology, sample_config, tmp_path):
        """Test exporting all device configs sequentially."""
        output_dir = tmp_path / "exports"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            results = await exporter.export_all_configs(output_dir, fmt="txt", parallel=False)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_export_all_configs_with_errors(self, sample_topology, sample_config, tmp_path):
        """Test that export_all handles errors gracefully."""
        output_dir = tmp_path / "exports"
        exporter = ConfigExporter(sample_topology)

        async def mock_exec(device, command, timeout):
            if device.name == "R1":
                raise ConnectionError("Connection failed")
            return sample_config

        with patch("ensp_cli.services.config_exporter.execute_command", side_effect=mock_exec):
            results = await exporter.export_all_configs(output_dir, fmt="txt")

        assert len(results) == 2
        r1_result = [r for r in results if r["device"] == "R1"][0]
        r2_result = [r for r in results if r["device"] == "R2"][0]

        assert r1_result["success"] is False
        assert "Connection failed" in r1_result["error"]
        assert r2_result["success"] is True

    def test_create_metadata(self, sample_topology, sample_device):
        """Test metadata creation."""
        topo_path = Path("/path/to/test.topo")
        exporter = ConfigExporter(sample_topology, topo_path)
        metadata = exporter._create_metadata(sample_device)

        assert metadata["device"] == "R1"
        assert metadata["device_type"] == "Router"
        assert metadata["model"] == "AR2220"
        assert metadata["topology_name"] == "TestTopology"
        assert metadata["topology"] == str(topo_path)
        assert "exported_at" in metadata

        # Verify exported_at is a valid ISO timestamp
        datetime.fromisoformat(metadata["exported_at"])

    def test_format_txt(self, sample_topology, sample_config):
        """Test txt format generation."""
        exporter = ConfigExporter(sample_topology)
        metadata = exporter._create_metadata(
            Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        )
        content = exporter._format_txt(sample_config, metadata)

        assert "! Configuration Export" in content
        assert "! Device: R1" in content
        assert "! Type: Router" in content
        assert "! Model: AR2220" in content
        assert "sysname R1" in content

    def test_format_json(self, sample_topology, sample_config):
        """Test JSON format generation."""
        exporter = ConfigExporter(sample_topology)
        metadata = exporter._create_metadata(
            Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        )
        content = exporter._format_json(sample_config, metadata)

        data = json.loads(content)
        assert data["metadata"] == metadata
        assert data["configuration"] == sample_config

    def test_format_markdown(self, sample_topology, sample_config):
        """Test Markdown format generation."""
        exporter = ConfigExporter(sample_topology)
        metadata = exporter._create_metadata(
            Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        )
        content = exporter._format_markdown(sample_config, metadata)

        assert "# Configuration Export: R1" in content
        assert "## Metadata" in content
        assert "| Device |" in content
        assert "## Configuration" in content
        assert "```" in content

    def test_get_output_path_txt(self, sample_topology):
        """Test output path generation for txt format."""
        exporter = ConfigExporter(sample_topology)
        output_dir = Path("/backup")
        device = Device(name="Router1", device_type="Router", model="AR2220", console_port=2000)

        path = exporter._get_output_path(output_dir, device, "txt")
        assert path == Path("/backup/Router1.txt")

    def test_get_output_path_json(self, sample_topology):
        """Test output path generation for JSON format."""
        exporter = ConfigExporter(sample_topology)
        output_dir = Path("/backup")
        device = Device(name="Router1", device_type="Router", model="AR2220", console_port=2000)

        path = exporter._get_output_path(output_dir, device, "json")
        assert path == Path("/backup/Router1.json")


class TestExportFunctions:
    """Tests for the convenience export functions."""

    @pytest.mark.asyncio
    async def test_export_device_config_function(self, sample_device, sample_config, tmp_path):
        """Test the standalone export_device_config function."""
        output_path = tmp_path / "r1.cfg"

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            result = await export_device_config(sample_device, output_path, fmt="txt")

        assert result["success"] is True
        assert result["device"] == "R1"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_export_all_configs_function(self, sample_topology, sample_config, tmp_path):
        """Test the standalone export_all_configs function."""
        output_dir = tmp_path / "exports"

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = sample_config
            results = await export_all_configs(sample_topology, output_dir, fmt="txt")

        assert len(results) == 2
        assert all(r["success"] for r in results)


class TestErrorHandling:
    """Tests for error handling in config exporter."""

    @pytest.mark.asyncio
    async def test_connection_error(self, sample_device, sample_topology, tmp_path):
        """Test handling of connection errors."""
        output_path = tmp_path / "r1.cfg"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = ConnectionError("Failed to connect to device")

            with pytest.raises(ConnectionError, match="Failed to connect to device"):
                await exporter.export_device_config(sample_device, output_path)

    @pytest.mark.asyncio
    async def test_timeout_error(self, sample_device, sample_topology, tmp_path):
        """Test handling of timeout errors."""
        output_path = tmp_path / "r1.cfg"
        exporter = ConfigExporter(sample_topology)

        with patch("ensp_cli.services.config_exporter.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = asyncio.TimeoutError("Command timed out")

            with pytest.raises(asyncio.TimeoutError):
                await exporter.export_device_config(sample_device, output_path)


# Import asyncio for the test
import asyncio
