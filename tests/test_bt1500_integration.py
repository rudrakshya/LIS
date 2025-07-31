"""
Test script for BT-1500 Sensacore analyzer integration
Tests parser, serial communication, and HL7 conversion
"""

import pytest
import asyncio
from datetime import datetime
from src.devices.parsers.bt1500_parser import BT1500Parser, BT1500Result
from src.communication.serial_handler import BT1500SerialHandler


class TestBT1500Parser:
    """Test BT-1500 data parser"""
    
    def setup_method(self):
        self.parser = BT1500Parser()
    
    def test_parse_calibration_report(self):
        """Test parsing calibration report data"""
        raw_data = """CALIBRATION REPORT
Na = 37.658 mV
K = 51.875 mV
iCa= 89.785 mV
Cl = 75.670 mV
pH = 39.877 mV
Na =56.412 mV
K = 69.519 mV
iCa= 78.291 mV
Cl = 58.429 mV
pH = 9.024 mV
Oct-31-13 12:18:29
_ _ _ _ _ _ _ _ _ _ _"""
        
        results = self.parser.parse_raw_data(raw_data)
        
        assert len(results) == 1
        result = results[0]
        assert result.test_type == 'CALIBRATION_REPORT'
        assert 'Na' in result.parameters
        assert result.parameters['Na'] == 37.658
        assert result.units['Na'] == 'mV'
    
    def test_parse_analyze_sample(self):
        """Test parsing analyze sample data"""
        raw_data = """ANALYZE REPORT
Na = 59.437 mV
K = 72.141 mV
iCa= 76.476 mV
Cl = 59.034 mV
pH = 4.285 mV
Na = 57.219 mV
K = 70.830 mV
iCa= 78.090 mV
Cl = 57.622 mV
pH = 8.318 mV
ANALYZE SAMPLE
Na =159.951 mmol/L HIGH
K =4.389 mmol/L HIGH
iCa=1.164 mmol/L HIGH
Cl =109.206 mmol/L HIGH
pH =7.487 mmol/L HIGH
Oct-31-13 12:27:32
_ _ _ _ _ _ _ _ _"""
        
        results = self.parser.parse_raw_data(raw_data)
        
        assert len(results) == 2  # ANALYZE_REPORT and ANALYZE_SAMPLE
        
        # Find analyze sample result
        sample_result = None
        for result in results:
            if result.test_type == 'ANALYZE_SAMPLE':
                sample_result = result
                break
        
        assert sample_result is not None
        assert sample_result.parameters['Na'] == 159.951
        assert sample_result.units['Na'] == 'mmol/L'
        assert sample_result.flags['Na'] == 'HIGH'
    
    def test_parse_calibration_slope(self):
        """Test parsing calibration slope data"""
        raw_data = """CALIBRATION SLOPE
Na =52.108 mv/decade
K =52.823 mv/decade
iCa=36.343 mv/decade
Cl =48.709 mv/decade
pH =53.103 mv/decade
Oct-31-13 12:18:29
_ _ _ _ _ _ _ _ _ _ _"""
        
        results = self.parser.parse_raw_data(raw_data)
        
        assert len(results) == 1
        result = results[0]
        assert result.test_type == 'CALIBRATION_SLOPE'
        assert result.parameters['Na'] == 52.108
        assert result.units['Na'] == 'mv/decade'
    
    def test_convert_to_hl7(self):
        """Test conversion to HL7 message"""
        # Create a test result
        result = BT1500Result(
            test_type='ANALYZE_SAMPLE',
            timestamp=datetime.now(),
            parameters={'Na': 159.951, 'K': 4.389, 'pH': 7.487},
            units={'Na': 'mmol/L', 'K': 'mmol/L', 'pH': 'mmol/L'},
            flags={'Na': 'HIGH', 'K': 'HIGH', 'pH': 'HIGH'},
            raw_data="test data"
        )
        
        hl7_message = self.parser.convert_to_hl7(result)
        
        # Check that HL7 message contains expected segments
        assert 'MSH|' in hl7_message
        assert 'OBR|' in hl7_message
        assert 'OBX|' in hl7_message
        
        # Check for specific parameters
        assert '2951-2^Sodium^LN' in hl7_message  # Na LOINC code
        assert '2823-3^Potassium^LN' in hl7_message  # K LOINC code
        assert '159.951' in hl7_message  # Na value
        assert 'HIGH' in hl7_message  # Flag
    
    def test_validate_data(self):
        """Test data validation"""
        valid_data = """CALIBRATION REPORT
Na = 37.658 mV
Oct-31-13 12:18:29
_ _ _ _ _ _ _ _ _ _ _"""
        
        invalid_data = "This is not BT-1500 data"
        
        assert self.parser.validate_data(valid_data) == True
        assert self.parser.validate_data(invalid_data) == False


class TestBT1500SerialHandler:
    """Test BT-1500 serial communication"""
    
    def setup_method(self):
        self.handler = BT1500SerialHandler("COM1", 9600)
    
    def test_handler_initialization(self):
        """Test handler initialization"""
        assert self.handler.port == "COM1"
        assert self.handler.baudrate == 9600
        assert self.handler.is_connected == False
        assert self.handler.parser is not None
    
    def test_is_complete_report(self):
        """Test complete report detection"""
        # Test with complete report
        self.handler.buffer = """CALIBRATION REPORT
Na = 37.658 mV
Oct-31-13 12:18:29
_ _ _ _ _ _ _ _ _ _ _"""
        
        assert self.handler._is_complete_report() == True
        
        # Test with incomplete report
        self.handler.buffer = "CALIBRATION REPORT\nNa = 37.658 mV"
        assert self.handler._is_complete_report() == False
    
    def test_get_status(self):
        """Test status reporting"""
        status = self.handler.get_status()
        
        assert 'connected' in status
        assert 'port' in status
        assert 'baudrate' in status
        assert 'last_communication' in status
        assert 'buffer_size' in status
        assert 'has_callback' in status


class TestBT1500Integration:
    """Integration tests for BT-1500"""
    
    @pytest.mark.asyncio
    async def test_device_manager_integration(self):
        """Test integration with device manager"""
        from src.devices.device_manager import device_manager
        
        # Test adding BT-1500 device (mock)
        # Note: This would require a mock serial connection for full testing
        pass
    
    def test_hl7_integration(self):
        """Test HL7 message integration"""
        from src.communication.hl7_handler import hl7_handler
        
        # Create a sample BT-1500 result
        parser = BT1500Parser()
        result = BT1500Result(
            test_type='ANALYZE_SAMPLE',
            timestamp=datetime.now(),
            parameters={'Na': 159.951, 'K': 4.389},
            units={'Na': 'mmol/L', 'K': 'mmol/L'},
            flags={'Na': 'HIGH', 'K': 'HIGH'},
            raw_data="test data"
        )
        
        # Convert to HL7
        hl7_message = parser.convert_to_hl7(result)
        
        # Parse with HL7 handler
        parsed = hl7_handler.parse_message(hl7_message)
        
        # Verify parsing was successful
        assert 'MSH' in parsed
        assert 'OBR' in parsed
        assert 'OBX' in parsed


def test_bt1500_sample_data():
    """Test with actual BT-1500 sample data from manual"""
    parser = BT1500Parser()
    
    # Sample data from the manual
    sample_data = """CALIBRATION REPORT
Na = 37.658 mV
K = 51.875 mV
iCa= 89.785 mV
Cl = 75.670 mV
pH = 39.877 mV
Na =56.412 mV
K = 69.519 mV
iCa= 78.291 mV
Cl = 58.429 mV
pH = 9.024 mV
CALIBRATION SLOPE
Na =52.108 mv/decade
K =52.823 mv/decade
iCa=36.343 mv/decade
Cl =48.709 mv/decade
pH =53.103 mv/decade
Oct-31-13 12:18:29
_ _ _ _ _ _ _ _ _ _ _

ANALYZE REPORT
Na = 59.437 mV
K = 72.141 mV
iCa= 76.476 mV
Cl = 59.034 mV
pH = 4.285 mV
Na = 57.219 mV
K = 70.830 mV
iCa= 78.090 mV
Cl = 57.622 mV
pH = 8.318 mV
ANALYZE SAMPLE
Na =159.951 mmol/L HIGH
K =4.389 mmol/L HIGH
iCa=1.164 mmol/L HIGH
Cl =109.206 mmol/L HIGH
pH =7.487 mmol/L HIGH
Oct-31-13 12:27:32
_ _ _ _ _ _ _ _ _"""
    
    # Test parsing
    results = parser.parse_raw_data(sample_data)
    
    # Should have multiple results
    assert len(results) >= 3  # CALIBRATION_REPORT, CALIBRATION_SLOPE, ANALYZE_SAMPLE
    
    # Test validation
    assert parser.validate_data(sample_data) == True
    
    # Test HL7 conversion for analyze sample
    for result in results:
        if result.test_type == 'ANALYZE_SAMPLE':
            hl7_message = parser.convert_to_hl7(result)
            assert 'MSH|' in hl7_message
            assert 'OBR|' in hl7_message
            assert 'OBX|' in hl7_message
            assert '159.951' in hl7_message  # Na value
            assert 'HIGH' in hl7_message  # Flag
            break


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 