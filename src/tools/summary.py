"""
Enhanced Health Summary Tool Module

Provides comprehensive health summary for servers using batched commands.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.utils.ssh import batch_execute_commands, execute_command_on_server

logger = logging.getLogger(__name__)

async def get_health_summary(config: dict) -> Dict[str, Any]:
    """
    Asynchronously gathers and summarizes system health metrics for a given server configuration
    using batched command execution for improved performance.
    
    This function collects various system metrics including CPU, memory, disk, process, and alert information
    in a single SSH session using batched commands. It aggregates the data into a comprehensive summary,
    determining the overall system status based on alert severity, and provides details on
    top resource-consuming processes and disks.
    
    Args:
        config (dict): Configuration dictionary containing server connection details (e.g., IP address).
        
    Returns:
        Dict[str, Any]: A dictionary containing the summarized health information, including:
            - server (str): Server IP address.
            - hostname (str): Hostname of the server.
            - overall_status (str): Overall health status ("healthy", "warning", or "critical").
            - uptime (str): Human-readable uptime string.
            - os_info (str): Operating system name and version.
            - kernel (str): Kernel version.
            - metrics (dict): CPU, memory, swap, and top disk usage metrics.
            - top_processes (list): List of top resource-consuming processes.
            - alerts (dict): Summary of system alerts (counts and details).
            - timestamp (str): ISO-formatted timestamp of the summary.
            
    Raises:
        Exception: If there is an error executing the batched commands or parsing the results.
    """
    logger.info(f"Collecting health summary for server: {config.get('ip', config.get('hostname', 'unknown'))}")
    
    try:
        # Define all the commands needed for a comprehensive health summary
        commands = [
            # System status commands
            "cat /proc/uptime",                     # 0: Uptime
            "uname -r",                             # 1: Kernel version
            "cat /proc/loadavg",                    # 2: Load average
            "hostname",                             # 3: Hostname
            "cat /etc/os-release 2>/dev/null || lsb_release -a 2>/dev/null || cat /etc/redhat-release 2>/dev/null", # 4: OS info
            "test -f /var/run/reboot-required && echo 'true' || echo 'false'", # 5: Reboot required
            
            # CPU metrics commands
            "top -bn1 | grep '%Cpu'",               # 6: CPU usage
            "nproc",                                # 7: CPU cores
            
            # Memory metrics commands
            "free -b",                              # 8: Memory usage
            
            # Disk metrics commands
            "df -BG --output=source,target,size,used,avail,pcent,itotal,iused,iavail,ipcent", # 9: Disk usage
            
            # Process list commands
            "ps aux --sort=-%cpu | head -6",        # 10: Top 5 CPU processes
            
            # Security metrics commands
            "grep -c 'Failed password' /var/log/auth.log 2>/dev/null || grep -c 'Failed password' /var/log/secure 2>/dev/null", # 11: Failed logins
            "apt list --upgradable 2>/dev/null | grep -c security || yum check-update --security --quiet 2>/dev/null | wc -l", # 12: Security updates
        ]
        
        # Execute all commands in a single SSH session
        results = await batch_execute_commands(config, commands)
        
        # Process system status information
        uptime_seconds = 0
        if results[0] and not results[0].startswith("Error"):
            try:
                uptime_seconds = int(float(results[0].split()[0]))
            except (ValueError, IndexError):
                logger.warning(f"Failed to parse uptime from: {results[0]}")
        
        # Calculate human-readable uptime
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = ((uptime_seconds % 86400) % 3600) // 60
        uptime_human = f"{days}d {hours}h {minutes}m"
        
        # Process kernel version
        kernel_version = results[1].strip() if results[1] and not results[1].startswith("Error") else "Unknown"
        
        # Process hostname
        hostname = results[3].strip() if results[3] and not results[3].startswith("Error") else config.get("ip") or config.get("hostname")
        
        # Process OS information
        os_name = "Unknown"
        os_version = "Unknown"
        
        if results[4] and not results[4].startswith("Error"):
            # Try to extract OS name and version
            if "PRETTY_NAME" in results[4]:
                for line in results[4].splitlines():
                    if line.startswith("PRETTY_NAME="):
                        os_name_version = line.split("=", 1)[1].strip('"\'')
                        parts = os_name_version.split(None, 1)
                        if len(parts) >= 1:
                            os_name = parts[0]
                        if len(parts) >= 2:
                            os_version = parts[1]
            elif "Description:" in results[4]:
                for line in results[4].splitlines():
                    if line.startswith("Description:"):
                        os_name_version = line.split(":", 1)[1].strip()
                        parts = os_name_version.split(None, 1)
                        if len(parts) >= 1:
                            os_name = parts[0]
                        if len(parts) >= 2:
                            os_version = parts[1]
            else:
                # For redhat-release and similar files
                parts = results[4].strip().split(None, 1)
                if len(parts) >= 1:
                    os_name = parts[0]
                if len(parts) >= 2:
                    os_version = parts[1]
        
        # Process reboot required
        reboot_pending = results[5].strip() == "true" if results[5] else False
        
        # Process load average
        load_avg = {"1m": 0, "5m": 0, "15m": 0}
        if results[2] and not results[2].startswith("Error"):
            load_parts = results[2].split()
            if len(load_parts) >= 3:
                try:
                    load_avg = {
                        "1m": float(load_parts[0]),
                        "5m": float(load_parts[1]),
                        "15m": float(load_parts[2])
                    }
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse load average from: {results[2]}")
        
        # Process CPU metrics
        cpu_usage = 0.0
        cpu_user = 0.0
        cpu_system = 0.0
        cpu_idle = 0.0
        cpu_iowait = 0.0
        
        if results[6]:
            # Parse CPU usage
            usage_parts = re.findall(r'(\d+\.\d+)\s+\w+', results[6])
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
        
        # Process CPU cores
        cores = 1  # Default to 1 core
        if results[7] and results[7].strip().isdigit():
            cores = int(results[7].strip())
        
        # Process memory metrics
        mem_total, mem_used, mem_free = 0, 0, 0
        mem_available, mem_cached, mem_buffers = 0, 0, 0
        swap_total, swap_used, swap_free = 0, 0, 0
        
        if results[8]:
            for line in results[8].splitlines():
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
        swap_total_gb = swap_total / gb_conversion
        swap_used_gb = swap_used / gb_conversion
        
        # Calculate usage percentages
        mem_usage_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
        swap_usage_percent = (swap_used / swap_total) * 100 if swap_total > 0 else 0
        
        # Process disk metrics
        disks = []
        if results[9]:
            lines = results[9].strip().splitlines()
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
                        
                        disks.append({
                            "device": device,
                            "mount_point": mount,
                            "total_gb": total_gb,
                            "used_gb": used_gb,
                            "free_gb": free_gb,
                            "usage_percent": usage_percent
                        })
        
        # Process top CPU processes
        processes = []
        if results[10]:
            lines = results[10].strip().splitlines()
            if len(lines) > 1:
                for line in lines[1:]:  # Skip header
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        user = parts[0]
                        pid = int(parts[1])
                        cpu_percent = float(parts[2])
                        memory_percent = float(parts[3])
                        command = parts[10]
                        
                        cmd_parts = command.split()
                        process_name = cmd_parts[0] if cmd_parts else "unknown"
                        
                        processes.append({
                            "name": process_name,
                            "cpu_percent": cpu_percent,
                            "memory_percent": memory_percent,
                            "pid": pid,
                            "user": user
                        })
        
        # Process security metrics
        failed_logins = 0
        if results[11] and results[11].strip().isdigit():
            failed_logins = int(results[11].strip())
        
        security_updates = 0
        if results[12] and results[12].strip().isdigit():
            security_updates = int(results[12].strip())
        
        # Determine alert status based on collected metrics
        alerts = []
        critical_count = 0
        warning_count = 0
        
        # CPU alerts
        if cpu_usage >= 90:
            alerts.append({
                "severity": "critical",
                "component": "CPU",
                "message": f"Critical CPU usage: {cpu_usage:.1f}%"
            })
            critical_count += 1
        elif cpu_usage >= 80:
            alerts.append({
                "severity": "warning",
                "component": "CPU",
                "message": f"High CPU usage: {cpu_usage:.1f}%"
            })
            warning_count += 1
        
        # Load average alerts
        if load_avg["1m"] > cores * 1.5:
            alerts.append({
                "severity": "warning",
                "component": "CPU",
                "message": f"High load average: {load_avg['1m']:.2f} (cores: {cores})"
            })
            warning_count += 1
        
        # Memory alerts
        if mem_usage_percent >= 95:
            alerts.append({
                "severity": "critical",
                "component": "Memory",
                "message": f"Critical memory usage: {mem_usage_percent:.1f}%"
            })
            critical_count += 1
        elif mem_usage_percent >= 85:
            alerts.append({
                "severity": "warning",
                "component": "Memory",
                "message": f"High memory usage: {mem_usage_percent:.1f}%"
            })
            warning_count += 1
        
        # Swap alerts
        if swap_usage_percent >= 80 and swap_total_gb > 0:
            alerts.append({
                "severity": "warning",
                "component": "Memory",
                "message": f"High swap usage: {swap_usage_percent:.1f}%"
            })
            warning_count += 1
        
        # Disk alerts
        for disk in disks:
            if disk["usage_percent"] >= 95:
                alerts.append({
                    "severity": "critical",
                    "component": "Disk",
                    "message": f"Critical disk usage on {disk['mount_point']}: {disk['usage_percent']}%"
                })
                critical_count += 1
            elif disk["usage_percent"] >= 85:
                alerts.append({
                    "severity": "warning",
                    "component": "Disk",
                    "message": f"High disk usage on {disk['mount_point']}: {disk['usage_percent']}%"
                })
                warning_count += 1
        
        # Security alerts
        if failed_logins > 10:
            alerts.append({
                "severity": "warning",
                "component": "Security",
                "message": f"High number of failed login attempts: {failed_logins}"
            })
            warning_count += 1
        
        if security_updates > 5:
            alerts.append({
                "severity": "critical",
                "component": "Security",
                "message": f"{security_updates} security updates available"
            })
            critical_count += 1
        elif security_updates > 0:
            alerts.append({
                "severity": "warning",
                "component": "Security",
                "message": f"{security_updates} security updates available"
            })
            warning_count += 1
        
        # Determine overall system status
        overall_status = "healthy"
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        
        # Create metrics summary
        metrics = {
            "cpu": {
                "usage_percent": round(cpu_usage, 1),
                "load_1m": load_avg["1m"],
                "cores": cores
            },
            "memory": {
                "usage_percent": round(mem_usage_percent, 1),
                "free_gb": round(mem_free_gb, 2),
                "total_gb": round(mem_total_gb, 2)
            },
            "swap": {
                "usage_percent": round(swap_usage_percent, 1),
                "total_gb": round(swap_total_gb, 2)
            },
            "disk": []
        }
        
        # Add disk metrics (top 3 by usage)
        sorted_disks = sorted(disks, key=lambda d: d["usage_percent"], reverse=True)
        for disk in sorted_disks[:3]:  # Top 3 disks
            metrics["disk"].append({
                "mount_point": disk["mount_point"],
                "usage_percent": disk["usage_percent"],
                "free_gb": disk["free_gb"],
                "total_gb": disk["total_gb"]
            })
        
        # Create comprehensive summary
        summary = {
            "server": config["ip"],
            "hostname": hostname,
            "overall_status": overall_status,
            "uptime": uptime_human,
            "os_info": f"{os_name} {os_version}",
            "kernel": kernel_version,
            "metrics": metrics,
            "top_processes": processes[:3],  # Top 3 processes
            "alerts": {
                "critical_count": critical_count,
                "warning_count": warning_count,
                "total_count": critical_count + warning_count,
                "items": alerts
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    except Exception as e:
        logger.error(f"Error getting health summary for {config.get('ip', 'unknown')}: {str(e)}", exc_info=True)
        return {
            "server": config.get("ip") or config.get("hostname", "unknown"),
            "error": f"Failed to get health summary: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }