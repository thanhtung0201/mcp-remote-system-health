import pytest
from unittest import mock
from src.tools.metrics import get_network_metrics

pytestmark = pytest.mark.asyncio(loop_scope="function")

async def test_get_network_metrics(server_config, monkeypatch):
    """Test network metrics collection."""
    # Mock run_ssh_command
    async def mock_run_ssh_command(*args, **kwargs):
        command = kwargs.get("command")
        if "cat /proc/net/dev" in command:
            return (
                "Inter-|   Receive                                                |  Transmit\n"
                " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
                "    lo: 1500000000   12345    0    0    0     0          0         0 1500000000   12345    0    0    0     0       0          0\n"
                "  eth0: 8000000000  100000    0    0    0     0          0         0 4000000000   75000    0    0    0     0       0          0\n"
                "  eth1: 3000000000   50000    0    0    0     0          0         0 1500000000   25000    0    0    0     0       0          0\n",
                "",
                0
            )
        elif "ip -s link" in command:
            return (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "    RX: bytes  packets  errors  dropped overrun mcast\n"
                "    1500000000 12345    0       0       0       0\n"
                "    TX: bytes  packets  errors  dropped carrier collsns\n"
                "    1500000000 12345    0       0       0       0\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000\n"
                "    link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff\n"
                "    RX: bytes  packets  errors  dropped overrun mcast\n"
                "    8000000000 100000   0       0       0       0\n"
                "    TX: bytes  packets  errors  dropped carrier collsns\n"
                "    4000000000 75000    0       0       0       0\n"
                "3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000\n"
                "    link/ether 00:11:22:33:44:56 brd ff:ff:ff:ff:ff:ff\n"
                "    RX: bytes  packets  errors  dropped overrun mcast\n"
                "    3000000000 50000    0       0       0       0\n"
                "    TX: bytes  packets  errors  dropped carrier collsns\n"
                "    1500000000 25000    0       0       0       0\n",
                "",
                0
            )
        elif "ss -tuln" in command:
            return (
                "Netid  State   Recv-Q  Send-Q   Local Address:Port   Peer Address:Port  Process\n"
                "udp    UNCONN  0       0              0.0.0.0:68          0.0.0.0:*\n"
                "tcp    LISTEN  0       128            0.0.0.0:22          0.0.0.0:*\n"
                "tcp    LISTEN  0       128          127.0.0.1:631         0.0.0.0:*\n"
                "tcp    LISTEN  0       128            0.0.0.0:80          0.0.0.0:*\n"
                "tcp    LISTEN  0       128               [::]:22             [::]:*\n",
                "",
                0
            )
        return "", "Unknown command", 1
    
    mock_ssh = mock.AsyncMock(side_effect=mock_run_ssh_command)
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)

    # Call the function
    result = await get_network_metrics(server_config)
    
    # Verify the result
    assert "error" not in result
    
    # Check interfaces list
    assert len(result["interfaces"]) == 2
    
    # Check specific interface data
    eth0 = next(iface for iface in result["interfaces"] if iface["interface"] == "eth0")

    assert eth0["rx_bytes"] == 8000000000
    assert eth0["tx_bytes"] == 4000000000
    assert eth0["rx_packets"] == 100000
    assert eth0["tx_packets"] == 75000
    assert eth0["rx_errors"] == 0
    assert eth0["tx_errors"] == 0
    
    
    # Verify timestamp exists
    assert "timestamp" in result

async def test_network_metrics_error(server_config, monkeypatch):
    """Test network metrics collection when command fails."""
    # Mock run_ssh_command to simulate an error
    mock_ssh = mock.AsyncMock(return_value=("", "Command failed", 1))
    monkeypatch.setattr("src.tools.metrics.run_ssh_command", mock_ssh)
    
    # Call the function
    result = await get_network_metrics(server_config)
    
    # Verify the result contains an error
    assert "error" in result
    assert "Command failed" in result["error"]
    assert "timestamp" in result