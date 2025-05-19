import pytest
from unittest import mock
from src.tools.metrics import get_memory_metrics

pytestmark = pytest.mark.asyncio(loop_scope="function")

async def test_get_memory_metrics(server_config, monkeypatch):
    """Test memory metrics collection."""
    # Mock run_ssh_command
    async def mock_run_ssh_command(*args, **kwargs):
        command = kwargs.get("command")
        if "free -b" in command:
            return (
                "              total        used        free      shared  buff/cache   available\n"
                "Mem:     17180000000  8000000000  2000000000   500000000  6000000000  7500000000\n"
                "Swap:     8000000000   500000000  7500000000\n",
                "",
                0
            )
        return "", "Unknown command", 1
    
    mock_ssh = mock.AsyncMock(side_effect=mock_run_ssh_command)
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)

    # Call the function
    result = await get_memory_metrics(server_config)
    # Verify the result
    assert "error" not in result
    
    # Check memory metrics
    gb_conversion = 1024 * 1024 * 1024
    print(round(7500000000/gb_conversion, 2))
    assert result["total_gb"] == 16.0
    assert result["used_gb"] == 7.45  # Convert bytes to GB
    assert result["free_gb"] == 1.86  # Convert bytes to GB
    assert result["available_gb"] == 6.98 # Convert bytes to GB
    assert result["cached_gb"] == 6.98
    assert result["buffers_gb"] == 5.59

    # Check calculated metrics
    assert result["usage_percent"] == 46.6
    assert result["available_percent"] == 43.7
    assert result["swap_usage_percent"] == 6.2

    # Check swap metrics
    assert result["swap_total_gb"] == 7.45
    assert result["swap_used_gb"] == 0.47
    assert result["swap_free_gb"] == 6.98

    # Verify timestamp exists
    assert "timestamp" in result
    
    # Verify the mock was called with the right command
    mock_ssh.assert_called_once_with(
        config=server_config,
        command="free -b"
    )

async def test_memory_metrics_error(server_config, monkeypatch):
    """Test memory metrics collection when command fails."""
    # Mock run_ssh_command to simulate an error
    mock_ssh = mock.AsyncMock(return_value=("", "Command failed", 1))
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)
    
    # Call the function
    result = await get_memory_metrics(server_config)
    
    # Verify the result contains an error
    assert "error" in result
    assert "Command failed" in result["error"]
    assert "timestamp" in result
    
        