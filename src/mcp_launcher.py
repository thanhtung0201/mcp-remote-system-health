#!/usr/bin/env python3
"""
System Health MCP Server Launcher

This script serves as an entry point for Claude to launch the System Health MCP Server.
It accepts arguments for SSH credentials and server IPs.

Usage:
  ./mcp_launcher.py --username=admin --key-path=~/.ssh/id_rsa --servers=192.168.1.100,192.168.1.101
"""

import os
import sys
import json
import argparse
import tempfile
import asyncio
import logging
from pathlib import Path

# Ensure the project directory is in the Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

# Import the serve function from your project
from src.server import serve

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(os.path.dirname(__file__), "mcp_system_health.log")),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("mcp_launcher")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="System Health MCP Server Launcher")
    
    # SSH credentials
    parser.add_argument("--username", type=str, required=True, help="SSH username")
    parser.add_argument("--password", type=str, help="SSH password")
    parser.add_argument("--key-path", type=str, help="Path to SSH private key")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port (default: 22)")
    
    # Server list
    parser.add_argument("--servers", type=str, required=True, help="Comma-separated list of server IPs")
    
    # Additional options
    parser.add_argument("--repository", type=str, help="Path to existing server repository")
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info")
    
    args = parser.parse_args()
    
    # Validate authentication parameters
    if not args.key_path and not args.password:
        parser.error("Either --key-path or --password must be provided")
    
    return args

def create_temp_repository(args):
    """
    Create a temporary repository with server configurations based on command-line arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Path to the temporary repository
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="mcp_servers_")
    
    # Parse server list
    servers = []
    if args.servers:
        servers = [ip.strip() for ip in args.servers.split(",") if ip.strip()]
    
    # Create a configuration file for each server
    for i, ip in enumerate(servers):
        server_name = f"server{i+1}"
        
        # Create server configuration
        config = {
            "hostname": server_name,
            "ip": ip,
            "ssh_port": args.ssh_port,
            "username": args.username
        }
        
        # Add authentication
        if args.key_path:
            config["key_path"] = os.path.expanduser(args.key_path)
        elif args.password:
            config["password"] = args.password
        
        # Write configuration to file
        config_path = os.path.join(temp_dir, f"{server_name}.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    
    return temp_dir

async def main():
    """Main entry point"""
    logger = setup_logging()
    args = parse_args()
    
    # Set log level
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    
    # Determine repository path
    repository_path = None
    if args.repository:
        # Use existing repository
        repository_path = Path(args.repository)
        if not repository_path.exists():
            logger.error(f"Repository path not found: {repository_path}")
            return 1
    elif args.servers:
        # Create temporary repository from server list
        repository_path = Path(create_temp_repository(args))
        logger.info(f"Created temporary repository at {repository_path}")
    else:
        logger.error("No repository or server list provided")
        return 1
    
    # List available servers
    logger.info(f"Available servers in repository {repository_path}:")
    server_configs = []
    
    for server_file in repository_path.glob("*.json"):
        logger.info(f"  - {server_file.stem}")
        
        # Load the server configuration
        with open(server_file, "r") as f:
            config = json.load(f)
            server_configs.append(config)
    
    if not server_configs:
        logger.error("No server configurations found in repository")
        return 1
    
    # Start the server
    logger.info(f"Starting MCP System Health Server with {len(server_configs)} server configurations...")
    
    try:
        await serve(server_configs)
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))