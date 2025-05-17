"""
Metrics Tool Module

Provides various system metrics collection functions.
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.utils.ssh import execute_command_on_server, run_ssh_command

logger = logging.getLogger(__name__)

async def get_cpu_metrics(config: dict) -> Dict[str, Any]:
    """
    Asynchronously collects CPU metrics from a remote server specified by the given configuration.
    Args:
        config (dict): A dictionary containing server connection details, including the 'ip' key.
    Returns:
        Dict[str, Any]: A dictionary containing the following CPU metrics:
            - usage_percent (float): Total CPU usage percentage.
            - user_percent (float): Percentage of CPU used by user processes.
            - system_percent (float): Percentage of CPU used by system processes.
            - idle_percent (float): Percentage of CPU that is idle.
            - iowait_percent (float): Percentage of CPU waiting for I/O operations.
            - cores (int): Number of CPU cores.
            - load_1m (float): System load average over the last 1 minute.
            - load_5m (float): System load average over the last 5 minutes.
            - load_15m (float): System load average over the last 15 minutes.
            - timestamp (str): ISO formatted timestamp of when the metrics were collected.
            - error (str, optional): Error message if metrics collection fails.
    Raises:
        None. Errors are logged and returned in the result dictionary.
    """
    logger.info(f"Collecting CPU metrics from {config['ip']}")
    
    # Get CPU usage
    cpu_output, stderr, exit_code = await execute_command_on_server(
        config=config,
        command="top -bn1 | grep '%Cpu'"
    )
    
    if exit_code != 0:
        logger.error(f"Error getting CPU metrics: {stderr}")
        return {
            "error": f"Failed to get CPU metrics: {stderr}",
            "timestamp": datetime.now().isoformat()
        }
    
    # Parse CPU usage
    cpu_usage = 0.0
    cpu_user = 0.0
    cpu_system = 0.0
    cpu_idle = 0.0
    cpu_iowait = 0.0
    
    if cpu_output:
        # Parse CPU usage
        usage_parts = re.findall(r'(\d+\.\d+)\s+\w+', cpu_output)
        if len(usage_parts) > 0:
            cpu_user = float(usage_parts[0])
        if len(usage_parts) > 1:
            cpu_system = float(usage_parts[1])
        if len(usage_parts) > 3:
            cpu_idle = float(usage_parts[3])
        if len(usage_parts) > 4:
            cpu_iowait = float(usage_parts[4])
        
        # Calculate total CPU usage
        cpu_usage = 100.0 - cpu_idle
    
    # Get load averages
    load_output, stderr, exit_code = await execute_command_on_server(
        config=config,
        command="cat /proc/loadavg"
    )
    
    load_1m, load_5m, load_15m = 0.0, 0.0, 0.0
    if exit_code == 0 and load_output:
        load_parts = load_output.split()
        if len(load_parts) >= 1:
            try:
                load_1m = float(load_parts[0])
            except ValueError:
                pass
        if len(load_parts) >= 2:
            try:
                load_5m = float(load_parts[1])
            except ValueError:
                pass
        if len(load_parts) >= 3:
            try:
                load_15m = float(load_parts[2])
            except ValueError:
                pass
    
    # Get CPU core count
    cores_output, stderr, exit_code = await execute_command_on_server(
        config=config,
        command="nproc"
    )
    
    cores = 1  # Default to 1 core
    if exit_code == 0 and cores_output and cores_output.strip().isdigit():
        cores = int(cores_output.strip())
    
    return {
        "usage_percent": round(cpu_usage, 1),
        "user_percent": round(cpu_user, 1),
        "system_percent": round(cpu_system, 1),
        "idle_percent": round(cpu_idle, 1),
        "iowait_percent": round(cpu_iowait, 1),
        "cores": cores,
        "load_1m": round(load_1m, 2),
        "load_5m": round(load_5m, 2),
        "load_15m": round(load_15m, 2),
        "timestamp": datetime.now().isoformat()
    }

async def get_memory_metrics(config: Dict) -> Dict[str, Any]:
    """
    Asynchronously retrieves memory and swap usage metrics from a remote system via SSH.
    Args:
        config (Dict): Configuration dictionary containing SSH connection parameters.
    Returns:
        Dict[str, Any]: A dictionary containing memory and swap statistics in gigabytes,
        usage percentages, and a timestamp. If an error occurs during SSH command execution,
        the dictionary contains an "error" key with the error message and a timestamp.
    Metrics returned:
        - total_gb: Total system memory in GB.
        - used_gb: Used system memory in GB.
        - free_gb: Free system memory in GB.
        - available_gb: Available system memory in GB.
        - cached_gb: Cached memory in GB.
        - buffers_gb: Buffers memory in GB.
        - usage_percent: Percentage of used memory.
        - available_percent: Percentage of available memory.
        - swap_total_gb: Total swap memory in GB.
        - swap_used_gb: Used swap memory in GB.
        - swap_free_gb: Free swap memory in GB.
        - swap_usage_percent: Percentage of used swap memory.
        - timestamp: ISO formatted timestamp of when the metrics were collected.
    """
    
    # Get memory information
    mem_output, stderr, exit_code = await run_ssh_command(
        config=config,
        command="free -b"
    )
    
    if exit_code != 0:
        logger.error(f"Error getting memory metrics: {stderr}")
        return {
            "error": f"Failed to get memory metrics: {stderr}",
            "timestamp": datetime.now().isoformat()
        }
    
    # Parse memory info
    mem_total, mem_used, mem_free = 0, 0, 0
    mem_available, mem_cached, mem_buffers = 0, 0, 0
    swap_total, swap_used, swap_free = 0, 0, 0
    
    for line in mem_output.splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 7:
                mem_total = int(parts[1])
                mem_used = int(parts[2])
                mem_free = int(parts[3])
                mem_buffers = int(parts[5]) if len(parts) > 5 else 0
                mem_cached = int(parts[6]) if len(parts) > 6 else 0
                mem_available = int(parts[6]) if len(parts) > 6 else mem_free
        elif line.startswith("Swap:"):
            parts = line.split()
            if len(parts) >= 4:
                swap_total = int(parts[1])
                swap_used = int(parts[2])
                swap_free = int(parts[3])
    
    # Convert to GB
    gb_conversion = 1024 * 1024 * 1024
    mem_total_gb = mem_total / gb_conversion
    mem_used_gb = mem_used / gb_conversion
    mem_free_gb = mem_free / gb_conversion
    mem_available_gb = mem_available / gb_conversion
    mem_cached_gb = mem_cached / gb_conversion
    mem_buffers_gb = mem_buffers / gb_conversion
    swap_total_gb = swap_total / gb_conversion
    swap_used_gb = swap_used / gb_conversion
    swap_free_gb = swap_free / gb_conversion
    
    # Calculate usage percentages
    mem_usage_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
    mem_available_percent = (mem_available / mem_total) * 100 if mem_total > 0 else 0
    swap_usage_percent = (swap_used / swap_total) * 100 if swap_total > 0 else 0
    
    return {
        "total_gb": round(mem_total_gb, 2),
        "used_gb": round(mem_used_gb, 2),
        "free_gb": round(mem_free_gb, 2),
        "available_gb": round(mem_available_gb, 2),
        "cached_gb": round(mem_cached_gb, 2),
        "buffers_gb": round(mem_buffers_gb, 2),
        "usage_percent": round(mem_usage_percent, 1),
        "available_percent": round(mem_available_percent, 1),
        "swap_total_gb": round(swap_total_gb, 2),
        "swap_used_gb": round(swap_used_gb, 2),
        "swap_free_gb": round(swap_free_gb, 2),
        "swap_usage_percent": round(swap_usage_percent, 1),
        "timestamp": datetime.now().isoformat()
    }

async def get_disk_metrics(config: dict, mount_point: Optional[str] = None) -> Dict[str, Any]:
    """
    Asynchronously collects disk usage and I/O metrics from a remote server via SSH.
    Args:
        config (dict): SSH connection configuration, must include at least the 'ip' key.
        mount_point (Optional[str], optional): Specific mount point to query. If None, all mount points are queried. Defaults to None.
    Returns:
        Dict[str, Any]: A dictionary containing:
            - "disks": A list of dictionaries, each with disk metrics:
                - "device": Device name (e.g., '/dev/sda1').
                - "mount_point": Mount point path.
                - "total_gb": Total disk size in GB.
                - "used_gb": Used disk space in GB.
                - "free_gb": Free disk space in GB.
                - "usage_percent": Percentage of disk used.
                - "inodes_total": Total number of inodes.
                - "inodes_used": Number of used inodes.
                - "inodes_free": Number of free inodes.
                - "inodes_usage_percent": Percentage of inodes used.
                - "io_stats" (optional): Dictionary with I/O statistics if available:
                    - "reads_per_sec": Reads per second.
                    - "writes_per_sec": Writes per second.
                    - "read_kb_per_sec": Read throughput in KB/s.
                    - "write_kb_per_sec": Write throughput in KB/s.
                    - "util_percent": Device utilization percentage.
            - "timestamp": ISO formatted timestamp of when metrics were collected.
            - "error" (optional): Error message if disk metrics collection failed.
    Logs:
        Logs information and errors related to disk metrics collection.
    Raises:
        None. Errors are captured in the returned dictionary under the "error" key.
    """
    logger.info(f"Collecting disk metrics from {config['ip']}")

    
    # Build command for disk usage
    command = "df -BG --output=source,target,size,used,avail,pcent,itotal,iused,iavail,ipcent"
    if mount_point:
        command += f" {mount_point}"
        
    disk_output, stderr, exit_code = await run_ssh_command(
        config=config,
        command=command
    )
    
    if exit_code != 0:
        logger.error(f"Error getting disk metrics: {stderr}")
        return {
            "error": f"Failed to get disk metrics: {stderr}",
            "disks": [],
            "timestamp": datetime.now().isoformat()
        }
    
    disks = []
    
    # Skip header line and parse disk information
    lines = disk_output.strip().splitlines()
    if len(lines) > 1:
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 10:
                device = parts[0]
                
                # Skip special filesystems
                if any(fs in device for fs in ['tmpfs', 'devtmpfs', 'none', 'udev']):
                    continue
                    
                mount = parts[1]
                
                # Remove trailing 'G' from sizes
                total_gb = float(parts[2].rstrip('G'))
                used_gb = float(parts[3].rstrip('G'))
                free_gb = float(parts[4].rstrip('G'))
                
                # Parse percentage (remove %)
                usage_percent = float(parts[5].rstrip('%'))
                
                # Parse inode info
                inodes_total = int(parts[6])
                inodes_used = int(parts[7])
                inodes_free = int(parts[8])
                inodes_usage_percent = float(parts[9].rstrip('%'))
                
                disks.append({
                    "device": device,
                    "mount_point": mount,
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "usage_percent": usage_percent,
                    "inodes_total": inodes_total,
                    "inodes_used": inodes_used,
                    "inodes_free": inodes_free,
                    "inodes_usage_percent": inodes_usage_percent
                })
    
    # Get disk I/O stats if available
    iostat_output, _, io_exit_code = await run_ssh_command(
        config=config,
        command="iostat -d -x 1 2"  # Remove tail to capture full output
    )
    
    if io_exit_code == 0:
        io_stats = {}
        lines = iostat_output.strip().splitlines()
        
        # Find the last device section (after the last "Device:" header)
        device_section_start = -1
        for i, line in enumerate(lines):
            if "Device:" in line:
                device_section_start = i
        
        if device_section_start >= 0 and device_section_start + 1 < len(lines):
            # Process device data lines that follow the last "Device:" header
            for line in lines[device_section_start + 1:]:
                parts = line.split()
                if len(parts) >= 14:
                    device = parts[0]
                    try:
                        # Try to parse as numbers (will fail for header lines with text like 'rrqm/s')
                        io_stats[device] = {
                            "reads_per_sec": float(parts[3]),
                            "writes_per_sec": float(parts[4]),
                            "read_kb_per_sec": float(parts[5]),
                            "write_kb_per_sec": float(parts[6]),
                            "util_percent": float(parts[13])
                        }
                    except ValueError:
                        # Skip lines that can't be parsed as numbers (like headers)
                        continue
        
        # Enhance disk metrics with I/O stats if available
        for disk in disks:
            device_name = os.path.basename(disk["device"])
            if device_name in io_stats:
                disk["io_stats"] = io_stats[device_name]
    
    return {
        "disks": disks,
        "timestamp": datetime.now().isoformat()
    }

async def get_network_metrics(config: dict, interface: Optional[str] = None) -> Dict[str, Any]:
    """
    Asynchronously retrieves network metrics from a remote system via SSH.
    This function gathers statistics for network interfaces, including bytes and packets sent/received,
    errors, dropped packets, interface speed, and IP address. It also collects TCP connection counts.
    Args:
        config (dict): SSH configuration dictionary for connecting to the remote system.
        interface (Optional[str], optional): Specific network interface to query. If None, all interfaces are included except loopback. Defaults to None.
    Returns:
        Dict[str, Any]: A dictionary containing:
            - "interfaces": List of dictionaries with metrics for each network interface.
            - "connections": Dictionary with TCP connection statistics.
            - "timestamp": ISO formatted timestamp of when the metrics were collected.
            - "error": Error message if metrics could not be retrieved (only present on failure).
    """
    
    # Get network statistics
    net_output, stderr, exit_code = await run_ssh_command(
        config=config,
        command="cat /proc/net/dev"
    )
    
    if exit_code != 0:
        logger.error(f"Error getting network metrics: {stderr}")
        return {
            "error": f"Failed to get network metrics: {stderr}",
            "interfaces": [],
            "timestamp": datetime.now().isoformat()
        }
    
    interfaces = []
    
    # Skip header lines (first two lines) and parse interface data
    lines = net_output.strip().splitlines()
    if len(lines) > 2:
        for line in lines[2:]:
            parts = line.split(":")
            if len(parts) < 2:
                continue
                
            iface = parts[0].strip()
            
            # Skip loopback or filter for specific interface
            if iface == "lo" or (interface and iface != interface):
                continue
                
            stats = parts[1].split()
            
            if len(stats) >= 16:
                rx_bytes = int(stats[0])
                rx_packets = int(stats[1])
                rx_errors = int(stats[2])
                rx_dropped = int(stats[3])
                tx_bytes = int(stats[8])
                tx_packets = int(stats[9])
                tx_errors = int(stats[10])
                tx_dropped = int(stats[11])
                
                # Convert bytes to MB
                rx_mb = rx_bytes / (1024 * 1024)
                tx_mb = tx_bytes / (1024 * 1024)
                
                interfaces.append({
                    "interface": iface,
                    "rx_bytes": rx_bytes,
                    "tx_bytes": tx_bytes,
                    "rx_mb": round(rx_mb, 2),
                    "tx_mb": round(tx_mb, 2),
                    "rx_packets": rx_packets,
                    "tx_packets": tx_packets,
                    "rx_errors": rx_errors,
                    "tx_errors": tx_errors,
                    "rx_dropped": rx_dropped,
                    "tx_dropped": tx_dropped
                })
    
    # Get additional network info like IP address and speed
    for iface in interfaces:
        interface_name = iface["interface"]
        
        # Get IP address
        ip_output, _, ip_exit_code = await run_ssh_command(
            config=config,
            command=f"ip addr show {interface_name} | grep 'inet ' | awk '{{print $2}}'"
        )
        
        if ip_exit_code == 0 and ip_output.strip():
            ip_parts = ip_output.strip().split('/')
            if len(ip_parts) > 0:
                iface["ip_address"] = ip_parts[0]
        
        # Get interface speed
        speed_output, _, speed_exit_code = await run_ssh_command(
            config=config,
            command=f"cat /sys/class/net/{interface_name}/speed 2>/dev/null || echo 'unknown'"
        )
        
        if speed_exit_code == 0 and speed_output.strip().isdigit():
            iface["speed_mbps"] = int(speed_output.strip())
    
    # Get network connections count
    conn_output, _, conn_exit_code = await run_ssh_command(
        config=config,
        command="ss -s | grep 'TCP:' | tr -s ' ' | cut -d' ' -f2-"
    )
    
    connections = {}
    if conn_exit_code == 0:
        # Extract connection counts
        tcp_total = re.search(r'(\d+) connections', conn_output)
        if tcp_total:
            connections["tcp_total"] = int(tcp_total.group(1))
        
        estab = re.search(r'(\d+) ESTAB', conn_output)
        if estab:
            connections["tcp_established"] = int(estab.group(1))
    
    return {
        "interfaces": interfaces,
        "connections": connections,
        "timestamp": datetime.now().isoformat()
    }

async def get_security_metrics(config: dict) -> Dict[str, Any]:
    """
    Asynchronously gathers various security-related metrics from a remote server via SSH.
    Args:
        config (dict): SSH connection configuration parameters.
    Returns:
        Dict[str, Any]: A dictionary containing the following security metrics:
            - failed_logins (int): Number of failed login attempts found in authentication logs.
            - open_ports (List[int]): List of open TCP/UDP port numbers.
            - updates_available (int): Number of available package updates (excluding header line).
            - security_updates (int): Number of available security updates.
            - days_since_update (int): Number of days since the last package update.
            - suspicious_processes (List[dict]): List of suspicious processes detected, each with 'user', 'pid', and 'command'.
            - recent_auth_failures (List[str]): Up to 5 recent authentication failure log entries.
            - timestamp (str): ISO formatted timestamp when metrics were collected.
    Notes:
        - This function relies on the presence of certain system utilities (e.g., grep, awk, ss, apt, yum, stat, ps).
        - The function is designed to work with both Debian-based and Red Hat-based Linux distributions.
        - Requires an asynchronous SSH command runner function named `run_ssh_command`.
    """

    
    # Check failed logins
    failed_logins_output, _, failed_exit_code = await run_ssh_command(
        config=config,
        command="grep -c 'Failed password' /var/log/auth.log 2>/dev/null || grep -c 'Failed password' /var/log/secure 2>/dev/null"
    )
    
    failed_logins = 0
    if failed_exit_code == 0 and failed_logins_output.strip().isdigit():
        failed_logins = int(failed_logins_output.strip())
    
    # Check open ports
    open_ports_output, _, ports_exit_code = await run_ssh_command(
        config=config,
        command="ss -tuln | awk '{print $5}' | awk -F: '{print $NF}' | sort -u | grep -v '^$'"
    )
    
    open_ports = []
    if ports_exit_code == 0:
        for line in open_ports_output.splitlines():
            if line.strip().isdigit():
                open_ports.append(int(line.strip()))
    
    # Check for available updates
    updates_output, _, updates_exit_code = await run_ssh_command(
        config=config,
        command="apt list --upgradable 2>/dev/null | wc -l || yum check-update --quiet 2>/dev/null | wc -l"
    )
    
    updates_available = 0
    if updates_exit_code == 0 and updates_output.strip().isdigit():
        updates_available = int(updates_output.strip())
        if updates_available > 0:
            # Adjust for header line in apt output
            updates_available -= 1
    
    # Check for security updates
    security_updates_output, _, security_exit_code = await run_ssh_command(
        config=config,
        command="apt list --upgradable 2>/dev/null | grep -c security || yum check-update --security --quiet 2>/dev/null | wc -l"
    )
    
    security_updates = 0
    if security_exit_code == 0 and security_updates_output.strip().isdigit():
        security_updates = int(security_updates_output.strip())
    
    # Check last update time
    last_update_output, _, update_exit_code = await run_ssh_command(
        config=config,
        command="stat -c %Y /var/lib/apt/lists/* 2>/dev/null | sort -n -r | head -n1 || stat -c %Y /var/lib/rpm/Packages 2>/dev/null"
    )
    
    days_since_update = 999
    if update_exit_code == 0 and last_update_output.strip().isdigit():
        try:
            last_update_timestamp = int(last_update_output.strip())
            days_since_update = (datetime.now() - datetime.fromtimestamp(last_update_timestamp)).days
        except (ValueError, TypeError):
            pass
    
    # Check for suspicious processes
    suspicious_output, _, suspicious_exit_code = await run_ssh_command(
        config=config,
        command="ps aux | grep -E '(cryptominer|nmap|torrent|proxy|bruteforce)' | grep -v grep"
    )
    
    suspicious_processes = []
    if suspicious_exit_code == 0 and suspicious_output.strip():
        for line in suspicious_output.splitlines():
            parts = line.split(None, 10)
            if len(parts) >= 11:
                suspicious_processes.append({
                    "user": parts[0],
                    "pid": parts[1],
                    "command": parts[10]
                })
    
    # Check recent auth logs for unusual activity
    auth_output, _, auth_exit_code = await run_ssh_command(
        config=config,
        command="grep 'authentication failure\\|Failed password\\|Invalid user' /var/log/auth.log 2>/dev/null || grep 'authentication failure\\|Failed password\\|Invalid user' /var/log/secure 2>/dev/null | tail -5"
    )
    
    recent_auth_failures = []
    if auth_exit_code == 0 and auth_output.strip():
        recent_auth_failures = [line.strip() for line in auth_output.splitlines() if line.strip()]
    
    return {
        "failed_logins": failed_logins,
        "open_ports": open_ports,
        "updates_available": updates_available,
        "security_updates": security_updates,
        "days_since_update": days_since_update,
        "suspicious_processes": suspicious_processes,
        "recent_auth_failures": recent_auth_failures[:5],  # Limit to 5 entries
        "timestamp": datetime.now().isoformat()
    }

async def get_process_list(config: dict, count: int = 10) -> Dict[str, Any]:
    """
    Asynchronously retrieves a list of top processes by CPU usage from a remote server via SSH.
    Args:
        config (dict): SSH configuration dictionary used to connect to the remote server.
        count (int, optional): Number of top processes to retrieve. Defaults to 10.
    Returns:
        Dict[str, Any]: A dictionary containing:
            - "processes": List of dictionaries, each representing a process with details such as user, pid, cpu_percent, memory_percent, virtual_size, resident_size, tty, state, start_time, time, command, runtime, and open_files.
            - "count": Number of processes returned.
            - "timestamp": ISO formatted timestamp of when the data was collected.
            - "error" (optional): Error message if the process list could not be retrieved.
    Notes:
        - Requires SSH access to the target server.
        - Uses `ps` and `/proc` to gather process information.
        - Each process entry includes additional runtime and open file count details.
    """
    
    # Get top processes by CPU usage
    process_output, stderr, exit_code = await run_ssh_command(
        config=config,
        command=f"ps aux --sort=-%cpu | head -{count + 1}"
    )
    
    if exit_code != 0:
        logger.error(f"Error getting process list: {stderr}")
        return {
            "error": f"Failed to get process list: {stderr}",
            "processes": [],
            "timestamp": datetime.now().isoformat()
        }
    
    processes = []
    
    # Skip the header line and parse process information
    lines = process_output.strip().splitlines()
    if len(lines) > 1:
        for line in lines[1:]:  # Skip header
            parts = line.split(None, 10)
            if len(parts) >= 11:
                user = parts[0]
                pid = int(parts[1])
                cpu_percent = float(parts[2])
                memory_percent = float(parts[3])
                vsz = int(parts[4])
                rss = int(parts[5])
                tty = parts[6]
                stat = parts[7]
                start_time = parts[8]
                time = parts[9]
                command = parts[10]
                
                processes.append({
                    "user": user,
                    "pid": pid,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "virtual_size": vsz,
                    "resident_size": rss,
                    "tty": tty,
                    "state": stat,
                    "start_time": start_time,
                    "time": time,
                    "command": command
                })
    
    # Get additional process info like running time for each process
    for process in processes:
        pid = process["pid"]
        
        # Get process runtime
        runtime_output, _, runtime_exit_code = await run_ssh_command(
            config=config,
            command=f"ps -o etimes= -p {pid}"
        )
        
        if runtime_exit_code == 0 and runtime_output.strip().isdigit():
            seconds = int(runtime_output.strip())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            process["runtime"] = f"{hours}h {minutes}m"
        
        # Get open files count
        files_output, _, files_exit_code = await run_ssh_command(
            config=config,
            command=f"ls -l /proc/{pid}/fd 2>/dev/null | wc -l"
        )
        
        if files_exit_code == 0 and files_output.strip().isdigit():
            process["open_files"] = int(files_output.strip()) - 1  # Subtract header line
    
    return {
        "processes": processes,
        "count": len(processes),
        "timestamp": datetime.now().isoformat()
    }