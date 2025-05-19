"""
conftest.py - Common fixtures for MCP System Health Monitoring tests

This file contains fixtures used across all test modules to simplify setup,
facilitate mocking, and provide consistent test data.
"""

import os
import asyncio
from pathlib import Path
import tempfile
import json
import sys
import pytest
from unittest import mock
from typing import Dict, List, Any, Optional, Tuple

# Add the project root directory to Python's path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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