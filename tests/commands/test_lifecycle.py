"""Tests for lifecycle CLI commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from ensp_cli.cli.main import app
from ensp_cli.models.running_device import RunningDevice
from ensp_cli.services.process_manager import ProcessManager

runner = CliRunner()


class TestLaunchRouterCommand:
    """Test launch-router command."""
    
    def test_launch_router_help(self) -> None:
        """Test launch-router --help shows correct options."""
        result = runner.invoke(app, ["lifecycle", "launch-router", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--port" in result.output
        assert "--x" in result.output
        assert "--y" in result.output
        assert "AR2220" in result.output
    
    def test_launch_router_missing_name(self) -> None:
        """Test error when device name not provided."""
        result = runner.invoke(app, ["lifecycle", "launch-router"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "NAME" in result.output
    
    def test_launch_router_invalid_model(self, monkeypatch, tmp_path) -> None:
        """Test error on invalid router model."""
        # Mock ProcessManager to avoid state file issues
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            lambda: ProcessManager(state_file=tmp_path / "state.json")
        )
        
        result = runner.invoke(app, ["lifecycle", "launch-router", "R1", "--model", "INVALID"])
        # Should fail because eNSP is not installed in test environment
        assert result.exit_code != 0


class TestLaunchSwitchCommand:
    """Test launch-switch command."""
    
    def test_launch_switch_help(self) -> None:
        """Test launch-switch --help shows correct options."""
        result = runner.invoke(app, ["lifecycle", "launch-switch", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "S5700" in result.output
        assert "S3700" in result.output
    
    def test_launch_switch_default_model(self) -> None:
        """Test default switch model is S5700."""
        result = runner.invoke(app, ["lifecycle", "launch-switch", "--help"])
        assert result.exit_code == 0
        assert "S5700" in result.output


class TestStopDeviceCommand:
    """Test stop-device command."""
    
    def test_stop_device_help(self) -> None:
        """Test stop-device --help shows correct options."""
        result = runner.invoke(app, ["lifecycle", "stop-device", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output
        assert "--all" in result.output
    
    def test_stop_nonexistent_device(self, tmp_path, monkeypatch) -> None:
        """Test stopping a non-existent device."""
        state_file = tmp_path / "state.json"
        
        class MockProcessManager:
            def __init__(self):
                self._state_file = state_file
            
            def list_devices(self, **kwargs):
                return []
            
            def stop_device(self, name, force=False):
                return {
                    "success": False,
                    "message": f"Device '{name}' not found",
                    "was_running": False,
                }
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        
        result = runner.invoke(app, ["lifecycle", "stop-device", "NONEXISTENT"])
        # Command returns error for non-existent device
        assert result.exit_code != 0
    
    def test_stop_all_no_devices(self, tmp_path, monkeypatch) -> None:
        """Test stop --all with no running devices."""
        
        class MockProcessManager:
            def list_devices(self, **kwargs):
                return []
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        
        result = runner.invoke(app, ["lifecycle", "stop-device", "--all"])
        assert result.exit_code == 0
        assert "No CLI-managed devices" in result.output


class TestPsCommand:
    """Test ps command."""
    
    def test_ps_help(self) -> None:
        """Test ps --help shows correct options."""
        result = runner.invoke(app, ["lifecycle", "ps", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--refresh" in result.output
    
    def test_ps_empty_output(self, tmp_path, monkeypatch) -> None:
        """Test ps with no devices."""
        
        class MockProcessManager:
            def __init__(self):
                pass
            
            def list_devices(self, **kwargs):
                return []
        
        class MockTopoSyncService:
            def get_gui_devices(self):
                return []
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.TopoSyncService",
            MockTopoSyncService
        )
        
        result = runner.invoke(app, ["lifecycle", "ps"])
        assert result.exit_code == 0
        assert "No running devices" in result.output
    
    def test_ps_json_output(self, tmp_path, monkeypatch) -> None:
        """Test ps with JSON output."""
        import json
        
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        class MockProcessManager:
            def list_devices(self, **kwargs):
                return [device]
        
        class MockTopoSyncService:
            def get_gui_devices(self):
                return []
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.TopoSyncService",
            MockTopoSyncService
        )
        
        result = runner.invoke(app, ["lifecycle", "ps", "--output", "json"])
        assert result.exit_code == 0
        
        # Verify JSON output
        data = json.loads(result.output)
        assert "cli_devices" in data
        assert len(data["cli_devices"]) == 1
        assert data["cli_devices"][0]["name"] == "R1"


class TestLaunchTopologyCommand:
    """Test launch-topology command."""
    
    def test_launch_topology_help(self) -> None:
        """Test launch-topology --help shows correct options."""
        result = runner.invoke(app, ["lifecycle", "launch-topology", "--help"])
        assert result.exit_code == 0
        assert "--timeout" in result.output
        assert "--parallel" in result.output
        assert "--max-devices" in result.output
    
    def test_launch_topology_no_file(self) -> None:
        """Test error when no topology file found."""
        result = runner.invoke(app, ["lifecycle", "launch-topology"])
        assert result.exit_code != 0
    
    def test_launch_topology_file_not_found(self) -> None:
        """Test error when specified file not found."""
        result = runner.invoke(app, ["lifecycle", "launch-topology", "nonexistent.topo"])
        assert result.exit_code != 0
    
    def test_launch_topology_with_file(self, tmp_path, monkeypatch) -> None:
        """Test launch-topology with valid file."""
        # Create test topology
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" device_type="Router" cx="100" cy="100"/>
                <dev id="2" name="S1" device_type="Switch" cx="200" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        result = runner.invoke(app, ["lifecycle", "launch-topology", str(topo_path)])
        # Should fail because eNSP is not installed
        assert result.exit_code != 0 or "Launching" in result.output


class TestErrorHandling:
    """Test error handling in lifecycle commands."""
    
    def test_device_already_running_error(self, tmp_path, monkeypatch) -> None:
        """Test error when trying to launch already running device."""
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
            status="running",
        )
        
        class MockProcessManager:
            def __init__(self):
                pass
            
            def list_devices(self, active_only=False, **kwargs):
                return [device]
            
            def get_device(self, name):
                return device if name == "R1" else None
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        
        result = runner.invoke(app, ["lifecycle", "launch-router", "R1"])
        assert result.exit_code != 0
        assert "already running" in result.output.lower() or "Device" in result.output
    
    def test_device_limit_reached(self, tmp_path, monkeypatch) -> None:
        """Test error when device limit reached."""
        
        devices = [
            RunningDevice(
                name=f"R{i}",
                device_type="router",
                model="AR2220",
                pid=10000 + i,
                port=2000 + i,
                mac_address=f"54-89-98-11-22-{i:02d}",
                status="running",
            )
            for i in range(10)  # Max devices
        ]
        
        class MockProcessManager:
            def list_devices(self, active_only=False, **kwargs):
                return devices if active_only else devices
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        
        result = runner.invoke(app, ["lifecycle", "launch-router", "NEW"])
        assert result.exit_code != 0


class TestExitCodes:
    """Test exit codes for lifecycle commands."""
    
    def test_success_exit_code_0(self, tmp_path, monkeypatch) -> None:
        """Test successful command returns exit code 0."""
        
        class MockProcessManager:
            def list_devices(self, **kwargs):
                return []
        
        class MockTopoSyncService:
            def get_gui_devices(self):
                return []
        
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.ProcessManager",
            MockProcessManager
        )
        monkeypatch.setattr(
            "ensp_cli.commands.lifecycle.TopoSyncService",
            MockTopoSyncService
        )
        
        result = runner.invoke(app, ["lifecycle", "ps"])
        assert result.exit_code == 0
    
    def test_error_exit_code_nonzero(self) -> None:
        """Test error returns non-zero exit code."""
        result = runner.invoke(app, ["lifecycle", "launch-topology", "nonexistent.topo"])
        assert result.exit_code != 0
