"""
SSH Utility Module

Provides utilities for executing SSH commands on remote servers with session reuse.
"""

import asyncio
import logging
import json
import os
import asyncssh
import tempfile
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Global dictionary to store active SSH connections
# Key: f"{username}@{hostname}:{port}"
# Value: asyncssh.SSHClientConnection object
active_connections = {}
connection_semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent connections

async def get_ssh_connection_with_retry(config, max_retries=3, initial_delay=1):
    """Get SSH connection with retry logic"""
    attempt = 0
    last_exception = None
    
    while attempt < max_retries:
        try:
            return await get_ssh_connection(config)
        except Exception as e:
            last_exception = e
            attempt += 1
            if attempt < max_retries:
                # Exponential backoff
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning(f"SSH connection attempt {attempt} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
    
    # If we get here, all retries failed
    logger.error(f"All SSH connection attempts failed: {last_exception}")
    raise last_exception

async def get_ssh_connection(
    config: Dict[str, Any],
    port: int = 22,
    timeout: int = 30
) -> asyncssh.SSHClientConnection:
    """
    Get an active SSH connection or create a new one if it doesn't exist.
    
    Args:
        config: Dictionary containing server configuration
        port: SSH port (default: 22)
        timeout: Connection timeout in seconds
        
    Returns:
        An active SSH connection
    """
    hostname = config.get("ip") or config.get("hostname")
    if not hostname:
        raise ValueError("No hostname or IP specified in server configuration")
    
    username = config.get("username")
    if not username:
        raise ValueError("No username specified in server configuration")
    
    # Get authentication information from config
    key_path = config.get("key_path")
    password = config.get("password")
    
    # Create a unique key for this connection
    connection_key = f"{username}@{hostname}:{port}"
    
    # Check if we already have an active connection
    if connection_key in active_connections:
        conn = active_connections[connection_key]
        # Check if the connection is still active
        if not conn.is_closed():
            logger.debug(f"Reusing existing SSH connection to {connection_key}")
            return conn
        else:
            # Remove the closed connection
            logger.debug(f"Removing closed SSH connection to {connection_key}")
            del active_connections[connection_key]
    
    logger.debug(f"Establishing new SSH connection to {connection_key}")
    
    # SSH client options
    options = {
        'known_hosts': None,  # Disable known hosts check
        'username': username,
        'port': port,
        'connect_timeout': timeout
    }
    
    # Try password authentication first if provided
    if password:
        options['password'] = password
    
    # Add key-based authentication as a fallback or primary method
    if key_path:
        key_path = os.path.expanduser(key_path)
        if os.path.exists(key_path):
            try:
                options['client_keys'] = [key_path]
            except Exception as e:
                logger.warning(f"Failed to load SSH key {key_path}: {e}")
    
    # Use the connection_semaphore to limit concurrent connections
    async with connection_semaphore:
        try:
            conn = await asyncssh.connect(hostname, **options)
            active_connections[connection_key] = conn
            return conn
        except (asyncssh.Error, OSError) as e:
            logger.error(f"SSH connection failed: {str(e)}")
            raise RuntimeError(f"Failed to establish SSH connection: {str(e)}")

async def run_ssh_command(
    config: Dict[str, Any],
    command: str,
    port: int = 22,
    timeout: int = 30,
    reuse_connection: bool = True
) -> Tuple[str, str, int]:
    """
    Execute a command on a remote server using SSH.
    
    Args:
        config: Dictionary containing server configuration
        command: Command to execute
        port: SSH port (default: 22)
        timeout: Command timeout in seconds
        reuse_connection: Whether to reuse an existing connection or create a new one
        
    Returns:
        Tuple containing (stdout, stderr, return_code)
    """
    if not command:
        raise ValueError("No command specified for execution")
    
    hostname = config.get("ip") or config.get("hostname")
    username = config.get("username")
    
    try:
        # Get an active connection (either new or reused)
        conn = await get_ssh_connection_with_retry(config)
        
        # Execute the command
        logger.debug(f"Executing command on {username}@{hostname}: {command}")
        
        try:
            result = await asyncio.wait_for(
                conn.run(command, check=False),
                timeout=timeout
            )
            
            stdout_text = result.stdout
            stderr_text = result.stderr
            return_code = result.exit_status or 0
            
            if return_code != 0:
                logger.warning(
                    f"SSH command failed with return code {return_code}: {stderr_text}"
                )
            
            # If we're not reusing connections, close this one
            if not reuse_connection:
                conn.close()
                connection_key = f"{username}@{hostname}:{port}"
                if connection_key in active_connections:
                    del active_connections[connection_key]
            
            return stdout_text, stderr_text, return_code
            
        except asyncio.TimeoutError:
            logger.error(f"SSH command timed out after {timeout} seconds")
            return "", f"Command timed out after {timeout} seconds", 124
            
    except Exception as e:
        logger.error(f"Failed to execute SSH command: {str(e)}")
        return "", f"Failed to execute SSH command: {str(e)}", 255

async def execute_command_on_server(
    config: Dict[str, Any], 
    command: str,
    reuse_connection: bool = True
) -> Tuple[str, str, int]:
    """
    Execute a command on a remote server using SSH.
    
    Args:
        config: Dictionary containing server configuration
        command: Command to execute on the server
        reuse_connection: Whether to reuse an existing connection
        
    Returns:        
        Tuple containing (stdout, stderr, return_code)
    """
    try:
        if not command:
            raise ValueError("No command specified for execution")
            
        ssh_port = config.get("ssh_port", 22)
        
        # Execute the command
        return await run_ssh_command(
            config=config,
            command=command,
            port=ssh_port,
            timeout=30,
            reuse_connection=reuse_connection
        )
    except Exception as e:
        logger.error(f"Failed to execute command on server: {e}")
        return "", str(e), 1

async def batch_execute_commands(config, commands):
    """Execute multiple commands in a single SSH session"""
    # Combine commands with separators and output markers
    batch_command = ""
    for i, cmd in enumerate(commands):
        # Add command with output marker
        batch_command += f'echo "===CMD_START_{i}==="; {cmd}; echo "===CMD_END_{i}==="'
        if i < len(commands) - 1:
            batch_command += "; "
    
    # Execute the batch command
    stdout, stderr, exit_code = await execute_command_on_server(config, batch_command)
    
    # Parse results
    results = []
    current_output = ""
    current_cmd = None
    
    for line in stdout.splitlines():
        if line.startswith("===CMD_START_"):
            current_cmd = int(line.split("_")[2].split("=")[0])
            current_output = ""
        elif line.startswith("===CMD_END_"):
            if current_cmd is not None:
                results.append(current_output)
                current_cmd = None
        elif current_cmd is not None:
            current_output += line + "\n"
    
    return results

async def close_all_connections():
    """Close all active SSH connections with timeout handling"""
    for key, conn in list(active_connections.items()):
        try:
            # Set a timeout for closing connections
            close_task = asyncio.create_task(conn.wait_closed())
            try:
                await asyncio.wait_for(close_task, timeout=5)
                logger.debug(f"Closed SSH connection to {key}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout closing SSH connection to {key}, forcing close")
                conn.abort()
            del active_connections[key]
        except Exception as e:
            logger.warning(f"Error closing SSH connection to {key}: {e}")