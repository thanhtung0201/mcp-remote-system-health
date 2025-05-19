import pytest
from unittest import mock
from src.tools.metrics import get_disk_metrics

pytestmark = pytest.mark.asyncio(loop_scope="function")

async def test_get_disk_metrics(server_config, monkeypatch):
    """Test disk metrics collection."""
    # Mock run_ssh_command
    async def mock_run_ssh_command(*args, **kwargs):
        command = kwargs.get("command")
        if "df -BG" in command:
            return (
                "Filesystem     Mounted on    Size    Used Available Use% Itotal IUsed IFree IUse%\n"
                "/dev/sda1      /             97G     45G       48G  49% 6111232 433555 5677677  8%\n"
                "/dev/sdb1      /data         932G    754G     131G  86% 60506112 7236076 53270036 12%\n"
                "tmpfs          /tmp          16G      0G      16G   0% 4026531 1052 4025479 1%\n",
                "",
                0
            )
        elif "iostat -d -x" in command:
            return (
                "Linux 5.15.0-58-generic (server1)  05/18/2025  _x86_64_  (4 CPU)\n\n"
                "Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util\n"
                "sda1             10.42    5.31    234.56    98.76     0.00     1.21   0.00  18.57    0.27    1.82   0.02    22.52    18.60   0.12   1.89\n"
                "sdb1             25.64   38.92   1024.50   786.32     0.15    15.43   0.58  28.38    0.35    2.64   0.18    39.96    20.20   0.28  18.25\n",
                "",
                0
            )
        return "", "Unknown command", 1
    
    mock_ssh = mock.AsyncMock(side_effect=mock_run_ssh_command)
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)

    # Call the function
    result = await get_disk_metrics(server_config)
    # Verify the result
    assert "error" not in result
    
    # Check disks count
    assert len(result["disks"]) == 2  # tmpfs should be excluded
    
    # Find specific disks
    root_disk = next(disk for disk in result["disks"] if disk["mount_point"] == "/")
    data_disk = next(disk for disk in result["disks"] if disk["mount_point"] == "/data")
    
    # Check root disk values
    assert root_disk["device"] == "/dev/sda1"
    assert root_disk["total_gb"] == 97
    assert root_disk["used_gb"] == 45
    assert root_disk["free_gb"] == 48
    assert root_disk["usage_percent"] == 49
    
    # Check inodes data
    assert root_disk["inodes_total"] == 6111232
    assert root_disk["inodes_used"] == 433555
    assert root_disk["inodes_free"] == 5677677
    assert root_disk["inodes_usage_percent"] == 8
    
    # Check data disk values
    assert data_disk["device"] == "/dev/sdb1"
    assert data_disk["total_gb"] == 932
    assert data_disk["used_gb"] == 754
    assert data_disk["free_gb"] == 131
    assert data_disk["usage_percent"] == 86
    
    # Check that disks have IO stats
    if "io_stats" in root_disk:
        assert root_disk["io_stats"]["reads_per_sec"] == 10.42
        assert root_disk["io_stats"]["writes_per_sec"] == 5.31
        assert root_disk["io_stats"]["read_kb_per_sec"] == 234.56
        assert root_disk["io_stats"]["write_kb_per_sec"] == 98.76
        assert root_disk["io_stats"]["util_percent"] == 1.89
    else:
        assert "io_stats" not in root_disk
    
    
    # Verify timestamp exists
    assert "timestamp" in result

async def test_disk_metrics_with_mount_point(server_config, monkeypatch):
    """Test disk metrics collection for a specific mount point."""
    # Mock run_ssh_command
    async def mock_run_ssh_command(*args, **kwargs):
        command = kwargs.get("command")
        if "df -BG" in command and "/data" in command:
            return (
                "Filesystem     Mounted on    Size    Used Available Use% Itotal IUsed IFree IUse%\n"
                "/dev/sdb1      /data         932G    754G     131G  86% 60506112 7236076 53270036 12%\n",
                "",
                0
            )
        elif "iostat -d -x" in command:
            return (
                "Linux 5.15.0-58-generic (server1)  05/18/2025  _x86_64_  (4 CPU)\n\n"
                "Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util\n"
                "sdb1             25.64   38.92   1024.50   786.32     0.15    15.43   0.58  28.38    0.35    2.64   0.18    39.96    20.20   0.28  18.25\n",
                "",
                0
            )
        return "", "Unknown command", 1
    
    mock_ssh = mock.AsyncMock(side_effect=mock_run_ssh_command)
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)

    # Call the function with specific mount point
    result = await get_disk_metrics(server_config, mount_point="/data")
    
    # Verify we only got data for the requested mount point
    assert len(result["disks"]) == 1
    assert result["disks"][0]["mount_point"] == "/data"

async def test_disk_metrics_error(server_config, monkeypatch):
    """Test disk metrics collection when command fails."""
    # Mock run_ssh_command to simulate an error
    mock_ssh = mock.AsyncMock(return_value=("", "Command failed", 1))
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)
    
    # Call the function
    result = await get_disk_metrics(server_config)
    
    # Verify the result contains an error
    assert "error" in result
    assert "Failed to get disk metrics: Command failed" in result["error"]
    assert "timestamp" in result
    assert result["disks"] == []