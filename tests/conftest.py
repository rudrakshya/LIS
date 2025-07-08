"""
Pytest configuration and fixtures for Laboratory Information System tests
"""

import pytest
import asyncio
from datetime import datetime, date
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from src.core.database import Base, get_database_session
from src.core.config import settings
from src.models import (
    Patient, TestOrder, Sample, TestResult, Equipment,
    Gender, OrderStatus, SampleType, EquipmentType, EquipmentStatus,
    CommunicationProtocol
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Create a test database"""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestSessionLocal
    
    # Cleanup is automatic with in-memory database


@pytest.fixture
def db_session(test_db):
    """Create a database session for testing"""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_patient(db_session) -> Patient:
    """Create a sample patient for testing"""
    patient = Patient(
        patient_id="TEST001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1980, 1, 1),
        gender=Gender.MALE,
        phone="555-0123",
        email="john.doe@example.com",
        address="123 Test St, Test City, TC 12345"
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def sample_equipment(db_session) -> Equipment:
    """Create sample equipment for testing"""
    equipment = Equipment(
        equipment_id="ANALYZER001",
        name="Test Analyzer",
        manufacturer="Test Corp",
        model="TA-1000",
        serial_number="12345",
        equipment_type=EquipmentType.ANALYZER,
        status=EquipmentStatus.OPERATIONAL,
        location="Lab Room 1",
        communication_protocol=CommunicationProtocol.TCP_IP,
        ip_address="192.168.1.100",
        port=8080,
        supported_tests=["CBC", "BMP", "LIPID"],
        sample_types=["BLOOD", "SERUM"],
        is_active=True
    )
    db_session.add(equipment)
    db_session.commit()
    db_session.refresh(equipment)
    return equipment


@pytest.fixture
def sample_test_order(db_session, sample_patient) -> TestOrder:
    """Create a sample test order for testing"""
    order = TestOrder(
        order_number="ORD001",
        patient_id=sample_patient.patient_id,
        test_code="CBC",
        test_name="Complete Blood Count",
        status=OrderStatus.PENDING,
        priority="ROUTINE",
        physician="Dr. Smith",
        department="Internal Medicine"
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def sample_sample(db_session, sample_test_order) -> Sample:
    """Create a sample for testing"""
    sample = Sample(
        sample_id="SAMPLE001",
        test_order_id=sample_test_order.id,
        sample_type=SampleType.BLOOD,
        collection_date=datetime.utcnow(),
        received_date=datetime.utcnow(),
        volume=5.0,
        container_type="EDTA Tube",
        collection_site="Left Arm",
        collector="Nurse Johnson"
    )
    db_session.add(sample)
    db_session.commit()
    db_session.refresh(sample)
    return sample


@pytest.fixture
def sample_test_result(db_session, sample_test_order, sample_equipment) -> TestResult:
    """Create a sample test result for testing"""
    result = TestResult(
        result_id="RES001",
        test_order_id=sample_test_order.id,
        test_code="CBC",
        test_name="Complete Blood Count",
        result_value="Normal",
        result_unit="",
        reference_range="Normal",
        result_status="FINAL",
        equipment_id=sample_equipment.equipment_id,
        technician="Tech Davis",
        test_datetime=datetime.utcnow()
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


@pytest.fixture
def hl7_message_orm():
    """Sample HL7 ORM (Order) message for testing"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return (
        f"MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|{timestamp}||ORM^O01|MSG001|P|2.5\r"
        "PID|1||TEST001||Doe^John||19800101|M|||123 Test St^^Test City^TC^12345\r"
        "ORC|NW|ORD001|||||||20231201120000\r"
        "OBR|1|ORD001||CBC^Complete Blood Count|||20231201120000\r"
    )


@pytest.fixture
def hl7_message_oru():
    """Sample HL7 ORU (Result) message for testing"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return (
        f"MSH|^~\\&|ANALYZER|DEVICE|LIS|LAB|{timestamp}||ORU^R01|MSG002|P|2.5\r"
        "PID|1||TEST001||Doe^John||19800101|M\r"
        "OBR|1|ORD001||CBC^Complete Blood Count|||20231201120000\r"
        "OBX|1|ST|WBC^White Blood Count||7.5|10^3/uL|4.0-11.0|N|||F\r"
        "OBX|2|ST|RBC^Red Blood Count||4.5|10^6/uL|4.2-5.4|N|||F\r"
        "OBX|3|ST|HGB^Hemoglobin||14.0|g/dL|12.0-16.0|N|||F\r"
    )


@pytest.fixture
def astm_message():
    """Sample ASTM message for testing"""
    return (
        "H|\\^&|||LIS|||||||||20231201120000\r\n"
        "P|1||TEST001||Doe^John||19800101|M\r\n"
        "O|1|ORD001||^^^CBC|R||20231201120000\r\n"
        "R|1|^^^WBC|7.5|10^3/uL|4.0-11.0|N||F\r\n"
        "R|2|^^^RBC|4.5|10^6/uL|4.2-5.4|N||F\r\n"
        "R|3|^^^HGB|14.0|g/dL|12.0-16.0|N||F\r\n"
        "L|1|N\r\n"
    )


@pytest.fixture
def json_test_result():
    """Sample JSON test result message for testing"""
    return {
        "type": "test_result",
        "device_id": "ANALYZER001",
        "order_number": "ORD001",
        "patient_id": "TEST001",
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "results": [
            {
                "analyte": "WBC",
                "value": "7.5",
                "unit": "10^3/uL",
                "reference_range": "4.0-11.0",
                "flag": "N"
            },
            {
                "analyte": "RBC", 
                "value": "4.5",
                "unit": "10^6/uL",
                "reference_range": "4.2-5.4",
                "flag": "N"
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    fd, path = tempfile.mkstemp()
    try:
        yield path
    finally:
        os.close(fd)
        os.unlink(path)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    class MockSettings:
        def __init__(self):
            self.app_name = "Test LIS"
            self.app_version = "1.0.0-test"
            self.environment = "test"
            
            # Database settings
            self.database_url = "sqlite:///:memory:"
            
            # Communication settings
            self.communication = type('obj', (object,), {
                'tcp_host': '127.0.0.1',
                'tcp_port': 8888,
                'tcp_timeout': 30,
                'tcp_buffer_size': 4096,
                'tcp_auth_token': 'test_token',
                'max_client_errors': 5,
                'serial_timeout': 5
            })()
            
            # Device settings
            self.devices = type('obj', (object,), {
                'device_timeout': 10,
                'device_scan_interval': 30,
                'response_timeout': 5
            })()
            
            # API settings
            self.api = type('obj', (object,), {
                'host': '127.0.0.1',
                'port': 8000,
                'cors_origins': ['*'],
                'cors_methods': ['*'],
                'cors_headers': ['*']
            })()
            
            # Logging settings
            self.logging = type('obj', (object,), {
                'log_level': 'DEBUG'
            })()
    
    return MockSettings()


# Async test helpers
@pytest.fixture
async def async_db_session(test_db):
    """Create an async database session for testing"""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


# Mock classes for testing
class MockStreamReader:
    """Mock StreamReader for testing"""
    def __init__(self, data: bytes = b""):
        self.data = data
        self.position = 0
    
    async def read(self, n: int = -1) -> bytes:
        if self.position >= len(self.data):
            return b""
        
        if n == -1:
            result = self.data[self.position:]
            self.position = len(self.data)
        else:
            result = self.data[self.position:self.position + n]
            self.position += len(result)
        
        return result
    
    async def readuntil(self, separator: bytes = b'\r\n') -> bytes:
        start = self.position
        sep_pos = self.data.find(separator, start)
        
        if sep_pos == -1:
            # No separator found, return remaining data
            result = self.data[start:]
            self.position = len(self.data)
        else:
            # Include separator in result
            result = self.data[start:sep_pos + len(separator)]
            self.position = sep_pos + len(separator)
        
        return result


class MockStreamWriter:
    """Mock StreamWriter for testing"""
    def __init__(self):
        self.data = b""
        self.closed = False
    
    def write(self, data: bytes):
        if not self.closed:
            self.data += data
    
    async def drain(self):
        pass
    
    def close(self):
        self.closed = True
    
    async def wait_closed(self):
        pass
    
    def is_closing(self) -> bool:
        return self.closed
    
    def get_extra_info(self, name: str):
        if name == 'peername':
            return ('127.0.0.1', 12345)
        return None


@pytest.fixture
def mock_stream_reader():
    """Create a mock stream reader for testing"""
    return MockStreamReader


@pytest.fixture
def mock_stream_writer():
    """Create a mock stream writer for testing"""
    return MockStreamWriter


# Test data generators
def generate_patient_data(**overrides):
    """Generate test patient data"""
    data = {
        "patient_id": "TEST001",
        "first_name": "John",
        "last_name": "Doe", 
        "date_of_birth": date(1980, 1, 1),
        "gender": Gender.MALE,
        "phone": "555-0123",
        "email": "john.doe@example.com"
    }
    data.update(overrides)
    return data


def generate_order_data(**overrides):
    """Generate test order data"""
    data = {
        "order_number": "ORD001",
        "patient_id": "TEST001",
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "status": OrderStatus.PENDING,
        "priority": "ROUTINE"
    }
    data.update(overrides)
    return data


def generate_equipment_data(**overrides):
    """Generate test equipment data"""
    data = {
        "equipment_id": "ANALYZER001",
        "name": "Test Analyzer",
        "manufacturer": "Test Corp",
        "model": "TA-1000",
        "equipment_type": EquipmentType.ANALYZER,
        "status": EquipmentStatus.OPERATIONAL,
        "communication_protocol": CommunicationProtocol.TCP_IP,
        "ip_address": "192.168.1.100",
        "port": 8080,
        "is_active": True
    }
    data.update(overrides)
    return data 