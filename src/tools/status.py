"""
Status Tool Module

Provides system status information for servers.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from src.utils.ssh import run_ssh_command

logger = logging.getLogger(__name__)

async def get_system_status(config: dict) -> Dict[str, Any]:
    """
    Asynchronously retrieves and summarizes the system status of a remote server via SSH.
    This function gathers various system metrics and status indicators by executing commands over SSH,
    including uptime, kernel version, load averages, logged-in user count, recent kernel messages,
    reboot requirements, hostname, and operating system information. The collected data is parsed and
    returned in a structured dictionary.
    Args:
        config (dict): SSH connection configuration containing at least the target server's IP or hostname,
            and authentication details.
    Returns:
        Dict[str, Any]: A dictionary containing:
            - server (str): The server's IP or hostname.
            - hostname (str): The system's hostname.
            - status (str): System status, one of "online", "recently_rebooted", "reboot_pending", or "high_load".
            - uptime_seconds (int): System uptime in seconds.
            - uptime_human (str): Human-readable uptime (e.g., "1d 2h 3m").
            - kernel_version (str): The running kernel version.
            - os_name (str): Operating system name.
            - os_version (str): Operating system version.
            - load_average (dict): Load averages for 1, 5, and 15 minutes.
            - logged_in_users (int): Number of currently logged-in users.
            - reboot_pending (bool): Whether a reboot is pending for updates.
            - recent_issues (list): Recent kernel messages indicating errors, warnings, or failures.
            - timestamp (str): ISO-formatted timestamp of when the status was collected.
    Raises:
        Any exceptions raised by the underlying SSH command execution or parsing logic.
    """
    
    # Get uptime
    uptime_output, _, _ = await run_ssh_command(
        config=config,
        command="cat /proc/uptime"
    )
    
    uptime_seconds = 0
    if uptime_output and not uptime_output.startswith("Error"):
        try:
            uptime_seconds = int(float(uptime_output.split()[0]))
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse uptime from: {uptime_output}")
    
    # Calculate human-readable uptime
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = ((uptime_seconds % 86400) % 3600) // 60
    uptime_human = f"{days}d {hours}h {minutes}m"
    
    # Get kernel version
    kernel_output, _, _ = await run_ssh_command(
        config=config,
        command="uname -r"
    )
    
    kernel_version = kernel_output.strip() if not kernel_output.startswith("Error") else "Unknown"
    
    # Get load averages
    load_output, _, _ = await run_ssh_command(
        config=config,
        command="cat /proc/loadavg"
    )
    
    load_avg = {"1m": 0, "5m": 0, "15m": 0}
    if load_output and not load_output.startswith("Error"):
        load_parts = load_output.split()
        if len(load_parts) >= 3:
            try:
                load_avg = {
                    "1m": float(load_parts[0]),
                    "5m": float(load_parts[1]),
                    "15m": float(load_parts[2])
                }
            except (ValueError, IndexError):
                logger.warning(f"Failed to parse load average from: {load_output}")
    
    # Get logged in users
    users_output, _, _ = await run_ssh_command(
        config=config,
        command="who | wc -l"
    )
    
    users_count = 0
    if users_output and not users_output.startswith("Error") and users_output.strip().isdigit():
        users_count = int(users_output.strip())
    
    # Check for recent kernel messages that might indicate issues
    dmesg_output, _, _ = await run_ssh_command(
        config=config,
        command="dmesg | grep -i 'error\\|warn\\|fail' | tail -5"
    )
    
    recent_issues = []
    if dmesg_output and not dmesg_output.startswith("Error"):
        recent_issues = [line.strip() for line in dmesg_output.splitlines() if line.strip()]
    
    # Check if system is about to reboot for updates
    reboot_pending = False
    reboot_output, _, _ = await run_ssh_command(
        config=config,
        command="test -f /var/run/reboot-required && echo 'true' || echo 'false'"
    )
    
    if reboot_output and reboot_output.strip() == "true":
        reboot_pending = True
    
    # Determine system status based on metrics
    status = "online"
    if uptime_seconds < 300:  # Less than 5 minutes
        status = "recently_rebooted"
    elif reboot_pending:
        status = "reboot_pending"
    elif load_avg["1m"] > 10.0:  # High load
        status = "high_load"
    
    # Get hostname
    hostname_output, _, _ = await run_ssh_command(
        config=config,
        command="hostname"
    )
    
    system_hostname = hostname_output.strip() if hostname_output and not hostname_output.startswith("Error") else config.get("ip") or config.get("hostname")
    
    # Get OS information
    os_info, _, _ = await run_ssh_command(
        config=config,
        command="cat /etc/os-release 2>/dev/null || lsb_release -a 2>/dev/null || cat /etc/redhat-release 2>/dev/null"
    )
    
    os_name = "Unknown"
    os_version = "Unknown"
    
    if os_info and not os_info.startswith("Error"):
        # Try to extract OS name and version
        if "PRETTY_NAME" in os_info:
            for line in os_info.splitlines():
                if line.startswith("PRETTY_NAME="):
                    os_name_version = line.split("=", 1)[1].strip('"\'')
                    parts = os_name_version.split(None, 1)
                    if len(parts) >= 1:
                        os_name = parts[0]
                    if len(parts) >= 2:
                        os_version = parts[1]
        elif "Description:" in os_info:
            for line in os_info.splitlines():
                if line.startswith("Description:"):
                    os_name_version = line.split(":", 1)[1].strip()
                    parts = os_name_version.split(None, 1)
                    if len(parts) >= 1:
                        os_name = parts[0]
                    if len(parts) >= 2:
                        os_version = parts[1]
        else:
            # For redhat-release and similar files
            parts = os_info.strip().split(None, 1)
            if len(parts) >= 1:
                os_name = parts[0]
            if len(parts) >= 2:
                os_version = parts[1]
    
    # Return all collected information
    return {
        "server": config.get("ip") or config.get("hostname"),
        "hostname": system_hostname,
        "status": status,
        "uptime_seconds": uptime_seconds,
        "uptime_human": uptime_human,
        "kernel_version": kernel_version,
        "os_name": os_name,
        "os_version": os_version,
        "load_average": load_avg,
        "logged_in_users": users_count,
        "reboot_pending": reboot_pending,
        "recent_issues": recent_issues,
        "timestamp": datetime.now().isoformat()
    }