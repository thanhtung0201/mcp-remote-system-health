from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# Server Configuration Models
class ServerConfig(BaseModel):
    """Server configuration model"""
    hostname: str
    ip: str
    ssh_port: int = 22
    username: str
    key_path: Optional[str] = None
    password: Optional[str] = None

class ServerHealthConfig(BaseModel):
    """Server configuration model"""
    hostname: str
    ip: str
    ssh_port: int = 22
    username: str
    key_path: Optional[str] = None
    password: Optional[str] = None

# Input Models for Tools
class SystemStatus(BaseModel):
    """Input for system status tool"""

class CpuMetrics(BaseModel):
    """Input for CPU metrics tool"""

class MemoryMetrics(BaseModel):
    """Input for memory metrics tool"""

class DiskMetrics(BaseModel):
    """Input for disk metrics tool"""
    mount_point: Optional[str] = None

class NetworkMetrics(BaseModel):
    """Input for network metrics tool"""
    interface: Optional[str] = None

class SecurityMetrics(BaseModel):
    """Input for security metrics tool"""

class ProcessList(BaseModel):
    """Input for process list tool"""
    count: int = 10

class SystemAlerts(BaseModel):
    """Input for system alerts tool"""

class HealthSummary(BaseModel):
    """Input for health summary tool"""

# Output Models

class CPUMetricsOutput(BaseModel):
    """CPU metrics output model"""
    usage_percent: float
    user_percent: float
    system_percent: float
    idle_percent: float
    cores: int
    load_1m: float
    load_5m: Optional[float] = None
    load_15m: Optional[float] = None
    timestamp: str

class MemoryMetricsOutput(BaseModel):
    """Memory metrics output model"""
    total_gb: float
    used_gb: float
    free_gb: float
    available_gb: Optional[float] = None
    usage_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_usage_percent: float
    timestamp: str

class DiskInfo(BaseModel):
    """Disk information model"""
    device: str
    mount_point: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float

class DiskMetricsOutput(BaseModel):
    """Disk metrics output model"""
    disks: List[DiskInfo]
    timestamp: str

class NetworkInfo(BaseModel):
    """Network interface information model"""
    interface: str
    rx_bytes: int
    tx_bytes: int
    rx_mb: float
    tx_mb: float
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int
    rx_dropped: int
    tx_dropped: int

class NetworkMetricsOutput(BaseModel):
    """Network metrics output model"""
    interfaces: List[NetworkInfo]
    timestamp: str

class ProcessInfo(BaseModel):
    """Process information model"""
    pid: int
    user: str
    cpu_percent: float
    memory_percent: float
    command: str

class ProcessListOutput(BaseModel):
    """Process list output model"""
    processes: List[ProcessInfo]
    timestamp: str

class AlertInfo(BaseModel):
    """Alert information model"""
    component: str
    severity: str
    message: str

class SystemAlertsOutput(BaseModel):
    """System alerts output model"""
    alerts: List[AlertInfo]
    count: int
    critical_count: int
    warning_count: int
    timestamp: str

class HealthSummaryOutput(BaseModel):
    """Health summary output model"""
    server: str
    status: str
    uptime: str
    metrics: Dict[str, Any]
    alerts: Dict[str, Any]
    timestamp: str

# Tool Enumeration
class SystemHealthTools(str, Enum):
    """Enumeration of available system health tools"""
    STATUS = "system_status"
    CPU = "cpu_metrics"
    MEMORY = "memory_metrics"
    DISK = "disk_metrics"
    NETWORK = "network_metrics"
    SECURITY = "security_metrics"
    PROCESSES = "process_list"
    ALERTS = "system_alerts"
    SUMMARY = "health_summary"