"""
conftest.py - Common fixtures for MCP System Health Monitoring tests

This file contains fixtures used across all test modules to simplify setup,
facilitate mocking, and provide consistent test data.
"""

import os
import asyncio
import tempfile
import json
import pytest
from unittest import mock
from typing import Dict, List, Any, Optional, Tuple

def pytest_configure(config):
    """Configure pytest options."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as using asyncio"
    )
    
    # Add this line to set the default fixture loop scope
    config.option.asyncio_default_fixture_loop_scope = "function"

@pytest.fixture
def server_config():
    """Return a sample server configuration for testing."""
    return {
        "hostname": "test-server",
        "ip": "192.168.1.100",
        "ssh_port": 22,
        "username": "testuser",
        "key_path": "/path/to/test_key",
        "password": None
    }

@pytest.fixture
def sample_server_configs():
    """Provide multiple sample server configurations for testing"""
    return [
        {
            "hostname": "test-server-1",
            "ip": "192.168.1.101",
            "ssh_port": 22,
            "username": "testuser",
            "key_path": "~/.ssh/id_rsa"
        },
        {
            "hostname": "test-server-2",
            "ip": "192.168.1.102",
            "ssh_port": 22,
            "username": "testuser",
            "key_path": "~/.ssh/id_rsa"
        },
        {
            "hostname": "test-server-3",
            "ip": "192.168.1.103",
            "ssh_port": 22,
            "username": "testuser",
            "key_path": "~/.ssh/id_rsa"
        }
    ]

@pytest.fixture
def mock_ssh_connection():
    """Create a mock SSH connection for testing"""
    conn = mock.AsyncMock()
    conn.is_closed.return_value = False
    
    # Mock run method to return sample outputs
    async def mock_run(command, check=False):
        result = mock.AsyncMock()
        
        # Sample responses for different commands
        if "top -bn1" in command:
            result.stdout = "%Cpu(s): 10.0 us, 5.0 sy, 0.0 ni, 80.0 id, 5.0 wa"
            result.stderr = ""
            result.exit_status = 0
        elif "free -b" in command:
            result.stdout = "              total        used        free      shared  buff/cache   available\n"\
                           "Mem:     8273289216  3975233536  1525145600   535805952  2772909080  3361726464\n"\
                           "Swap:    2147483648    75497472  2071986176"
            result.stderr = ""
            result.exit_status = 0
        elif "df -BG" in command:
            result.stdout = "Filesystem     1G-blocks  Used Available Use% Mounted on\n"\
                           "/dev/sda1            98G   45G       48G  48% /\n"\
                           "/dev/sdb1           932G  750G      135G  85% /data"
            result.stderr = ""
            result.exit_status = 0
        elif "cat /proc/loadavg" in command:
            result.stdout = "0.52 0.58 0.59 1/1250 24816"
            result.stderr = ""
            result.exit_status = 0
        elif "nproc" in command:
            result.stdout = "4"
            result.stderr = ""
            result.exit_status = 0
        elif "cat /proc/uptime" in command:
            result.stdout = "1234567.89 1234567.89"
            result.stderr = ""
            result.exit_status = 0
        elif "uname -r" in command:
            result.stdout = "5.15.0-1032-aws"
            result.stderr = ""
            result.exit_status = 0
        elif "hostname" in command:
            result.stdout = "test-server"
            result.stderr = ""
            result.exit_status = 0
        elif "cat /etc/os-release" in command:
            result.stdout = 'NAME="Ubuntu"\nVERSION="22.04.1 LTS (Jammy Jellyfish)"\nID=ubuntu\nPRETTY_NAME="Ubuntu 22.04.1 LTS"'
            result.stderr = ""
            result.exit_status = 0
        elif "ps aux" in command:
            result.stdout = "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"\
                          "root      1234  5.0  2.0 125000 40000 ?        Ss   May10   2:30 /usr/sbin/sshd\n"\
                          "user      2345  4.0  1.5  98000 30000 ?        S    May10   1:45 /usr/bin/python3\n"\
                          "www-data  3456  3.0  1.0  85000 20000 ?        S    May10   1:10 /usr/sbin/apache2"
            result.stderr = ""
            result.exit_status = 0
        elif "cat /proc/net/dev" in command:
            result.stdout = "Inter-|   Receive                                                |  Transmit\n"\
                          " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"\
                          "    lo: 1000000     100    0    0    0     0          0         0  1000000     100    0    0    0     0       0          0\n"\
                          "  eth0: 5000000     500    0    0    0     0          0         0  3000000     300    0    0    0     0       0          0"
            result.stderr = ""
            result.exit_status = 0
        elif "grep -c 'Failed password'" in command:
            result.stdout = "12"
            result.stderr = ""
            result.exit_status = 0
        elif "ss -tuln" in command:
            result.stdout = "Netid   State    Recv-Q   Send-Q     Local Address:Port      Peer Address:Port   Process\n"\
                          "tcp     LISTEN   0        128          0.0.0.0:22             0.0.0.0:*\n"\
                          "tcp     LISTEN   0        128          0.0.0.0:80             0.0.0.0:*\n"\
                          "tcp     LISTEN   0        128          0.0.0.0:443            0.0.0.0:*"
            result.stderr = ""
            result.exit_status = 0
        elif "apt list --upgradable" in command:
            result.stdout = "Listing...\n"\
                          "python3/jammy-updates 3.10.4-0ubuntu2.1 amd64 [upgradable from: 3.10.4-0ubuntu2]\n"\
                          "openssh-server/jammy-security 1:8.9p1-3ubuntu0.1 amd64 [upgradable from: 1:8.9p1-3]"
            result.stderr = ""
            result.exit_status = 0
        elif "who | wc -l" in command:
            result.stdout = "3"
            result.stderr = ""
            result.exit_status = 0
        elif "test -f /var/run/reboot-required" in command:
            result.stdout = "false"
            result.stderr = ""
            result.exit_status = 0
        elif "dmesg" in command:
            result.stdout = "[    0.000000] ACPI: RSDP 0x00000000000F6B60 000024 (v02 INTEL )\n"\
                          "[    0.000000] ACPI: XSDT 0x00000000000F6C40 00005C (v01 INTEL  440BX    06040000 LOHR 0000005A)\n"\
                          "[    1.234567] EXT4-fs (sda1): mounted filesystem with ordered data mode. Opts: (null)"
            result.stderr = ""
            result.exit_status = 0
        elif "iostat" in command:
            result.stdout = "Linux 5.15.0-1032-aws (test-server) 	05/15/25 	_x86_64_	(4 CPU)\n\n"\
                          "Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util\n"\
                          "sda              5.00    3.00     50.00     30.00     0.00     0.00   0.00   0.00    1.20    1.40   0.00    10.00    10.00   0.20   5.00\n"\
                          "sdb              2.00    8.00     20.00     80.00     0.00     0.00   0.00   0.00    1.10    1.30   0.00    10.00    10.00   0.50  12.00"
            result.stderr = ""
            result.exit_status = 0
        else:
            # Default response for unhandled commands
            result.stdout = f"Sample output for: {command}"
            result.stderr = ""
            result.exit_status = 0
            
        return result
    
    conn.run.side_effect = mock_run
    return conn

@pytest.fixture
def mock_failed_ssh_connection():
    """Create a mock SSH connection that simulates failures"""
    conn = mock.AsyncMock()
    conn.is_closed.return_value = False
    
    # Mock run method to return errors
    async def mock_run(command, check=False):
        result = mock.AsyncMock()
        result.stdout = ""
        result.stderr = "Connection failed: Connection refused"
        result.exit_status = 255
        return result
    
    conn.run.side_effect = mock_run
    return conn

@pytest.fixture
def mock_execute_command_on_server(mock_ssh_connection):
    """Mock execute_command_on_server function for testing"""
    async def mock_execute(config, command, reuse_connection=True):
        if "error" in config:
            # Simulate an error if the config has an "error" key
            return "", f"Failed to execute command: {config['error']}", 1
            
        # Use the mock SSH connection to get the command output
        result = await mock_ssh_connection.run(command)
        return result.stdout, result.stderr, result.exit_status
        
    return mock_execute

@pytest.fixture
def mock_batch_execute_commands(mock_ssh_connection):
    """Mock batch_execute_commands function for testing"""
    async def mock_batch(config, commands):
        if "error" in config:
            # Simulate an error if the config has an "error" key
            raise RuntimeError(f"Failed to execute batch commands: {config['error']}")
            
        # Execute each command and collect results
        results = []
        for command in commands:
            result = await mock_ssh_connection.run(command)
            results.append(result.stdout)
            
        return results
        
    return mock_batch

@pytest.fixture
def temp_server_configs():
    """Create temporary server configuration files for testing"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="mcp_test_configs_")
    configs = []
    
    # Create sample configs
    for i in range(3):
        config = {
            "hostname": f"test-server-{i+1}",
            "ip": f"192.168.1.{101+i}",
            "ssh_port": 22,
            "username": "testuser",
            "key_path": "~/.ssh/id_rsa"
        }
        
        # Write config to file
        config_path = os.path.join(temp_dir, f"server{i+1}.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        configs.append(config)
    
    yield temp_dir, configs
    
    # Clean up
    for i in range(3):
        os.remove(os.path.join(temp_dir, f"server{i+1}.json"))
    os.rmdir(temp_dir)

@pytest.fixture
def sample_cpu_metrics():
    """Sample CPU metrics for testing"""
    return {
        "usage_percent": 20.0,
        "user_percent": 10.0,
        "system_percent": 5.0,
        "idle_percent": 80.0,
        "iowait_percent": 5.0,
        "cores": 4,
        "load_1m": 0.52,
        "load_5m": 0.58,
        "load_15m": 0.59,
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_memory_metrics():
    """Sample memory metrics for testing"""
    return {
        "total_gb": 8.0,
        "used_gb": 4.0,
        "free_gb": 1.5,
        "available_gb": 3.0,
        "cached_gb": 2.5,
        "buffers_gb": 0.5,
        "usage_percent": 50.0,
        "available_percent": 37.5,
        "swap_total_gb": 2.0,
        "swap_used_gb": 0.1,
        "swap_free_gb": 1.9,
        "swap_usage_percent": 5.0,
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_disk_metrics():
    """Sample disk metrics for testing"""
    return {
        "disks": [
            {
                "device": "/dev/sda1",
                "mount_point": "/",
                "total_gb": 100.0,
                "used_gb": 50.0,
                "free_gb": 50.0,
                "usage_percent": 50.0,
                "inodes_total": 10000000,
                "inodes_used": 1000000,
                "inodes_free": 9000000,
                "inodes_usage_percent": 10.0
            },
            {
                "device": "/dev/sdb1",
                "mount_point": "/data",
                "total_gb": 1000.0,
                "used_gb": 800.0,
                "free_gb": 200.0,
                "usage_percent": 80.0,
                "inodes_total": 20000000,
                "inodes_used": 5000000,
                "inodes_free": 15000000,
                "inodes_usage_percent": 25.0
            }
        ],
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_network_metrics():
    """Sample network metrics for testing"""
    return {
        "interfaces": [
            {
                "interface": "eth0",
                "rx_bytes": 5000000,
                "tx_bytes": 3000000,
                "rx_mb": 4.77,
                "tx_mb": 2.86,
                "rx_packets": 500,
                "tx_packets": 300,
                "rx_errors": 0,
                "tx_errors": 0,
                "rx_dropped": 0,
                "tx_dropped": 0
            }
        ],
        "connections": {
            "tcp_total": 12,
            "tcp_established": 5
        },
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_security_metrics():
    """Sample security metrics for testing"""
    return {
        "failed_logins": 12,
        "open_ports": [22, 80, 443],
        "updates_available": 5,
        "security_updates": 2,
        "days_since_update": 15,
        "suspicious_processes": [],
        "recent_auth_failures": [
            "May 15 10:15:23 test-server sshd[12345]: Failed password for invalid user admin from 192.168.1.200 port 54321 ssh2",
            "May 15 10:15:26 test-server sshd[12346]: Failed password for invalid user root from 192.168.1.200 port 54322 ssh2"
        ],
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_process_list():
    """Sample process list for testing"""
    return {
        "processes": [
            {
                "user": "root",
                "pid": 1234,
                "cpu_percent": 5.0,
                "memory_percent": 2.0,
                "virtual_size": 125000,
                "resident_size": 40000,
                "tty": "?",
                "state": "Ss",
                "start_time": "May10",
                "time": "2:30",
                "command": "/usr/sbin/sshd"
            },
            {
                "user": "user",
                "pid": 2345,
                "cpu_percent": 4.0,
                "memory_percent": 1.5,
                "virtual_size": 98000,
                "resident_size": 30000,
                "tty": "?",
                "state": "S",
                "start_time": "May10",
                "time": "1:45",
                "command": "/usr/bin/python3"
            },
            {
                "user": "www-data",
                "pid": 3456,
                "cpu_percent": 3.0,
                "memory_percent": 1.0,
                "virtual_size": 85000,
                "resident_size": 20000,
                "tty": "?",
                "state": "S",
                "start_time": "May10",
                "time": "1:10",
                "command": "/usr/sbin/apache2"
            }
        ],
        "count": 3,
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_system_alerts():
    """Sample system alerts for testing"""
    return {
        "alerts": [
            {
                "component": "Disk",
                "severity": "warning",
                "message": "High disk usage on /data: 80.0%",
                "details": {
                    "device": "/dev/sdb1",
                    "mount_point": "/data",
                    "usage_percent": 80.0,
                    "free_gb": 200.0,
                    "total_gb": 1000.0
                }
            },
            {
                "component": "Security",
                "severity": "warning",
                "message": "12 failed login attempts",
                "details": {
                    "failed_logins": 12
                }
            }
        ],
        "count": 2,
        "critical_count": 0,
        "warning_count": 2,
        "info_count": 0,
        "timestamp": "2025-05-15T12:00:00.000000"
    }

@pytest.fixture
def sample_health_summary():
    """Sample health summary for testing"""
    return {
        "server": "192.168.1.100",
        "hostname": "test-server",
        "overall_status": "warning",
        "uptime": "14d 6h 56m",
        "os_info": "Ubuntu 22.04.1 LTS",
        "kernel": "5.15.0-1032-aws",
        "metrics": {
            "cpu": {
                "usage_percent": 20.0,
                "load_1m": 0.52,
                "cores": 4
            },
            "memory": {
                "usage_percent": 50.0,
                "free_gb": 1.5,
                "total_gb": 8.0
            },
            "swap": {
                "usage_percent": 5.0,
                "total_gb": 2.0
            },
            "disk": [
                {
                    "mount_point": "/",
                    "usage_percent": 50.0,
                    "free_gb": 50.0,
                    "total_gb": 100.0
                },
                {
                    "mount_point": "/data",
                    "usage_percent": 80.0,
                    "free_gb": 200.0,
                    "total_gb": 1000.0
                }
            ]
        },
        "top_processes": [
            {
                "name": "/usr/sbin/sshd",
                "cpu_percent": 5.0,
                "memory_percent": 2.0,
                "pid": 1234,
                "user": "root"
            },
            {
                "name": "/usr/bin/python3",
                "cpu_percent": 4.0,
                "memory_percent": 1.5,
                "pid": 2345,
                "user": "user"
            },
            {
                "name": "/usr/sbin/apache2",
                "cpu_percent": 3.0,
                "memory_percent": 1.0,
                "pid": 3456,
                "user": "www-data"
            }
        ],
        "alerts": {
            "critical_count": 0,
            "warning_count": 2,
            "total_count": 2,
            "items": [
                {
                    "severity": "warning",
                    "component": "Disk",
                    "message": "High disk usage on /data: 80.0%"
                },
                {
                    "severity": "warning",
                    "component": "Security",
                    "message": "12 failed login attempts"
                }
            ]
        },
        "timestamp": "2025-05-15T12:00:00.000000"
    }