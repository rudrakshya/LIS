"""
Equipment model for the Laboratory Information System
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum, Float, JSON
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from ..core.database import Base


class EquipmentStatus(PyEnum):
    """Equipment status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    CALIBRATING = "calibrating"
    QUALITY_CONTROL = "quality_control"
    STANDBY = "standby"


class EquipmentType(PyEnum):
    """Equipment type enumeration"""
    CHEMISTRY_ANALYZER = "chemistry_analyzer"
    HEMATOLOGY_ANALYZER = "hematology_analyzer"
    IMMUNOASSAY_ANALYZER = "immunoassay_analyzer"
    MICROBIOLOGY_ANALYZER = "microbiology_analyzer"
    COAGULATION_ANALYZER = "coagulation_analyzer"
    URINALYSIS_ANALYZER = "urinalysis_analyzer"
    MOLECULAR_ANALYZER = "molecular_analyzer"
    MICROSCOPE = "microscope"
    CENTRIFUGE = "centrifuge"
    INCUBATOR = "incubator"
    REFRIGERATOR = "refrigerator"
    FREEZER = "freezer"
    OTHER = "other"


class CommunicationProtocol(PyEnum):
    """Communication protocol enumeration"""
    HL7 = "hl7"
    ASTM = "astm"
    TCP_IP = "tcp_ip"
    SERIAL = "serial"
    FILE_BASED = "file_based"
    HTTP = "http"
    FTP = "ftp"
    OTHER = "other"


class Equipment(Base):
    """Equipment/Device model"""
    
    __tablename__ = "equipment"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Equipment identifiers
    equipment_id = Column(String(50), unique=True, index=True, nullable=False)
    serial_number = Column(String(100), unique=True, index=True)
    asset_tag = Column(String(50), unique=True)
    
    # Basic information
    name = Column(String(200), nullable=False)
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    equipment_type = Column(Enum(EquipmentType), nullable=False)
    
    # Version and firmware
    software_version = Column(String(50))
    firmware_version = Column(String(50))
    driver_version = Column(String(50))
    
    # Location and installation
    location = Column(String(100))  # Lab room, department
    installation_date = Column(DateTime)
    warranty_expiration = Column(DateTime)
    
    # Status and operational info
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.OFFLINE, nullable=False)
    is_active = Column(Boolean, default=True)
    is_validated = Column(Boolean, default=False)
    last_validation_date = Column(DateTime)
    
    # Communication settings
    communication_protocol = Column(Enum(CommunicationProtocol))
    ip_address = Column(String(45))  # IPv4 or IPv6
    port = Column(Integer)
    serial_port = Column(String(20))  # COM1, /dev/ttyUSB0, etc.
    baud_rate = Column(Integer)
    
    # Connection settings (stored as JSON)
    connection_settings = Column(JSON)  # Additional protocol-specific settings
    
    # Capabilities
    supported_tests = Column(JSON)  # List of test codes this equipment can perform
    sample_types = Column(JSON)     # List of sample types it accepts
    throughput_per_hour = Column(Integer)  # Max samples per hour
    
    # Quality control settings
    qc_frequency = Column(String(50))  # Daily, weekly, etc.
    last_qc_date = Column(DateTime)
    next_qc_due = Column(DateTime)
    qc_status = Column(String(20))  # Pass, Fail, Due, Overdue
    
    # Calibration information
    last_calibration_date = Column(DateTime)
    next_calibration_due = Column(DateTime)
    calibration_status = Column(String(20))  # Current, Due, Overdue, Failed
    calibration_frequency = Column(String(50))  # Monthly, quarterly, etc.
    
    # Maintenance information
    last_maintenance_date = Column(DateTime)
    next_maintenance_due = Column(DateTime)
    maintenance_interval_days = Column(Integer)
    
    # Performance metrics
    uptime_percentage = Column(Float)
    error_rate_percentage = Column(Float)
    average_processing_time = Column(Float)  # in minutes
    total_samples_processed = Column(Integer, default=0)
    
    # Environmental conditions
    operating_temperature_min = Column(Float)
    operating_temperature_max = Column(Float)
    operating_humidity_min = Column(Float)
    operating_humidity_max = Column(Float)
    
    # Service and support
    service_contract_number = Column(String(100))
    service_provider = Column(String(200))
    technical_contact = Column(String(200))
    technical_phone = Column(String(20))
    
    # Configuration and settings
    configuration = Column(JSON)  # Equipment-specific configuration
    default_settings = Column(JSON)  # Default operational settings
    
    # Interface information
    interface_engine = Column(String(100))  # Middleware or interface engine used
    last_connection = Column(DateTime)
    connection_errors = Column(Integer, default=0)
    
    # Notes and documentation
    description = Column(Text)
    installation_notes = Column(Text)
    operational_notes = Column(Text)
    troubleshooting_notes = Column(Text)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    def __repr__(self):
        return f"<Equipment(id={self.id}, equipment_id='{self.equipment_id}', name='{self.name}', status='{self.status.value}')>"
    
    @property
    def is_online(self) -> bool:
        """Check if equipment is online"""
        return self.status == EquipmentStatus.ONLINE
    
    @property
    def is_operational(self) -> bool:
        """Check if equipment is operational"""
        return self.status in [EquipmentStatus.ONLINE, EquipmentStatus.STANDBY]
    
    @property
    def needs_maintenance(self) -> bool:
        """Check if equipment needs maintenance"""
        if not self.next_maintenance_due:
            return False
        return datetime.utcnow() >= self.next_maintenance_due
    
    @property
    def needs_calibration(self) -> bool:
        """Check if equipment needs calibration"""
        if not self.next_calibration_due:
            return False
        return datetime.utcnow() >= self.next_calibration_due
    
    @property
    def needs_qc(self) -> bool:
        """Check if equipment needs quality control"""
        if not self.next_qc_due:
            return False
        return datetime.utcnow() >= self.next_qc_due
    
    @property
    def is_warranty_valid(self) -> bool:
        """Check if equipment warranty is still valid"""
        if not self.warranty_expiration:
            return False
        return datetime.utcnow() <= self.warranty_expiration
    
    @property
    def age_in_years(self) -> Optional[float]:
        """Calculate equipment age in years"""
        if not self.installation_date:
            return None
        return (datetime.utcnow() - self.installation_date).days / 365.25
    
    def can_perform_test(self, test_code: str) -> bool:
        """Check if equipment can perform a specific test"""
        if not self.supported_tests:
            return False
        return test_code in self.supported_tests
    
    def accepts_sample_type(self, sample_type: str) -> bool:
        """Check if equipment accepts a specific sample type"""
        if not self.sample_types:
            return False
        return sample_type in self.sample_types
    
    def get_connection_string(self) -> str:
        """Generate connection string for the equipment"""
        if self.communication_protocol == CommunicationProtocol.TCP_IP:
            return f"tcp://{self.ip_address}:{self.port}"
        elif self.communication_protocol == CommunicationProtocol.SERIAL:
            return f"serial://{self.serial_port}:{self.baud_rate}"
        else:
            return f"{self.communication_protocol.value}://{self.ip_address or self.serial_port}"
    
    def to_dict(self) -> dict:
        """Convert equipment to dictionary"""
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "serial_number": self.serial_number,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "equipment_type": self.equipment_type.value,
            "status": self.status.value,
            "is_active": self.is_active,
            "is_online": self.is_online,
            "is_operational": self.is_operational,
            "location": self.location,
            "communication_protocol": self.communication_protocol.value if self.communication_protocol else None,
            "connection_string": self.get_connection_string(),
            "needs_maintenance": self.needs_maintenance,
            "needs_calibration": self.needs_calibration,
            "needs_qc": self.needs_qc,
            "is_warranty_valid": self.is_warranty_valid,
            "age_in_years": self.age_in_years,
            "uptime_percentage": self.uptime_percentage,
            "total_samples_processed": self.total_samples_processed,
            "last_connection": self.last_connection.isoformat() if self.last_connection else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 