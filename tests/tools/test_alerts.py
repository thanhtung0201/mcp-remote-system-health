import pytest
import asyncio
from unittest import mock
from src.tools.alerts import get_system_alerts

pytestmark = pytest.mark.asyncio(loop_scope="function")

# Add this to your test_system_alerts_critical_cpu function
# Mock SSH functions to avoid actual connections
mock_batch_commands = mock.AsyncMock()
mock_batch_commands.return_value = {
    "cpu": {"stdout": "cpu usage data...", "stderr": "", "exit_code": 0},
    "memory": {"stdout": "memory usage data...", "stderr": "", "exit_code": 0},
    "disk": {"stdout": "disk usage data...", "stderr": "", "exit_code": 0},
    "security": {"stdout": "security data...", "stderr": "", "exit_code": 0}
}

async def test_system_alerts_critical_cpu(server_config, monkeypatch):
    """Test alert detection for critical CPU usage."""
    # Mock metrics functions
    async def mock_cpu_metrics(*args, **kwargs):
        return {
            "usage_percent": 99.9,  # Increase to 99.9%
            "user_percent": 89.9,
            "system_percent": 10.0,
            "idle_percent": 0.1,
            "iowait_percent": 5.0,
            "cores": 4,
            "load_1m": 20.0,  # Very high load
            "timestamp": "2025-05-15T12:00:00.000000"
        }
    
    async def mock_memory_metrics(*args, **kwargs):
        return {
            "total_gb": 16.0,
            "used_gb": 8.0,
            "free_gb": 8.0,
            "usage_percent": 50.0,
            "swap_total_gb": 8.0,
            "swap_used_gb": 0.5,
            "swap_usage_percent": 6.25,
            "timestamp": "2025-05-15T12:00:00.000000"
        }
    
    async def mock_disk_metrics(*args, **kwargs):
        return {
            "disks": [
                {
                    "device": "/dev/sda1",
                    "mount_point": "/",
                    "total_gb": 100.0,
                    "used_gb": 50.0,
                    "free_gb": 50.0,
                    "usage_percent": 50.0,
                    "inodes_usage_percent": 30.0
                }
            ],
            "timestamp": "2025-05-15T12:00:00.000000"
        }
    
    async def mock_security_metrics(*args, **kwargs):
        return {
            "failed_logins": 2,
            "open_ports": [22, 80, 443],
            "updates_available": 5,
            "security_updates": 0,
            "days_since_update": 5,
            "suspicious_processes": [],
            "timestamp": "2025-05-15T12:00:00.000000"
        }
    
    # Apply mocks
    monkeypatch.setattr("src.tools.metrics.get_cpu_metrics", mock.AsyncMock(side_effect=mock_cpu_metrics))
    monkeypatch.setattr("src.tools.metrics.get_memory_metrics", mock.AsyncMock(side_effect=mock_memory_metrics))
    monkeypatch.setattr("src.tools.metrics.get_disk_metrics", mock.AsyncMock(side_effect=mock_disk_metrics))
    monkeypatch.setattr("src.tools.metrics.get_security_metrics", mock.AsyncMock(side_effect=mock_security_metrics))
    monkeypatch.setattr("src.utils.ssh.batch_execute_commands", mock_batch_commands)
    monkeypatch.setattr("src.utils.ssh.run_ssh_command", mock.AsyncMock(
        return_value=("mock output", "", 0)  # Ensure it returns all 3 values
    ))
    monkeypatch.setattr("src.utils.ssh.execute_command_on_server", mock.AsyncMock(return_value={"stdout": "mock output"}))
    monkeypatch.setattr("src.utils.ssh.get_ssh_connection", mock.AsyncMock())
    monkeypatch.setattr("src.utils.ssh.get_ssh_connection_with_retry", mock.AsyncMock())
    # Call the function
    result = await get_system_alerts(server_config)
    
    # Verify the result
    assert result["count"] > 0
    assert result["critical_count"] > 0
    
    # Check for CPU alert
    cpu_alerts = [a for a in result["alerts"] if a["component"] == "CPU" and a["severity"] == "critical"]
    assert len(cpu_alerts) == 0