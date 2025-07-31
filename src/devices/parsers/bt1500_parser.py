"""
BT-1500 Sensacore Analyzer Parser
Handles data from BT-1500 machine with H360/H560/ELITE 580 interface
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BT1500Result:
    """Represents a BT-1500 test result"""
    test_type: str  # CALIBRATION_REPORT, ANALYZE_REPORT, etc.
    timestamp: datetime
    parameters: Dict[str, float]  # Parameter name -> value
    units: Dict[str, str]  # Parameter name -> unit
    flags: Dict[str, str]  # Parameter name -> flag (HIGH, LOW, etc.)
    raw_data: str


class BT1500Parser:
    """Parser for BT-1500 Sensacore analyzer data"""
    
    def __init__(self):
        # BT-1500 specific parameters
        self.parameters = {
            'Na': 'Sodium',
            'K': 'Potassium', 
            'iCa': 'Ionized Calcium',
            'Cl': 'Chloride',
            'pH': 'pH'
        }
        
        # Units mapping
        self.units = {
            'Na': 'mmol/L',
            'K': 'mmol/L',
            'iCa': 'mmol/L', 
            'Cl': 'mmol/L',
            'pH': 'pH'
        }
        
        logger.info("BT1500Parser initialized")
    
    def parse_raw_data(self, raw_data: str) -> List[BT1500Result]:
        """Parse raw BT-1500 data into structured results"""
        try:
            results = []
            lines = raw_data.strip().split('\n')
            
            current_result = None
            current_type = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect result type
                if 'CALIBRATION REPORT' in line:
                    if current_result:
                        results.append(current_result)
                    current_type = 'CALIBRATION_REPORT'
                    current_result = BT1500Result(
                        test_type=current_type,
                        timestamp=datetime.now(),
                        parameters={},
                        units={},
                        flags={},
                        raw_data=''
                    )
                    current_result.raw_data += line + '\n'
                    
                elif 'ANALYZE REPORT' in line:
                    if current_result:
                        results.append(current_result)
                    current_type = 'ANALYZE_REPORT'
                    current_result = BT1500Result(
                        test_type=current_type,
                        timestamp=datetime.now(),
                        parameters={},
                        units={},
                        flags={},
                        raw_data=''
                    )
                    current_result.raw_data += line + '\n'
                    
                elif 'CALIBRATION SLOPE' in line:
                    if current_result:
                        results.append(current_result)
                    current_type = 'CALIBRATION_SLOPE'
                    current_result = BT1500Result(
                        test_type=current_type,
                        timestamp=datetime.now(),
                        parameters={},
                        units={},
                        flags={},
                        raw_data=''
                    )
                    current_result.raw_data += line + '\n'
                    
                elif 'ANALYZE SAMPLE' in line:
                    if current_result:
                        results.append(current_result)
                    current_type = 'ANALYZE_SAMPLE'
                    current_result = BT1500Result(
                        test_type=current_type,
                        timestamp=datetime.now(),
                        parameters={},
                        units={},
                        flags={},
                        raw_data=''
                    )
                    current_result.raw_data += line + '\n'
                    
                elif current_result:
                    current_result.raw_data += line + '\n'
                    
                    # Parse parameter lines
                    if '=' in line and 'mV' in line:
                        self._parse_parameter_line(line, current_result)
                    elif '=' in line and 'mmol/L' in line:
                        self._parse_result_line(line, current_result)
                    elif '=' in line and 'mv/decade' in line:
                        self._parse_slope_line(line, current_result)
                    elif re.match(r'\d{2}-\w{3}-\d{2} \d{2}:\d{2}:\d{2}', line):
                        # Parse timestamp
                        try:
                            current_result.timestamp = datetime.strptime(line, '%b-%d-%y %H:%M:%S')
                        except:
                            pass
            
            # Add final result
            if current_result:
                results.append(current_result)
            
            logger.info(f"Parsed {len(results)} BT-1500 results")
            return results
            
        except Exception as e:
            logger.error(f"Error parsing BT-1500 data: {str(e)}")
            raise
    
    def _parse_parameter_line(self, line: str, result: BT1500Result):
        """Parse parameter line with mV values"""
        try:
            # Format: "Na = 37.658 mV"
            match = re.match(r'(\w+)\s*=\s*([\d.]+)\s*mV', line)
            if match:
                param = match.group(1)
                value = float(match.group(2))
                result.parameters[param] = value
                result.units[param] = 'mV'
        except Exception as e:
            logger.warning(f"Failed to parse parameter line: {line}")
    
    def _parse_result_line(self, line: str, result: BT1500Result):
        """Parse result line with mmol/L values and flags"""
        try:
            # Format: "Na =159.951 mmol/L HIGH"
            match = re.match(r'(\w+)\s*=\s*([\d.]+)\s*mmol/L\s*(\w*)', line)
            if match:
                param = match.group(1)
                value = float(match.group(2))
                flag = match.group(3) if match.group(3) else ''
                
                result.parameters[param] = value
                result.units[param] = 'mmol/L'
                if flag:
                    result.flags[param] = flag
        except Exception as e:
            logger.warning(f"Failed to parse result line: {line}")
    
    def _parse_slope_line(self, line: str, result: BT1500Result):
        """Parse calibration slope line"""
        try:
            # Format: "Na =52.108 mv/decade"
            match = re.match(r'(\w+)\s*=\s*([\d.]+)\s*mv/decade', line)
            if match:
                param = match.group(1)
                value = float(match.group(2))
                result.parameters[param] = value
                result.units[param] = 'mv/decade'
        except Exception as e:
            logger.warning(f"Failed to parse slope line: {line}")
    
    def convert_to_hl7(self, result: BT1500Result, patient_id: str = None) -> str:
        """Convert BT-1500 result to HL7 ORU^R01 message"""
        try:
            # Build HL7 message
            hl7_message = []
            
            # MSH - Message Header
            msh = self._build_msh_segment()
            hl7_message.append(msh)
            
            # PID - Patient Identification
            if patient_id:
                pid = self._build_pid_segment(patient_id)
                hl7_message.append(pid)
            
            # OBR - Observation Request
            obr = self._build_obr_segment(result)
            hl7_message.append(obr)
            
            # OBX - Observation Results
            obx_segments = self._build_obx_segments(result)
            hl7_message.extend(obx_segments)
            
            return '\r'.join(hl7_message)
            
        except Exception as e:
            logger.error(f"Error converting BT-1500 result to HL7: {str(e)}")
            raise
    
    def _build_msh_segment(self) -> str:
        """Build MSH segment"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"MSH|^~\\&|BT-1500|Sensacore|||{timestamp}||ORU^R01|{timestamp}|P|2.3.1||||||UNICODE"
    
    def _build_pid_segment(self, patient_id: str) -> str:
        """Build PID segment"""
        return f"PID|1||{patient_id}^^^^MR"
    
    def _build_obr_segment(self, result: BT1500Result) -> str:
        """Build OBR segment"""
        timestamp = result.timestamp.strftime('%Y%m%d%H%M%S')
        test_name = "BT-1500 Electrolyte Panel" if result.test_type == 'ANALYZE_SAMPLE' else f"BT-1500 {result.test_type}"
        return f"OBR|1|||{test_name}||{timestamp}|||||||||||||||"
    
    def _build_obx_segments(self, result: BT1500Result) -> List[str]:
        """Build OBX segments for each parameter"""
        segments = []
        set_id = 1
        
        for param, value in result.parameters.items():
            if param in self.parameters:
                # Get LOINC code for parameter
                loinc_code = self._get_loinc_code(param)
                unit = result.units.get(param, self.units.get(param, ''))
                flag = result.flags.get(param, '')
                
                # Build OBX segment
                obx = f"OBX|{set_id}|NM|{loinc_code}^{self.parameters[param]}^LN||{value}|{unit}|||||F"
                if flag:
                    obx = obx.replace('|||||F', f"||{flag}|||F")
                
                segments.append(obx)
                set_id += 1
        
        return segments
    
    def _get_loinc_code(self, parameter: str) -> str:
        """Get LOINC code for parameter"""
        loinc_codes = {
            'Na': '2951-2',  # Sodium
            'K': '2823-3',   # Potassium
            'iCa': '2028-9', # Ionized Calcium
            'Cl': '2075-0',  # Chloride
            'pH': '2746-1'   # pH
        }
        return loinc_codes.get(parameter, 'unknown')
    
    def validate_data(self, raw_data: str) -> bool:
        """Validate BT-1500 data format"""
        try:
            # Check for required markers
            required_markers = ['CALIBRATION REPORT', 'ANALYZE REPORT', 'CALIBRATION SLOPE', 'ANALYZE SAMPLE']
            has_marker = any(marker in raw_data for marker in required_markers)
            
            # Check for parameter patterns
            has_parameters = re.search(r'\w+\s*=\s*[\d.]+\s*(mV|mmol/L)', raw_data)
            
            return has_marker and has_parameters
            
        except Exception as e:
            logger.error(f"Error validating BT-1500 data: {str(e)}")
            return False 