"""
Configuration management for the Laboratory Information System (LIS)
"""

import os
from typing import Optional, List
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Main configuration class combining all settings"""
    
    # Application settings
    app_name: str = "Laboratory Information System"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # Database configuration
    database_url: str = "sqlite:///./lis.db"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "lis_db"
    database_user: str = "lis_user"
    database_password: str = ""
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    
    # Security and authentication settings
    security_secret_key: str = "your-secret-key-change-in-production"
    security_algorithm: str = "HS256"
    security_access_token_expire_minutes: int = 30
    security_encryption_key: Optional[str] = None
    
    # Communication and networking settings
    comm_tcp_host: str = "0.0.0.0"
    comm_tcp_port: int = 8000
    comm_tcp_buffer_size: int = 4096
    comm_hl7_encoding: str = "utf-8"
    comm_hl7_field_separator: str = "|"
    comm_hl7_component_separator: str = "^"
    comm_hl7_repetition_separator: str = "~"
    comm_hl7_escape_character: str = "\\"
    comm_hl7_subcomponent_separator: str = "&"
    comm_serial_timeout: int = 30
    comm_serial_baudrate: int = 9600
    comm_serial_bytesize: int = 8
    comm_serial_parity: str = "N"
    comm_serial_stopbits: int = 1
    
    # Device configuration
    device_auto_discover_devices: bool = True
    device_scan_interval: int = 60
    device_supported_protocols: List[str] = ["HL7", "ASTM", "TCP", "Serial"]
    device_timeout: int = 30
    device_response_timeout: int = 10
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: str = "logs/lis.log"
    log_max_size: int = 10485760
    log_backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_structured_logging: bool = True
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_debug: bool = False
    api_reload: bool = False
    api_cors_origins: List[str] = ["*"]
    api_cors_methods: List[str] = ["*"]
    api_cors_headers: List[str] = ["*"]
    api_rate_limit: str = "100/minute"
    
    # Production settings
    production_service_name: str = "lis-production"
    production_pid_file: str = "/var/run/lis.pid"
    production_user: str = "lis"
    production_group: str = "lis"
    production_working_directory: str = "/opt/lis"
    production_restart_policy: str = "always"
    production_max_memory: str = "512M"
    production_max_restarts: int = 3
    production_restart_delay: int = 5
    
    # Health monitoring
    health_check_interval: int = 30
    health_check_timeout: int = 10
    health_check_retries: int = 3
    
    # Auto-processing settings
    auto_process_messages: bool = True
    auto_store_results: bool = True
    auto_generate_reports: bool = True
    auto_archive_data: bool = True
    
    # Queue and processing settings
    message_queue_size: int = 1000
    processing_batch_size: int = 50
    processing_timeout: int = 30
    max_processing_errors: int = 5
    
    # Performance settings
    performance_max_connections: int = 100
    performance_connection_timeout: int = 30
    performance_request_timeout: int = 60
    performance_thread_pool_size: int = 10
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        if v not in ['development', 'testing', 'production']:
            raise ValueError('Environment must be development, testing, or production')
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    def create_log_directory(self):
        """Create log directory if it doesn't exist"""
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Create log directory on import
settings.create_log_directory() 