"""
CPU Metrics Module

Collects CPU metrics from remote servers.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.utils.ssh import execute_command_on_server

logger = logging.getLogger(__name__)

async def get_cpu_metrics(config: dict) -> Dict[str, Any]:
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