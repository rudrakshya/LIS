"""
Unit tests for HL7 message handler
"""

import pytest
from datetime import datetime

from src.communication.hl7_handler import HL7Handler, HL7Parser
from src.core.exceptions import HL7Exception


class TestHL7Parser:
    """Test HL7 message parsing functionality"""
    
    def test_parse_msh_segment(self):
        """Test parsing MSH (Message Header) segment"""
        parser = HL7Parser()
        msh_segment = "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||ORM^O01|MSG001|P|2.5"
        
        result = parser.parse_msh_segment(msh_segment)
        
        assert result['sending_application'] == 'LIS'
        assert result['sending_facility'] == 'LAB'
        assert result['receiving_application'] == 'ANALYZER'
        assert result['receiving_facility'] == 'DEVICE'
        assert result['message_type'] == 'ORM^O01'
        assert result['message_control_id'] == 'MSG001'
        assert result['processing_id'] == 'P'
        assert result['version_id'] == '2.5'
    
    def test_parse_pid_segment(self):
        """Test parsing PID (Patient Identification) segment"""
        parser = HL7Parser()
        pid_segment = "PID|1||TEST001||Doe^John^Middle||19800101|M|||123 Test St^^Test City^TC^12345||555-0123|||||||||||||||||"
        
        result = parser.parse_pid_segment(pid_segment)
        
        assert result['patient_id'] == 'TEST001'
        assert result['last_name'] == 'Doe'
        assert result['first_name'] == 'John'
        assert result['middle_name'] == 'Middle'
        assert result['date_of_birth'] == '19800101'
        assert result['gender'] == 'M'
        assert result['address'] == '123 Test St^^Test City^TC^12345'
        assert result['phone'] == '555-0123'
    
    def test_parse_orc_segment(self):
        """Test parsing ORC (Common Order) segment"""
        parser = HL7Parser()
        orc_segment = "ORC|NW|ORD001|EXT001||CM|||20231201120000|||Dr. Smith|||||||||"
        
        result = parser.parse_orc_segment(orc_segment)
        
        assert result['order_control'] == 'NW'
        assert result['placer_order_number'] == 'ORD001'
        assert result['filler_order_number'] == 'EXT001'
        assert result['order_status'] == 'CM'
        assert result['ordering_provider'] == 'Dr. Smith'
    
    def test_parse_obr_segment(self):
        """Test parsing OBR (Observation Request) segment"""
        parser = HL7Parser()
        obr_segment = "OBR|1|ORD001|EXT001|CBC^Complete Blood Count^L||20231201120000|20231201130000||||||||Dr. Smith|||||||||||"
        
        result = parser.parse_obr_segment(obr_segment)
        
        assert result['set_id'] == '1'
        assert result['placer_order_number'] == 'ORD001'
        assert result['filler_order_number'] == 'EXT001'
        assert result['test_code'] == 'CBC'
        assert result['test_name'] == 'Complete Blood Count'
        assert result['observation_datetime'] == '20231201120000'
        assert result['ordering_provider'] == 'Dr. Smith'
    
    def test_parse_obx_segment(self):
        """Test parsing OBX (Observation Result) segment"""
        parser = HL7Parser()
        obx_segment = "OBX|1|ST|WBC^White Blood Count^L||7.5|10^3/uL|4.0-11.0|N|||F|||20231201130000"
        
        result = parser.parse_obx_segment(obx_segment)
        
        assert result['set_id'] == '1'
        assert result['value_type'] == 'ST'
        assert result['observation_identifier'] == 'WBC'
        assert result['observation_name'] == 'White Blood Count'
        assert result['observation_value'] == '7.5'
        assert result['units'] == '10^3/uL'
        assert result['reference_range'] == '4.0-11.0'
        assert result['abnormal_flags'] == 'N'
        assert result['result_status'] == 'F'
    
    def test_parse_invalid_segment(self):
        """Test parsing invalid segment"""
        parser = HL7Parser()
        
        with pytest.raises(HL7Exception):
            parser.parse_msh_segment("INVALID|SEGMENT")
    
    def test_parse_empty_segment(self):
        """Test parsing empty segment"""
        parser = HL7Parser()
        
        with pytest.raises(HL7Exception):
            parser.parse_msh_segment("")


class TestHL7Handler:
    """Test HL7 message handler functionality"""
    
    def test_process_orm_message(self, hl7_message_orm):
        """Test processing ORM (Order) message"""
        handler = HL7Handler()
        
        result = handler.process_message(hl7_message_orm)
        
        assert result['success'] is True
        assert result['message_type'] == 'ORM^O01'
        assert result['patient_id'] == 'TEST001'
        assert result['order_number'] == 'ORD001'
        assert 'patient_data' in result
        assert 'order_data' in result
        
        # Check patient data
        patient_data = result['patient_data']
        assert patient_data['patient_id'] == 'TEST001'
        assert patient_data['last_name'] == 'Doe'
        assert patient_data['first_name'] == 'John'
        assert patient_data['gender'] == 'M'
        
        # Check order data
        order_data = result['order_data']
        assert order_data['order_number'] == 'ORD001'
        assert order_data['test_code'] == 'CBC'
        assert order_data['test_name'] == 'Complete Blood Count'
    
    def test_process_oru_message(self, hl7_message_oru):
        """Test processing ORU (Result) message"""
        handler = HL7Handler()
        
        result = handler.process_message(hl7_message_oru)
        
        assert result['success'] is True
        assert result['message_type'] == 'ORU^R01'
        assert result['patient_id'] == 'TEST001'
        assert result['order_number'] == 'ORD001'
        assert 'patient_data' in result
        assert 'results' in result
        
        # Check results
        results = result['results']
        assert len(results) == 3
        
        # Check first result (WBC)
        wbc_result = results[0]
        assert wbc_result['test_code'] == 'WBC'
        assert wbc_result['test_name'] == 'White Blood Count'
        assert wbc_result['result_value'] == '7.5'
        assert wbc_result['units'] == '10^3/uL'
        assert wbc_result['reference_range'] == '4.0-11.0'
        assert wbc_result['abnormal_flag'] == 'N'
    
    def test_process_invalid_message(self):
        """Test processing invalid HL7 message"""
        handler = HL7Handler()
        invalid_message = "INVALID MESSAGE FORMAT"
        
        result = handler.process_message(invalid_message)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid HL7 message format' in result['error']
    
    def test_process_empty_message(self):
        """Test processing empty message"""
        handler = HL7Handler()
        
        result = handler.process_message("")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Empty message' in result['error']
    
    def test_process_message_without_msh(self):
        """Test processing message without MSH segment"""
        handler = HL7Handler()
        message = "PID|1||TEST001||Doe^John||19800101|M\rOBR|1|ORD001||CBC^Complete Blood Count\r"
        
        result = handler.process_message(message)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'MSH segment not found' in result['error']
    
    def test_create_ack_message(self):
        """Test creating ACK message"""
        handler = HL7Handler()
        original_message = "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||ORM^O01|MSG001|P|2.5\r"
        
        ack_message = handler.create_ack_message(original_message, "AA")
        
        assert ack_message.startswith("MSH|")
        assert "ACK" in ack_message
        assert "MSG001" in ack_message
        assert "MSA|AA|MSG001" in ack_message
    
    def test_validate_message_structure(self):
        """Test message structure validation"""
        handler = HL7Handler()
        
        # Valid message structure
        valid_message = "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||ORM^O01|MSG001|P|2.5\rPID|1||TEST001||Doe^John\r"
        assert handler.validate_message_structure(valid_message) is True
        
        # Invalid message structure (no MSH)
        invalid_message = "PID|1||TEST001||Doe^John\r"
        assert handler.validate_message_structure(invalid_message) is False
    
    def test_extract_patient_demographics(self, hl7_message_orm):
        """Test extracting patient demographics from message"""
        handler = HL7Handler()
        
        patient_data = handler.extract_patient_demographics(hl7_message_orm)
        
        assert patient_data['patient_id'] == 'TEST001'
        assert patient_data['last_name'] == 'Doe'
        assert patient_data['first_name'] == 'John'
        assert patient_data['date_of_birth'] == '19800101'
        assert patient_data['gender'] == 'M'
        assert patient_data['address'] == '123 Test St^^Test City^TC^12345'
    
    def test_extract_order_information(self, hl7_message_orm):
        """Test extracting order information from message"""
        handler = HL7Handler()
        
        order_data = handler.extract_order_information(hl7_message_orm)
        
        assert order_data['order_number'] == 'ORD001'
        assert order_data['test_code'] == 'CBC'
        assert order_data['test_name'] == 'Complete Blood Count'
        assert order_data['order_control'] == 'NW'
    
    def test_extract_results(self, hl7_message_oru):
        """Test extracting results from ORU message"""
        handler = HL7Handler()
        
        results = handler.extract_results(hl7_message_oru)
        
        assert len(results) == 3
        
        # Check each result
        expected_results = [
            {'code': 'WBC', 'name': 'White Blood Count', 'value': '7.5', 'unit': '10^3/uL'},
            {'code': 'RBC', 'name': 'Red Blood Count', 'value': '4.5', 'unit': '10^6/uL'},
            {'code': 'HGB', 'name': 'Hemoglobin', 'value': '14.0', 'unit': 'g/dL'}
        ]
        
        for i, expected in enumerate(expected_results):
            assert results[i]['test_code'] == expected['code']
            assert results[i]['test_name'] == expected['name']
            assert results[i]['result_value'] == expected['value']
            assert results[i]['units'] == expected['unit']
    
    def test_parse_datetime(self):
        """Test parsing HL7 datetime format"""
        handler = HL7Handler()
        
        # Test full datetime
        dt1 = handler.parse_datetime("20231201120000")
        assert dt1.year == 2023
        assert dt1.month == 12
        assert dt1.day == 1
        assert dt1.hour == 12
        assert dt1.minute == 0
        assert dt1.second == 0
        
        # Test date only
        dt2 = handler.parse_datetime("20231201")
        assert dt2.year == 2023
        assert dt2.month == 12
        assert dt2.day == 1
        assert dt2.hour == 0
        assert dt2.minute == 0
        assert dt2.second == 0
        
        # Test invalid format
        assert handler.parse_datetime("invalid") is None
        assert handler.parse_datetime("") is None
    
    def test_format_datetime(self):
        """Test formatting datetime to HL7 format"""
        handler = HL7Handler()
        
        dt = datetime(2023, 12, 1, 12, 30, 45)
        formatted = handler.format_datetime(dt)
        
        assert formatted == "20231201123045"
    
    def test_escape_hl7_text(self):
        """Test escaping special characters in HL7 text"""
        handler = HL7Handler()
        
        # Test escaping special characters
        text = "Test & Data | More ^ Data ~ Extra \\ Data"
        escaped = handler.escape_hl7_text(text)
        
        assert "\\E\\" in escaped  # & becomes \E\
        assert "\\F\\" in escaped  # | becomes \F\
        assert "\\S\\" in escaped  # ^ becomes \S\
        assert "\\T\\" in escaped  # ~ becomes \T\
        assert "\\E\\" in escaped  # \ becomes \E\
    
    def test_unescape_hl7_text(self):
        """Test unescaping HL7 text"""
        handler = HL7Handler()
        
        escaped_text = "Test \\E\\ Data \\F\\ More \\S\\ Data \\T\\ Extra"
        unescaped = handler.unescape_hl7_text(escaped_text)
        
        assert "&" in unescaped
        assert "|" in unescaped
        assert "^" in unescaped
        assert "~" in unescaped


class TestHL7MessageTypes:
    """Test different HL7 message types"""
    
    def test_adm_message_processing(self):
        """Test ADT (Admit/Discharge/Transfer) message processing"""
        handler = HL7Handler()
        
        adt_message = (
            "MSH|^~\\&|HIS|HOSPITAL|LIS|LAB|20231201120000||ADT^A01|MSG003|P|2.5\r"
            "PID|1||TEST002||Smith^Jane||19900215|F|||456 Oak St^^City^ST^67890\r"
            "PV1|1|I|ICU^101^1|||Dr. Johnson||||||||||||V\r"
        )
        
        result = handler.process_message(adt_message)
        
        assert result['success'] is True
        assert result['message_type'] == 'ADT^A01'
        assert result['patient_id'] == 'TEST002'
        assert 'patient_data' in result
    
    def test_ack_message_processing(self):
        """Test ACK (Acknowledgment) message processing"""
        handler = HL7Handler()
        
        ack_message = (
            "MSH|^~\\&|ANALYZER|DEVICE|LIS|LAB|20231201120000||ACK|MSG001|P|2.5\r"
            "MSA|AA|MSG001\r"
        )
        
        result = handler.process_message(ack_message)
        
        assert result['success'] is True
        assert result['message_type'] == 'ACK'
        assert 'acknowledgment_code' in result
        assert result['acknowledgment_code'] == 'AA'


class TestHL7ErrorHandling:
    """Test HL7 error handling scenarios"""
    
    def test_malformed_segment_handling(self):
        """Test handling of malformed segments"""
        handler = HL7Handler()
        
        # Message with malformed PID segment (missing required fields)
        malformed_message = (
            "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||ORM^O01|MSG001|P|2.5\r"
            "PID|\r"  # Malformed PID segment
            "OBR|1|ORD001||CBC^Complete Blood Count\r"
        )
        
        result = handler.process_message(malformed_message)
        
        # Should still succeed but with warnings
        assert result['success'] is True
        assert 'warnings' in result
    
    def test_missing_required_segments(self):
        """Test handling of missing required segments"""
        handler = HL7Handler()
        
        # ORM message without OBR segment
        incomplete_message = (
            "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||ORM^O01|MSG001|P|2.5\r"
            "PID|1||TEST001||Doe^John||19800101|M\r"
            # Missing OBR segment
        )
        
        result = handler.process_message(incomplete_message)
        
        # Should fail or succeed with warnings depending on implementation
        assert 'warnings' in result or result['success'] is False
    
    def test_unsupported_message_type(self):
        """Test handling of unsupported message types"""
        handler = HL7Handler()
        
        unsupported_message = (
            "MSH|^~\\&|LIS|LAB|ANALYZER|DEVICE|20231201120000||XXX^Y01|MSG001|P|2.5\r"
            "PID|1||TEST001||Doe^John||19800101|M\r"
        )
        
        result = handler.process_message(unsupported_message)
        
        # Should succeed but mark as unsupported
        assert result['success'] is True
        assert result['message_type'] == 'XXX^Y01'
        assert 'warnings' in result or 'unsupported_type' in result


class TestHL7Utilities:
    """Test HL7 utility functions"""
    
    def test_segment_parsing(self):
        """Test utility functions for segment parsing"""
        parser = HL7Parser()
        
        # Test field splitting
        segment = "PID|1||TEST001||Doe^John^Middle||19800101|M"
        fields = parser.split_segment_fields(segment)
        
        assert len(fields) >= 8
        assert fields[0] == "PID"
        assert fields[3] == "TEST001"
        assert fields[5] == "Doe^John^Middle"
    
    def test_component_parsing(self):
        """Test parsing field components"""
        parser = HL7Parser()
        
        name_field = "Doe^John^Middle^Jr^Dr"
        components = parser.split_field_components(name_field)
        
        assert len(components) == 5
        assert components[0] == "Doe"
        assert components[1] == "John"
        assert components[2] == "Middle"
        assert components[3] == "Jr"
        assert components[4] == "Dr"
    
    def test_subcomponent_parsing(self):
        """Test parsing field subcomponents"""
        parser = HL7Parser()
        
        address_field = "123 Main St&Apt 2^City^ST^12345"
        components = parser.split_field_components(address_field)
        
        # Test subcomponent splitting
        street_subcomponents = parser.split_subcomponents(components[0])
        assert len(street_subcomponents) == 2
        assert street_subcomponents[0] == "123 Main St"
        assert street_subcomponents[1] == "Apt 2" 