import pytest
import asyncio
from unittest import mock
from src.tools.metrics import get_cpu_metrics

pytestmark = pytest.mark.asyncio(loop_scope="function")

async def test_get_cpu_metrics(server_config, monkeypatch):
    """Test CPU metrics collection."""
    # Mock execute_command_on_server
    async def mock_execute(*args, **kwargs):
        command = kwargs.get("command")
        if "top -bn1" in command:
            return "%Cpu(s): 10.0 us, 5.0 sy, 0.0 ni, 80.0 id, 5.0 wa", "", 0
        elif "cat /proc/loadavg" in command:
            return "0.52 0.58 0.59 1/1250 24816", "", 0
        elif "nproc" in command:
            return "4", "", 0
        return "", "Unknown command", 1
    
    mock_exec = mock.AsyncMock(side_effect=mock_execute)
    monkeypatch.setattr("src.tools.metrics.execute_command_on_server", mock_exec)
    
    # Call the function
    result = await get_cpu_metrics(server_config)
    
    # Verify the result
    assert "error" not in result
    assert result["usage_percent"] == 20.0  # 100 - 80.0 idle
    assert result["user_percent"] == 10.0
    assert result["system_percent"] == 5.0
    assert result["iowait_percent"] == 5.0
    assert result["cores"] == 4
    assert result["load_1m"] == 0.52
    assert result["load_5m"] == 0.58
    assert result["load_15m"] == 0.59
    assert "timestamp" in result