"""
Enhanced System Alerts Tool Module

Detects and reports system alerts based on metrics using batched commands.
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.utils.ssh import batch_execute_commands

logger = logging.getLogger(__name__)

async def get_system_alerts(config: dict) -> Dict[str, Any]:
    """
    Asynchronously collects and analyzes system metrics to generate alerts for a given server configuration
    using batched command execution for improved performance.
    
    This function gathers CPU, memory, disk, and security metrics in a single SSH session, evaluates them 
    against predefined thresholds, and returns a summary of alerts with severity levels (critical, warning, info).
    It also includes counts of each alert type and a timestamp.
    
    Args:
        config (dict): Server configuration dictionary containing connection details (e.g., IP address).
        
    Returns:
        dict: A dictionary containing:
            - alerts (list): List of alert dictionaries with component, severity, message, and details.
            - count (int): Total number of alerts.
            - critical_count (int): Number of critical alerts.
            - warning_count (int): Number of warning alerts.
            - info_count (int): Number of informational alerts.
            - timestamp (str): ISO-formatted timestamp of when the alerts were generated.
            
    Raises:
        Exception: If there is an error executing the batched commands or parsing the results.
    """
    logger.info(f"Checking alerts for server: {config.get('ip', config.get('hostname', 'unknown'))}")
    
    try:
        # Define all the commands needed for comprehensive alert detection
        commands = [
            # CPU commands
            "top -bn1 | grep '%Cpu'",               # 0: CPU usage
            "cat /proc/loadavg",                    # 1: Load average
            "nproc",                                # 2: CPU cores
            
            # Memory commands
            "free -b",                              # 3: Memory usage
            
            # Disk commands
            "df -BG --output=source,target,size,used,avail,pcent,itotal,iused,iavail,ipcent", # 4: Disk usage
            "iostat -d -x 1 2 | tail -n +8",        # 5: Disk I/O stats
            
            # Security commands
            "grep -c 'Failed password' /var/log/auth.log 2>/dev/null || grep -c 'Failed password' /var/log/secure 2>/dev/null", # 6: Failed logins
            "ss -tuln | awk '{print $5}' | awk -F: '{print $NF}' | sort -u | grep -v '^$'", # 7: Open ports
            "apt list --upgradable 2>/dev/null | wc -l || yum check-update --quiet 2>/dev/null | wc -l", # 8: Updates available
            "apt list --upgradable 2>/dev/null | grep -c security || yum check-update --security --quiet 2>/dev/null | wc -l", # 9: Security updates
            "stat -c %Y /var/lib/apt/lists/* 2>/dev/null | sort -n -r | head -n1 || stat -c %Y /var/lib/rpm/Packages 2>/dev/null", # 10: Last update time
            "ps aux | grep -E '(cryptominer|nmap|torrent|proxy|bruteforce)' | grep -v grep", # 11: Suspicious processes
            "grep 'authentication failure\\|Failed password\\|Invalid user' /var/log/auth.log 2>/dev/null || grep 'authentication failure\\|Failed password\\|Invalid user' /var/log/secure 2>/dev/null | tail -5" # 12: Recent auth logs
        ]
        
        # Execute all commands in a single SSH session
        results = await batch_execute_commands(config, commands)
        
        alerts = []
        
        # Process CPU metrics
        cpu_usage = 0.0
        cpu_iowait = 0.0
        cpu_idle = 100.0  # Default to 100% idle if parsing fails
        
        if results[0]:
            # Parse CPU usage
            usage_parts = re.findall(r'(\d+\.\d+)\s+\w+', results[0])
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
        
        # Process load average
        load_1m, load_5m, load_15m = 0.0, 0.0, 0.0
        if results[1]:
            load_parts = results[1].split()
            if len(load_parts) >= 3:
                try:
                    load_1m = float(load_parts[0])
                    load_5m = float(load_parts[1])
                    load_15m = float(load_parts[2])
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse load average from: {results[1]}")
        
        # Process CPU cores
        cores = 1  # Default to 1 core
        if results[2] and results[2].strip().isdigit():
            cores = int(results[2].strip())
        
        # Process memory metrics
        mem_total, mem_used, mem_free = 0, 0, 0
        mem_available, mem_cached, mem_buffers = 0, 0, 0
        swap_total, swap_used, swap_free = 0, 0, 0
        
        if results[3]:
            for line in results[3].splitlines():
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
        swap_free_gb = swap_free / gb_conversion
        
        # Calculate usage percentages
        mem_usage_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
        swap_usage_percent = (swap_used / swap_total) * 100 if swap_total > 0 else 0
        
        # Process disk metrics
        disks = []
        if results[4]:
            lines = results[4].strip().splitlines()
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
        
        # Process disk I/O stats
        io_stats = {}
        if results[5]:
            lines = results[5].strip().splitlines()
            for line in lines:
                parts = line.split()
                if len(parts) >= 14:
                    device = parts[0]
                    # Map basic iostat metrics
                    io_stats[device] = {
                        "reads_per_sec": float(parts[3]),
                        "writes_per_sec": float(parts[4]),
                        "read_kb_per_sec": float(parts[5]),
                        "write_kb_per_sec": float(parts[6]),
                        "util_percent": float(parts[13])
                    }
            
            # Enhance disk metrics with I/O stats if available
            for disk in disks:
                device_name = os.path.basename(disk["device"])
                if device_name in io_stats:
                    disk["io_stats"] = io_stats[device_name]
        
        # Process security metrics
        failed_logins = 0
        if results[6] and results[6].strip().isdigit():
            failed_logins = int(results[6].strip())
        
        # Process open ports
        open_ports = []
        if results[7]:
            for line in results[7].splitlines():
                if line.strip().isdigit():
                    open_ports.append(int(line.strip()))
        
        # Process updates available
        updates_available = 0
        if results[8] and results[8].strip().isdigit():
            updates_available = int(results[8].strip())
            if updates_available > 0:
                # Adjust for header line in apt output
                updates_available -= 1
        
        # Process security updates
        security_updates = 0
        if results[9] and results[9].strip().isdigit():
            security_updates = int(results[9].strip())
        
        # Process last update time
        days_since_update = 999
        if results[10] and results[10].strip().isdigit():
            try:
                last_update_timestamp = int(results[10].strip())
                days_since_update = (datetime.now() - datetime.fromtimestamp(last_update_timestamp)).days
            except (ValueError, TypeError):
                pass
        
        # Process suspicious processes
        suspicious_processes = []
        if results[11] and results[11].strip():
            for line in results[11].splitlines():
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    suspicious_processes.append({
                        "user": parts[0],
                        "pid": parts[1],
                        "command": parts[10]
                    })
        
        # Process recent auth logs
        recent_auth_failures = []
        if results[12] and results[12].strip():
            recent_auth_failures = [line.strip() for line in results[12].splitlines() if line.strip()]
        
        # Generate alerts based on collected metrics
        
        # CPU alerts
        if cpu_usage >= 90:
            alerts.append({
                "component": "CPU",
                "severity": "critical",
                "message": f"Critical CPU usage: {cpu_usage:.1f}%",
                "details": {
                    "usage_percent": cpu_usage,
                    "load_1m": load_1m
                }
            })
        elif cpu_usage >= 80:
            alerts.append({
                "component": "CPU",
                "severity": "warning",
                "message": f"High CPU usage: {cpu_usage:.1f}%",
                "details": {
                    "usage_percent": cpu_usage,
                    "load_1m": load_1m
                }
            })
        
        # Load average alerts
        if load_1m > cores * 1.5:
            alerts.append({
                "component": "CPU",
                "severity": "warning",
                "message": f"High load average: {load_1m:.2f} (cores: {cores})",
                "details": {
                    "load_1m": load_1m,
                    "load_5m": load_5m,
                    "load_15m": load_15m,
                    "cores": cores
                }
            })
        
        # IO wait alerts
        if cpu_iowait > 20:
            alerts.append({
                "component": "CPU",
                "severity": "warning",
                "message": f"High I/O wait: {cpu_iowait:.1f}%",
                "details": {
                    "iowait_percent": cpu_iowait
                }
            })
        
        # Memory alerts
        if mem_usage_percent >= 95:
            alerts.append({
                "component": "Memory",
                "severity": "critical",
                "message": f"Critical memory usage: {mem_usage_percent:.1f}%",
                "details": {
                    "usage_percent": mem_usage_percent,
                    "free_gb": mem_free_gb,
                    "total_gb": mem_total_gb
                }
            })
        elif mem_usage_percent >= 85:
            alerts.append({
                "component": "Memory",
                "severity": "warning",
                "message": f"High memory usage: {mem_usage_percent:.1f}%",
                "details": {
                    "usage_percent": mem_usage_percent,
                    "free_gb": mem_free_gb,
                    "total_gb": mem_total_gb
                }
            })
        
        # Swap usage alerts
        if swap_usage_percent >= 80 and swap_total_gb > 0:
            alerts.append({
                "component": "Memory",
                "severity": "warning",
                "message": f"High swap usage: {swap_usage_percent:.1f}%",
                "details": {
                    "swap_usage_percent": swap_usage_percent,
                    "swap_used_gb": swap_used_gb,
                    "swap_total_gb": swap_total_gb
                }
            })
        
        # Low memory warning
        if mem_free_gb < 1.0 and mem_total_gb > 2.0:
            alerts.append({
                "component": "Memory",
                "severity": "warning",
                "message": f"Low free memory: {mem_free_gb:.2f} GB",
                "details": {
                    "free_gb": mem_free_gb,
                    "total_gb": mem_total_gb
                }
            })
        
        # Disk space alerts
        for disk in disks:
            if disk["usage_percent"] >= 95:
                alerts.append({
                    "component": "Disk",
                    "severity": "critical",
                    "message": f"Critical disk usage on {disk['mount_point']}: {disk['usage_percent']}%",
                    "details": {
                        "device": disk["device"],
                        "mount_point": disk["mount_point"],
                        "usage_percent": disk["usage_percent"],
                        "free_gb": disk["free_gb"],
                        "total_gb": disk["total_gb"]
                    }
                })
            elif disk["usage_percent"] >= 85:
                alerts.append({
                    "component": "Disk",
                    "severity": "warning",
                    "message": f"High disk usage on {disk['mount_point']}: {disk['usage_percent']}%",
                    "details": {
                        "device": disk["device"],
                        "mount_point": disk["mount_point"],
                        "usage_percent": disk["usage_percent"],
                        "free_gb": disk["free_gb"],
                        "total_gb": disk["total_gb"]
                    }
                })
            
            # Low disk space alert (absolute value)
            if disk["free_gb"] < 1.0 and disk["total_gb"] > 10.0:
                alerts.append({
                    "component": "Disk",
                    "severity": "warning",
                    "message": f"Low free space on {disk['mount_point']}: {disk['free_gb']} GB",
                    "details": {
                        "mount_point": disk["mount_point"],
                        "free_gb": disk["free_gb"],
                        "total_gb": disk["total_gb"]
                    }
                })
            
            # Inode usage alerts
            if disk.get("inodes_usage_percent", 0) >= 90:
                alerts.append({
                    "component": "Disk",
                    "severity": "warning",
                    "message": f"High inode usage on {disk['mount_point']}: {disk['inodes_usage_percent']}%",
                    "details": {
                        "mount_point": disk["mount_point"],
                        "inodes_usage_percent": disk["inodes_usage_percent"],
                        "inodes_free": disk.get("inodes_free", 0)
                    }
                })
            
            # Check I/O stats if available
            if "io_stats" in disk and disk["io_stats"].get("util_percent", 0) > 80:
                alerts.append({
                    "component": "Disk",
                    "severity": "warning",
                    "message": f"High disk I/O utilization on {disk['device']}: {disk['io_stats']['util_percent']}%",
                    "details": {
                        "device": disk["device"],
                        "util_percent": disk["io_stats"]["util_percent"],
                        "reads_per_sec": disk["io_stats"]["reads_per_sec"],
                        "writes_per_sec": disk["io_stats"]["writes_per_sec"]
                    }
                })
        
        # Security alerts
        if failed_logins > 10:
            alerts.append({
                "component": "Security",
                "severity": "warning",
                "message": f"High number of failed login attempts: {failed_logins}",
                "details": {
                    "failed_logins": failed_logins
                }
            })
        
        if security_updates > 0:
            severity = "critical" if security_updates > 5 else "warning"
            alerts.append({
                "component": "Security",
                "severity": severity,
                "message": f"{security_updates} security updates available",
                "details": {
                    "security_updates": security_updates,
                    "updates_available": updates_available
                }
            })
        
        if days_since_update > 30:
            alerts.append({
                "component": "Security",
                "severity": "warning",
                "message": f"System not updated for {days_since_update} days",
                "details": {
                    "days_since_update": days_since_update
                }
            })
        
        if len(suspicious_processes) > 0:
            alerts.append({
                "component": "Security",
                "severity": "critical",
                "message": "Suspicious processes detected",
                "details": {
                    "suspicious_processes": suspicious_processes
                }
            })
        
        # Check for unusual ports
        suspicious_ports = [
            port for port in open_ports
            if port not in [22, 80, 443, 3306, 5432, 8080, 8443]  # Common legitimate ports
        ]
        if suspicious_ports:
            alerts.append({
                "component": "Security",
                "severity": "warning",
                "message": f"Unusual ports open: {', '.join(map(str, suspicious_ports))}",
                "details": {
                    "unusual_ports": suspicious_ports,
                    "all_open_ports": open_ports
                }
            })
        
        # Count alerts by severity
        critical_count = sum(1 for alert in alerts if alert["severity"] == "critical")
        warning_count = sum(1 for alert in alerts if alert["severity"] == "warning")
        info_count = sum(1 for alert in alerts if alert["severity"] == "info")
        
        logger.info(f"Found {len(alerts)} alerts for {config.get('ip', 'unknown')}: {critical_count} critical, {warning_count} warning")
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting system alerts for {config.get('ip', 'unknown')}: {str(e)}", exc_info=True)
        return {
            "alerts": [{
                "component": "Monitoring",
                "severity": "critical",
                "message": f"Failed to collect system alerts: {str(e)}",
                "details": {}
            }],
            "count": 1,
            "critical_count": 1,
            "warning_count": 0,
            "info_count": 0,
            "timestamp": datetime.now().isoformat()
        }