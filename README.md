# MCP System Health Monitoring

A robust server monitoring system built on the Multi-Channel Protocol (MCP) framework, designed for seamless integration with Claude and other AI assistants.

## Overview

MCP System Health Monitoring provides real-time health and performance metrics for remote Linux servers. It establishes SSH connections to collect system metrics including CPU usage, memory utilization, disk space, network statistics, security metrics, and more.

## Features

- **Comprehensive Metrics Collection**: CPU, memory, disk, network, security metrics, and more
- **Real-time Monitoring**: Live system status checks and performance insights
- **Multi-Server Support**: Monitor multiple servers from a single MCP instance
- **Threshold-based Alerts**: Automatic detection of critical system conditions
- **SSH Connection Management**: Efficient connection pooling and reuse
- **Security-focused**: Monitor for failed login attempts, suspicious processes, and security updates
- **MCP Integration**: Ready for AI assistant interaction via the MCP protocol

## Requirements

- Python 3.8+
- asyncssh
- MCP Python SDK
- SSH access to target servers

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-system-health.git
   cd mcp-system-health
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a configuration file for each server you want to monitor:

```json
{
  "hostname": "server1",
  "ip": "192.168.1.100",
  "ssh_port": 22,
  "username": "admin",
  "key_path": "~/.ssh/id_rsa"
}
```

Alternatively, you can use the command-line launcher to dynamically create configurations.

## Usage

### Using the Launcher

```bash
./mcp_launcher.py --username=admin --key-path=~/.ssh/id_rsa --servers=192.168.1.100,192.168.1.101
```

### Command-line Options

- `--username`: SSH username (required)
- `--password`: SSH password (either this or key-path required)
- `--key-path`: Path to SSH private key (either this or password required)
- `--ssh-port`: SSH port (default: 22)
- `--servers`: Comma-separated list of server IPs (required)
- `--repository`: Path to existing server repository
- `--log-level`: Logging level (debug, info, warning, error)

### Using as a Library

```python
from src.server import serve

# Configure your servers
server_configs = [
    {
        "hostname": "server1",
        "ip": "192.168.1.100",
        "ssh_port": 22,
        "username": "admin",
        "key_path": "~/.ssh/id_rsa"
    }
]

# Start the MCP server
await serve(server_configs)
```

## Available Tools

The MCP server exposes the following tools:

1. **system_status**: General system status information
2. **cpu_metrics**: Detailed CPU metrics
3. **memory_metrics**: Memory usage and swap statistics
4. **disk_metrics**: Disk usage for all or specific mount points
5. **network_metrics**: Network interface statistics
6. **security_metrics**: Security-related metrics
7. **process_list**: List of top CPU-consuming processes
8. **system_alerts**: Current alerts based on threshold violations
9. **health_summary**: Comprehensive health summary

## Alert Thresholds

The system provides automatic alerts based on these default thresholds:

- **CPU**:
  - Critical: Usage ≥ 90%
  - Warning: Usage ≥ 80%
  - Warning: Load average > 1.5 × core count
  - Warning: I/O wait > 20%

- **Memory**:
  - Critical: Usage ≥ 95%
  - Warning: Usage ≥ 85%
  - Warning: Swap usage ≥ 80%
  - Warning: Free memory < 1GB (on systems with ≥ 2GB)

- **Disk**:
  - Critical: Usage ≥ 95%
  - Warning: Usage ≥ 85%
  - Warning: Free space < 1GB (on disks ≥ 10GB)
  - Warning: Inode usage ≥ 90%
  - Warning: Disk I/O utilization > 80%

- **Security**:
  - Warning: Failed logins > 10
  - Critical: Security updates > 5
  - Warning: Security updates ≥ 1
  - Warning: System not updated for ≥ 30 days
  - Critical: Suspicious processes detected
  - Warning: Unusual ports open

## Security Considerations

- Prefer key-based authentication over password authentication
- Use dedicated monitoring accounts with limited permissions
- Store SSH credentials securely
- Run the MCP server on a secure, trusted host

## Limitations

- Currently only supports Linux-based servers
- No historical data storage (metrics are real-time only)
- No notification system for alerts (alerts are only available via tool calls)
- Limited customization of alert thresholds

## Troubleshooting

- Ensure SSH credentials are correct
- Check that target servers allow SSH connections
- Verify that the user has sufficient permissions to execute system commands
- Enable debug logging for more detailed output

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License