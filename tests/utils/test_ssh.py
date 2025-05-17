import pytest
import asyncio
import asyncssh
from unittest import mock
from src.utils.ssh import get_ssh_connection, run_ssh_command

pytestmark = pytest.mark.asyncio(loop_scope="function")

async def test_get_ssh_connection(server_config, monkeypatch):
    """Test SSH connection establishment."""
    # Mock asyncssh.connect
    mock_connect = mock.AsyncMock()
    mock_conn = mock.AsyncMock()
    mock_connect.return_value = mock_conn
    monkeypatch.setattr(asyncssh, "connect", mock_connect)
    
    # Call the function
    conn = await get_ssh_connection(server_config)
    
    # Verify the connection
    assert conn == mock_conn
    mock_connect.assert_called_once_with(
        server_config["ip"],
        username=server_config["username"],
        port=server_config["ssh_port"],
        known_hosts=None,
        connect_timeout=30
    )

async def test_run_ssh_command(server_config, mock_ssh_connection, monkeypatch):
    """Test executing a command via SSH."""
    # Mock get_ssh_connection
    mock_get_conn = mock.AsyncMock()
    mock_get_conn.return_value = mock_ssh_connection
    monkeypatch.setattr("src.utils.ssh.get_ssh_connection", mock_get_conn)
    
    # Call the function
    stdout, stderr, exit_code = await run_ssh_command(
        config=server_config,
        command="echo 'test'"
    )
    
    # Verify the result
    assert stdout == "Sample output for: echo 'test'"
    assert stderr == ""
    assert exit_code == 0
    mock_ssh_connection.run.assert_called_once_with("echo 'test'", check=False)

async def test_ssh_command_timeout(server_config, mock_ssh_connection, monkeypatch):
    """Test timeout handling for SSH commands."""
    # Mock get_ssh_connection
    mock_get_conn = mock.AsyncMock()
    mock_get_conn.return_value = mock_ssh_connection
    monkeypatch.setattr("src.utils.ssh.get_ssh_connection", mock_get_conn)
    
    # Make run raise a timeout
    mock_ssh_connection.run.side_effect = asyncio.TimeoutError()
    
    # Call the function
    stdout, stderr, exit_code = await run_ssh_command(
        config=server_config,
        command="sleep 100",
        timeout=1
    )
    
    # Verify the result
    assert stdout == ""
    assert "Command timed out" in stderr
    assert exit_code == 124