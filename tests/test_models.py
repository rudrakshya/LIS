"""
Unit tests for Laboratory Information System models
"""

import pytest
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError

from src.models import (
    Patient, TestOrder, Sample, TestResult, Equipment,
    Gender, OrderStatus, SampleType, EquipmentType, EquipmentStatus,
    CommunicationProtocol
)
from tests.conftest import generate_patient_data, generate_order_data, generate_equipment_data


class TestPatientModel:
    """Test Patient model functionality"""
    
    def test_create_patient(self, db_session):
        """Test creating a patient"""
        patient_data = generate_patient_data()
        patient = Patient(**patient_data)
        
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
        
        assert patient.id is not None
        assert patient.patient_id == "TEST001"
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.gender == Gender.MALE
        assert patient.created_at is not None
    
    def test_patient_unique_constraint(self, db_session):
        """Test patient_id unique constraint"""
        patient_data = generate_patient_data()
        
        # Create first patient
        patient1 = Patient(**patient_data)
        db_session.add(patient1)
        db_session.commit()
        
        # Try to create another patient with same patient_id
        patient2 = Patient(**patient_data)
        db_session.add(patient2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_patient_validation(self, db_session):
        """Test patient data validation"""
        # Test invalid email
        patient_data = generate_patient_data(email="invalid-email")
        patient = Patient(**patient_data)
        
        # Note: Email validation would be done at the application layer
        # Here we just test that the model accepts the data
        assert patient.email == "invalid-email"
    
    def test_patient_relationships(self, db_session, sample_patient):
        """Test patient relationships with orders"""
        # Create a test order
        order = TestOrder(
            order_number="ORD001",
            patient_id=sample_patient.patient_id,
            test_code="CBC",
            test_name="Complete Blood Count",
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        db_session.commit()
        
        # Check relationship
        db_session.refresh(sample_patient)
        assert len(sample_patient.test_orders) == 1
        assert sample_patient.test_orders[0].order_number == "ORD001"
    
    def test_patient_str_representation(self, sample_patient):
        """Test patient string representation"""
        expected = "Patient(TEST001: Doe, John)"
        assert str(sample_patient) == expected


class TestTestOrderModel:
    """Test TestOrder model functionality"""
    
    def test_create_test_order(self, db_session, sample_patient):
        """Test creating a test order"""
        order_data = generate_order_data(patient_id=sample_patient.patient_id)
        order = TestOrder(**order_data)
        
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        assert order.id is not None
        assert order.order_number == "ORD001"
        assert order.patient_id == sample_patient.patient_id
        assert order.status == OrderStatus.PENDING
        assert order.created_at is not None
    
    def test_order_unique_constraint(self, db_session, sample_patient):
        """Test order_number unique constraint"""
        order_data = generate_order_data(patient_id=sample_patient.patient_id)
        
        # Create first order
        order1 = TestOrder(**order_data)
        db_session.add(order1)
        db_session.commit()
        
        # Try to create another order with same order_number
        order2 = TestOrder(**order_data)
        db_session.add(order2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_order_status_transitions(self, db_session, sample_test_order):
        """Test order status transitions"""
        # Test status update
        sample_test_order.status = OrderStatus.IN_PROGRESS
        sample_test_order.updated_at = datetime.utcnow()
        db_session.commit()
        
        db_session.refresh(sample_test_order)
        assert sample_test_order.status == OrderStatus.IN_PROGRESS
        assert sample_test_order.updated_at is not None
    
    def test_order_completion(self, db_session, sample_test_order):
        """Test order completion"""
        # Complete the order
        sample_test_order.status = OrderStatus.COMPLETED
        sample_test_order.completed_at = datetime.utcnow()
        sample_test_order.updated_at = datetime.utcnow()
        db_session.commit()
        
        db_session.refresh(sample_test_order)
        assert sample_test_order.status == OrderStatus.COMPLETED
        assert sample_test_order.completed_at is not None


class TestSampleModel:
    """Test Sample model functionality"""
    
    def test_create_sample(self, db_session, sample_test_order):
        """Test creating a sample"""
        sample = Sample(
            sample_id="SAMPLE001",
            test_order_id=sample_test_order.id,
            sample_type=SampleType.BLOOD,
            collection_date=datetime.utcnow(),
            volume=5.0,
            container_type="EDTA Tube"
        )
        
        db_session.add(sample)
        db_session.commit()
        db_session.refresh(sample)
        
        assert sample.id is not None
        assert sample.sample_id == "SAMPLE001"
        assert sample.test_order_id == sample_test_order.id
        assert sample.sample_type == SampleType.BLOOD
        assert sample.volume == 5.0
    
    def test_sample_relationships(self, db_session, sample_sample):
        """Test sample relationships"""
        # Check relationship with test order
        assert sample_sample.test_order is not None
        assert sample_sample.test_order.order_number == "ORD001"
    
    def test_sample_validation(self, db_session, sample_test_order):
        """Test sample validation"""
        # Test negative volume should be handled at application level
        sample = Sample(
            sample_id="SAMPLE002",
            test_order_id=sample_test_order.id,
            sample_type=SampleType.BLOOD,
            volume=-1.0  # Negative volume
        )
        
        # Model should accept this, validation at application layer
        db_session.add(sample)
        db_session.commit()
        assert sample.volume == -1.0


class TestTestResultModel:
    """Test TestResult model functionality"""
    
    def test_create_test_result(self, db_session, sample_test_order, sample_equipment):
        """Test creating a test result"""
        result = TestResult(
            result_id="RES001",
            test_order_id=sample_test_order.id,
            test_code="CBC",
            test_name="Complete Blood Count",
            result_value="7.5",
            result_unit="10^3/uL",
            reference_range="4.0-11.0",
            result_status="FINAL",
            equipment_id=sample_equipment.equipment_id,
            test_datetime=datetime.utcnow()
        )
        
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        assert result.id is not None
        assert result.result_id == "RES001"
        assert result.test_order_id == sample_test_order.id
        assert result.result_value == "7.5"
        assert result.result_unit == "10^3/uL"
        assert result.equipment_id == sample_equipment.equipment_id
    
    def test_result_relationships(self, db_session, sample_test_result):
        """Test test result relationships"""
        # Check relationship with test order
        assert sample_test_result.test_order is not None
        assert sample_test_result.test_order.order_number == "ORD001"
        
        # Check relationship with equipment
        assert sample_test_result.equipment is not None
        assert sample_test_result.equipment.equipment_id == "ANALYZER001"
    
    def test_abnormal_flag_handling(self, db_session, sample_test_order):
        """Test abnormal flag handling"""
        result = TestResult(
            result_id="RES002",
            test_order_id=sample_test_order.id,
            test_code="WBC",
            test_name="White Blood Count",
            result_value="15.0",
            result_unit="10^3/uL",
            reference_range="4.0-11.0",
            abnormal_flag="H",  # High
            result_status="FINAL",
            test_datetime=datetime.utcnow()
        )
        
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        assert result.abnormal_flag == "H"


class TestEquipmentModel:
    """Test Equipment model functionality"""
    
    def test_create_equipment(self, db_session):
        """Test creating equipment"""
        equipment_data = generate_equipment_data()
        equipment = Equipment(**equipment_data)
        
        db_session.add(equipment)
        db_session.commit()
        db_session.refresh(equipment)
        
        assert equipment.id is not None
        assert equipment.equipment_id == "ANALYZER001"
        assert equipment.name == "Test Analyzer"
        assert equipment.equipment_type == EquipmentType.ANALYZER
        assert equipment.status == EquipmentStatus.OPERATIONAL
        assert equipment.communication_protocol == CommunicationProtocol.TCP_IP
        assert equipment.is_active is True
    
    def test_equipment_unique_constraint(self, db_session):
        """Test equipment_id unique constraint"""
        equipment_data = generate_equipment_data()
        
        # Create first equipment
        equipment1 = Equipment(**equipment_data)
        db_session.add(equipment1)
        db_session.commit()
        
        # Try to create another equipment with same equipment_id
        equipment2 = Equipment(**equipment_data)
        db_session.add(equipment2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_equipment_status_updates(self, db_session, sample_equipment):
        """Test equipment status updates"""
        # Update equipment status
        sample_equipment.status = EquipmentStatus.MAINTENANCE
        sample_equipment.updated_at = datetime.utcnow()
        db_session.commit()
        
        db_session.refresh(sample_equipment)
        assert sample_equipment.status == EquipmentStatus.MAINTENANCE
        assert sample_equipment.updated_at is not None
    
    def test_equipment_maintenance_tracking(self, db_session, sample_equipment):
        """Test equipment maintenance tracking"""
        # Set maintenance dates
        now = datetime.utcnow()
        sample_equipment.last_maintenance = now
        sample_equipment.next_maintenance = now
        sample_equipment.calibration_date = now
        db_session.commit()
        
        db_session.refresh(sample_equipment)
        assert sample_equipment.last_maintenance == now
        assert sample_equipment.next_maintenance == now
        assert sample_equipment.calibration_date == now
    
    def test_equipment_communication_settings(self, db_session):
        """Test equipment communication settings"""
        # Test TCP/IP equipment
        tcp_equipment = Equipment(
            equipment_id="TCP_ANALYZER",
            name="TCP Analyzer",
            equipment_type=EquipmentType.ANALYZER,
            communication_protocol=CommunicationProtocol.TCP_IP,
            ip_address="192.168.1.100",
            port=8080,
            is_active=True
        )
        
        db_session.add(tcp_equipment)
        db_session.commit()
        
        assert tcp_equipment.ip_address == "192.168.1.100"
        assert tcp_equipment.port == 8080
        
        # Test Serial equipment
        serial_equipment = Equipment(
            equipment_id="SERIAL_ANALYZER",
            name="Serial Analyzer",
            equipment_type=EquipmentType.ANALYZER,
            communication_protocol=CommunicationProtocol.SERIAL,
            serial_port="/dev/ttyUSB0",
            baud_rate=9600,
            is_active=True
        )
        
        db_session.add(serial_equipment)
        db_session.commit()
        
        assert serial_equipment.serial_port == "/dev/ttyUSB0"
        assert serial_equipment.baud_rate == 9600
    
    def test_equipment_capabilities(self, db_session, sample_equipment):
        """Test equipment capabilities"""
        # Test supported tests and sample types
        assert "CBC" in sample_equipment.supported_tests
        assert "BMP" in sample_equipment.supported_tests
        assert "BLOOD" in sample_equipment.sample_types
        assert "SERUM" in sample_equipment.sample_types


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_patient_order_relationship(self, db_session, sample_patient, sample_test_order):
        """Test patient to order relationship"""
        # Refresh patient to load relationships
        db_session.refresh(sample_patient)
        
        assert len(sample_patient.test_orders) == 1
        assert sample_patient.test_orders[0].id == sample_test_order.id
        
        # Test reverse relationship
        assert sample_test_order.patient.id == sample_patient.id
    
    def test_order_sample_relationship(self, db_session, sample_test_order, sample_sample):
        """Test order to sample relationship"""
        # Refresh order to load relationships
        db_session.refresh(sample_test_order)
        
        assert len(sample_test_order.samples) == 1
        assert sample_test_order.samples[0].id == sample_sample.id
        
        # Test reverse relationship
        assert sample_sample.test_order.id == sample_test_order.id
    
    def test_order_result_relationship(self, db_session, sample_test_order, sample_test_result):
        """Test order to result relationship"""
        # Refresh order to load relationships
        db_session.refresh(sample_test_order)
        
        assert len(sample_test_order.test_results) == 1
        assert sample_test_order.test_results[0].id == sample_test_result.id
        
        # Test reverse relationship
        assert sample_test_result.test_order.id == sample_test_order.id
    
    def test_equipment_result_relationship(self, db_session, sample_equipment, sample_test_result):
        """Test equipment to result relationship"""
        # Refresh equipment to load relationships
        db_session.refresh(sample_equipment)
        
        assert len(sample_equipment.test_results) == 1
        assert sample_equipment.test_results[0].id == sample_test_result.id
        
        # Test reverse relationship
        assert sample_test_result.equipment.id == sample_equipment.id


class TestModelStringRepresentations:
    """Test string representations of models"""
    
    def test_patient_str(self, sample_patient):
        """Test patient string representation"""
        expected = "Patient(TEST001: Doe, John)"
        assert str(sample_patient) == expected
    
    def test_test_order_str(self, sample_test_order):
        """Test test order string representation"""
        expected = "TestOrder(ORD001: CBC for TEST001)"
        assert str(sample_test_order) == expected
    
    def test_sample_str(self, sample_sample):
        """Test sample string representation"""
        expected = "Sample(SAMPLE001: BLOOD for ORD001)"
        assert str(sample_sample) == expected
    
    def test_test_result_str(self, sample_test_result):
        """Test test result string representation"""
        expected = "TestResult(RES001: CBC = Normal)"
        assert str(sample_test_result) == expected
    
    def test_equipment_str(self, sample_equipment):
        """Test equipment string representation"""
        expected = "Equipment(ANALYZER001: Test Analyzer)"
        assert str(sample_equipment) == expected


class TestModelValidation:
    """Test model validation and constraints"""
    
    def test_required_fields(self, db_session):
        """Test that required fields are enforced"""
        # Test patient without required fields
        with pytest.raises(TypeError):
            Patient()  # Missing required fields
        
        # Test equipment without required fields
        with pytest.raises(TypeError):
            Equipment()  # Missing required fields
    
    def test_enum_validation(self, db_session):
        """Test enum field validation"""
        # Test valid enum values
        patient = Patient(
            patient_id="TEST002",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE
        )
        
        db_session.add(patient)
        db_session.commit()
        
        assert patient.gender == Gender.FEMALE
    
    def test_datetime_fields(self, db_session, sample_patient):
        """Test datetime field behavior"""
        # created_at should be set automatically
        assert sample_patient.created_at is not None
        assert isinstance(sample_patient.created_at, datetime)
        
        # updated_at starts as None
        assert sample_patient.updated_at is None
        
        # Update patient
        sample_patient.phone = "555-9999"
        sample_patient.updated_at = datetime.utcnow()
        db_session.commit()
        
        assert sample_patient.updated_at is not None 