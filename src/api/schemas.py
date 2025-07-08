"""
Pydantic schemas for Laboratory Information System API
Defines request and response models for REST API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

from ..models import (
    OrderStatus, SampleType, EquipmentType, EquipmentStatus,
    CommunicationProtocol, Gender
)


# Base schemas with common fields
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        orm_mode = True
        use_enum_values = True


# Patient schemas
class PatientBase(BaseSchema):
    """Base patient schema with common fields"""
    patient_id: str = Field(..., description="Unique patient identifier")
    first_name: str = Field(..., min_length=1, max_length=100, description="Patient first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Patient last name")
    date_of_birth: Optional[date] = Field(None, description="Patient date of birth")
    gender: Optional[Gender] = Field(None, description="Patient gender")
    phone: Optional[str] = Field(None, max_length=20, description="Patient phone number")
    email: Optional[str] = Field(None, max_length=255, description="Patient email address")
    address: Optional[str] = Field(None, max_length=500, description="Patient address")
    emergency_contact: Optional[str] = Field(None, max_length=255, description="Emergency contact")
    insurance_number: Optional[str] = Field(None, max_length=100, description="Insurance number")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email address')
        return v


class PatientCreate(PatientBase):
    """Schema for creating a new patient"""
    pass


class PatientUpdate(BaseSchema):
    """Schema for updating patient information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact: Optional[str] = Field(None, max_length=255)
    insurance_number: Optional[str] = Field(None, max_length=100)


class PatientResponse(PatientBase):
    """Schema for patient API response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# Test Order schemas
class TestOrderBase(BaseSchema):
    """Base test order schema"""
    patient_id: str = Field(..., description="Patient identifier")
    test_code: str = Field(..., min_length=1, max_length=50, description="Test code")
    test_name: str = Field(..., min_length=1, max_length=200, description="Test name")
    priority: str = Field("ROUTINE", description="Order priority")
    clinical_info: Optional[str] = Field(None, max_length=1000, description="Clinical information")
    physician: Optional[str] = Field(None, max_length=200, description="Ordering physician")
    department: Optional[str] = Field(None, max_length=100, description="Ordering department")


class TestOrderCreate(TestOrderBase):
    """Schema for creating a new test order"""
    order_number: Optional[str] = Field(None, max_length=100, description="Order number (auto-generated if not provided)")


class TestOrderUpdate(BaseSchema):
    """Schema for updating test order"""
    test_code: Optional[str] = Field(None, min_length=1, max_length=50)
    test_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[OrderStatus] = None
    priority: Optional[str] = None
    clinical_info: Optional[str] = Field(None, max_length=1000)
    physician: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)


class TestOrderResponse(TestOrderBase):
    """Schema for test order API response"""
    id: int
    order_number: str
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Sample schemas
class SampleBase(BaseSchema):
    """Base sample schema"""
    sample_id: str = Field(..., description="Unique sample identifier")
    test_order_id: int = Field(..., description="Associated test order ID")
    sample_type: SampleType = Field(..., description="Type of sample")
    collection_date: Optional[datetime] = Field(None, description="Sample collection date")
    received_date: Optional[datetime] = Field(None, description="Sample received date")
    volume: Optional[float] = Field(None, ge=0, description="Sample volume in mL")
    container_type: Optional[str] = Field(None, max_length=100, description="Container type")
    collection_site: Optional[str] = Field(None, max_length=200, description="Collection site")
    collector: Optional[str] = Field(None, max_length=200, description="Sample collector")
    comments: Optional[str] = Field(None, max_length=500, description="Sample comments")


class SampleCreate(SampleBase):
    """Schema for creating a new sample"""
    pass


class SampleUpdate(BaseSchema):
    """Schema for updating sample information"""
    sample_type: Optional[SampleType] = None
    collection_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    volume: Optional[float] = Field(None, ge=0)
    container_type: Optional[str] = Field(None, max_length=100)
    collection_site: Optional[str] = Field(None, max_length=200)
    collector: Optional[str] = Field(None, max_length=200)
    comments: Optional[str] = Field(None, max_length=500)


class SampleResponse(SampleBase):
    """Schema for sample API response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# Test Result schemas
class TestResultBase(BaseSchema):
    """Base test result schema"""
    test_order_id: int = Field(..., description="Associated test order ID")
    test_code: str = Field(..., min_length=1, max_length=50, description="Test code")
    test_name: str = Field(..., min_length=1, max_length=200, description="Test name")
    result_value: Optional[str] = Field(None, max_length=500, description="Test result value")
    result_unit: Optional[str] = Field(None, max_length=50, description="Result unit")
    reference_range: Optional[str] = Field(None, max_length=200, description="Reference range")
    result_status: str = Field("FINAL", description="Result status")
    abnormal_flag: Optional[str] = Field(None, max_length=10, description="Abnormal flag")
    comments: Optional[str] = Field(None, max_length=1000, description="Result comments")
    equipment_id: Optional[str] = Field(None, description="Equipment that performed the test")
    technician: Optional[str] = Field(None, max_length=200, description="Technician who performed test")


class TestResultCreate(TestResultBase):
    """Schema for creating a new test result"""
    result_id: Optional[str] = Field(None, max_length=100, description="Result ID (auto-generated if not provided)")


class TestResultUpdate(BaseSchema):
    """Schema for updating test result"""
    result_value: Optional[str] = Field(None, max_length=500)
    result_unit: Optional[str] = Field(None, max_length=50)
    reference_range: Optional[str] = Field(None, max_length=200)
    result_status: Optional[str] = None
    abnormal_flag: Optional[str] = Field(None, max_length=10)
    comments: Optional[str] = Field(None, max_length=1000)
    technician: Optional[str] = Field(None, max_length=200)


class TestResultResponse(TestResultBase):
    """Schema for test result API response"""
    id: int
    result_id: str
    test_datetime: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


# Equipment schemas
class EquipmentBase(BaseSchema):
    """Base equipment schema"""
    equipment_id: str = Field(..., description="Unique equipment identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Equipment name")
    manufacturer: Optional[str] = Field(None, max_length=100, description="Manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Equipment model")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number")
    equipment_type: EquipmentType = Field(..., description="Equipment type")
    location: Optional[str] = Field(None, max_length=200, description="Equipment location")
    communication_protocol: Optional[CommunicationProtocol] = Field(None, description="Communication protocol")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address for network equipment")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Network port")
    serial_port: Optional[str] = Field(None, max_length=50, description="Serial port")
    baud_rate: Optional[int] = Field(None, description="Serial baud rate")
    supported_tests: Optional[List[str]] = Field(None, description="List of supported test codes")
    sample_types: Optional[List[str]] = Field(None, description="List of supported sample types")
    is_active: bool = Field(True, description="Whether equipment is active")


class EquipmentCreate(EquipmentBase):
    """Schema for creating new equipment"""
    pass


class EquipmentUpdate(BaseSchema):
    """Schema for updating equipment"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    equipment_type: Optional[EquipmentType] = None
    location: Optional[str] = Field(None, max_length=200)
    status: Optional[EquipmentStatus] = None
    communication_protocol: Optional[CommunicationProtocol] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = Field(None, ge=1, le=65535)
    serial_port: Optional[str] = Field(None, max_length=50)
    baud_rate: Optional[int] = None
    supported_tests: Optional[List[str]] = None
    sample_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EquipmentResponse(EquipmentBase):
    """Schema for equipment API response"""
    id: int
    status: EquipmentStatus
    last_maintenance: Optional[datetime] = None
    next_maintenance: Optional[datetime] = None
    calibration_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Communication schemas
class HL7MessageRequest(BaseSchema):
    """Schema for HL7 message request"""
    message: str = Field(..., description="HL7 message content")
    device_id: Optional[str] = Field(None, description="Source device ID")


class HL7MessageResponse(BaseSchema):
    """Schema for HL7 message response"""
    success: bool = Field(..., description="Whether message was processed successfully")
    message_type: Optional[str] = Field(None, description="Type of HL7 message")
    patient_id: Optional[str] = Field(None, description="Patient ID from message")
    order_number: Optional[str] = Field(None, description="Order number from message")
    errors: Optional[List[str]] = Field(None, description="List of processing errors")
    warnings: Optional[List[str]] = Field(None, description="List of processing warnings")


# Device status schemas
class DeviceStatusResponse(BaseSchema):
    """Schema for device status response"""
    device_id: str = Field(..., description="Device identifier")
    connection_status: str = Field(..., description="Connection status")
    equipment_status: str = Field(..., description="Equipment status")
    is_online: bool = Field(..., description="Whether device is online")
    last_communication: Optional[str] = Field(None, description="Last communication timestamp")
    message_count: int = Field(0, description="Number of messages processed")
    error_count: int = Field(0, description="Number of errors")
    configuration: Dict[str, Any] = Field({}, description="Device configuration")


class DeviceListResponse(BaseSchema):
    """Schema for device list response"""
    devices: List[DeviceStatusResponse] = Field(..., description="List of device statuses")
    total_devices: int = Field(..., description="Total number of devices")


# Error schemas
class ErrorResponse(BaseSchema):
    """Schema for error responses"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: str = Field(..., description="Error timestamp")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return datetime.utcnow().isoformat()


# Health check schema
class HealthCheckResponse(BaseSchema):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")


# Statistics schemas
class TestStatistics(BaseSchema):
    """Schema for test statistics"""
    total_orders: int = Field(0, description="Total number of orders")
    pending_orders: int = Field(0, description="Number of pending orders")
    completed_orders: int = Field(0, description="Number of completed orders")
    failed_orders: int = Field(0, description="Number of failed orders")
    total_results: int = Field(0, description="Total number of results")
    average_turnaround_time: Optional[float] = Field(None, description="Average turnaround time in hours")


class EquipmentStatistics(BaseSchema):
    """Schema for equipment statistics"""
    total_equipment: int = Field(0, description="Total number of equipment")
    active_equipment: int = Field(0, description="Number of active equipment")
    online_equipment: int = Field(0, description="Number of online equipment")
    equipment_utilization: Dict[str, float] = Field({}, description="Equipment utilization rates")


class SystemStatistics(BaseSchema):
    """Schema for system statistics"""
    test_stats: TestStatistics = Field(..., description="Test-related statistics")
    equipment_stats: EquipmentStatistics = Field(..., description="Equipment-related statistics")
    uptime: float = Field(0, description="System uptime in hours")
    message_throughput: float = Field(0, description="Messages per minute")
    error_rate: float = Field(0, description="Error rate percentage") 