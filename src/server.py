"""
MCP System Health Server

Main server implementation that registers and handles MCP tools.
"""

import logging
import json
from pathlib import Path
from typing import Sequence, List, Dict, Any, Optional

from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)

from src.models.metrics import (
    SystemHealthTools,
    SystemStatus,
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    NetworkMetrics,
    SecurityMetrics,
    ProcessList,
    SystemAlerts,
    HealthSummary,
)

from src.tools.status import get_system_status
from src.tools.metrics import (
    get_memory_metrics,
    get_disk_metrics,
    get_network_metrics,
    get_security_metrics,
    get_process_list,
    get_cpu_metrics
)
from src.tools.alerts import get_system_alerts
from src.tools.summary import get_health_summary

logger = logging.getLogger(__name__)

async def serve(server_configs: List[Dict[str, Any]]) -> None:
    """
    Start the MCP System Health server.
    
    Args:
        server_configs: List of dictionaries containing server configurations
                       (hostname, ip, credentials, etc.)
    """
    if not server_configs:
        raise ValueError("No server configurations provided")
    
    logger.info(f"Starting MCP System Health server with {len(server_configs)} servers")
    
    server = Server("mcp-system-health")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """
        Register the tools that the server provides.
        
        Returns:
            List of Tool objects
        """
        return [
            Tool(
                name=SystemHealthTools.STATUS,
                description="Get general system status information",
                inputSchema=SystemStatus.schema(),
            ),
            Tool(
                name=SystemHealthTools.CPU,
                description="Get detailed CPU metrics",
                inputSchema=CpuMetrics.schema(),
            ),
            Tool(
                name=SystemHealthTools.MEMORY,
                description="Get detailed memory metrics",
                inputSchema=MemoryMetrics.schema(),
            ),
            Tool(
                name=SystemHealthTools.DISK,
                description="Get disk usage metrics for all disks or a specific mount point",
                inputSchema=DiskMetrics.schema(),
            ),
            Tool(
                name=SystemHealthTools.NETWORK,
                description="Get network interface metrics for all interfaces or a specific one",
                inputSchema=NetworkMetrics.schema(),
            ),
            Tool(
                name=SystemHealthTools.SECURITY,
                description="Get security-related metrics including updates and failed logins",
                inputSchema=SecurityMetrics.schema(),
            ),
            Tool(
                name=SystemHealthTools.PROCESSES,
                description="Get list of top CPU-consuming processes",
                inputSchema=ProcessList.schema(),
            ),
            Tool(
                name=SystemHealthTools.ALERTS,
                description="Get current system alerts based on thresholds",
                inputSchema=SystemAlerts.schema(),
            ),
            Tool(
                name=SystemHealthTools.SUMMARY,
                description="Get a comprehensive health summary for the server",
                inputSchema=HealthSummary.schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle tool calls by dispatching to the appropriate handler.
        Collects metrics from all configured servers.
        
        Args:
            name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            List of TextContent with the tool results
        """
        logger.info(f"Calling tool {name} for all servers")
        results = []
        
        # Process specific arguments that apply to all servers
        mount_point = arguments.get("mount_point")
        interface = arguments.get("interface")
        count = arguments.get("count", 10)
        
        # Collect metrics from all servers
        for config in server_configs:
            hostname = config.get("hostname", "unknown")
            ip = config.get("ip", "unknown")
            
            logger.info(f"Processing {name} for server {hostname} ({ip})")
            
            try:
                match name:
                    case SystemHealthTools.STATUS:
                        result = await get_system_status(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"System Status for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.CPU:
                        result = await get_cpu_metrics(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"CPU Metrics for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.MEMORY:
                        result = await get_memory_metrics(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"Memory Metrics for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.DISK:
                        result = await get_disk_metrics(config=config, mount_point=mount_point)
                        results.append(TextContent(
                            type="text",
                            text=f"Disk Metrics for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.NETWORK:
                        result = await get_network_metrics(config=config, interface=interface)
                        results.append(TextContent(
                            type="text",
                            text=f"Network Metrics for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.SECURITY:
                        result = await get_security_metrics(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"Security Metrics for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.PROCESSES:
                        result = await get_process_list(config=config, count=count)
                        results.append(TextContent(
                            type="text",
                            text=f"Process List for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.ALERTS:
                        result = await get_system_alerts(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"System Alerts for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case SystemHealthTools.SUMMARY:
                        result = await get_health_summary(config=config)
                        results.append(TextContent(
                            type="text",
                            text=f"Health Summary for {hostname} ({ip}):\n{json.dumps(result, indent=2)}"
                        ))
                        
                    case _:
                        raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error calling tool {name} for {hostname} ({ip}): {e}", exc_info=True)
                results.append(TextContent(
                    type="text",
                    text=f"Error executing {name} for {hostname} ({ip}): {str(e)}"
                ))
        
        return results

    # Launch the server
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)