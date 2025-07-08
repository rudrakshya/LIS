"""
ASTM Message Handler for Laboratory Information System (LIS)
Handles ASTM E1381/E1394 standard messages for laboratory equipment communication
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ASTMRecord:
    """Represents a single ASTM record"""
    record_type: str
    sequence_number: str
    fields: List[str]
    parsed_data: Dict[str, Any]
    raw_data: str


@dataclass
class ASTMMessage:
    """Represents a complete ASTM message"""
    frame_number: Optional[int]
    records: List[ASTMRecord]
    checksum: Optional[str]
    checksum_valid: bool
    raw_message: str
    timestamp: datetime


class ASTMHandler:
    """ASTM Message Handler for laboratory equipment communication"""
    
    # ASTM control characters
    STX = '\x02'  # Start of Text
    ETX = '\x03'  # End of Text
    ACK = '\x06'  # Acknowledgment
    NAK = '\x15'  # Negative Acknowledgment
    EOT = '\x04'  # End of Transmission
    ENQ = '\x05'  # Enquiry
    CR = '\r'     # Carriage Return
    LF = '\n'     # Line Feed
    
    def __init__(self):
        """Initialize ASTM handler"""
        self.message_counter = 0
        logger.info("ASTM Handler initialized")
    
    def parse_message(self, raw_message: str) -> ASTMMessage:
        """Parse raw ASTM message into structured format"""
        try:
            self.message_counter += 1
            
            # Clean the message
            message = self._clean_message(raw_message)
            
            # Extract frame number
            frame_number = self._extract_frame_number(message)
            
            # Extract and validate checksum
            checksum, checksum_valid = self._validate_checksum(message)
            
            # Parse records
            records = self._parse_records(message)
            
            astm_message = ASTMMessage(
                frame_number=frame_number,
                records=records,
                checksum=checksum,
                checksum_valid=checksum_valid,
                raw_message=raw_message,
                timestamp=datetime.now()
            )
            
            logger.info(f"Parsed ASTM message with {len(records)} records")
            return astm_message
            
        except Exception as e:
            logger.error(f"Error parsing ASTM message: {str(e)}")
            raise
    
    def _clean_message(self, message: str) -> str:
        """Remove control characters and clean message"""
        # Remove STX, ETX characters
        cleaned = message.replace(self.STX, '').replace(self.ETX, '')
        
        # Handle different line endings
        cleaned = cleaned.replace('\r\n', '\r').replace('\n', '\r')
        
        return cleaned
    
    def _extract_frame_number(self, message: str) -> Optional[int]:
        """Extract frame number from message"""
        try:
            lines = message.split(self.CR)
            if lines and lines[0] and lines[0][0].isdigit():
                return int(lines[0][0])
        except (ValueError, IndexError):
            pass
        return None
    
    def _validate_checksum(self, message: str) -> tuple[Optional[str], bool]:
        """Validate message checksum"""
        try:
            lines = message.split(self.CR)
            
            # Look for checksum (usually last 2 hex characters)
            for line in reversed(lines):
                if len(line) == 2 and all(c in '0123456789ABCDEF' for c in line.upper()):
                    expected_checksum = line.upper()
                    
                    # Calculate actual checksum
                    content = message[:message.rfind(line)]
                    calculated_checksum = self._calculate_checksum(content)
                    
                    return expected_checksum, expected_checksum == calculated_checksum
            
            return None, False
            
        except Exception as e:
            logger.error(f"Error validating checksum: {str(e)}")
            return None, False
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate ASTM checksum"""
        try:
            checksum = 0
            for char in content:
                checksum += ord(char)
            
            # Return last 2 hex digits
            return f"{checksum & 0xFF:02X}"
            
        except Exception as e:
            logger.error(f"Error calculating checksum: {str(e)}")
            return "00"
    
    def _parse_records(self, message: str) -> List[ASTMRecord]:
        """Parse individual records from message"""
        records = []
        
        try:
            lines = message.split(self.CR)
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip frame number if present
                if line[0].isdigit():
                    line = line[1:]
                
                # Skip checksum lines
                if len(line) == 2 and all(c in '0123456789ABCDEF' for c in line.upper()):
                    continue
                
                # Parse record if it contains field separators
                if '|' in line:
                    record = self._parse_single_record(line)
                    if record:
                        records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error parsing records: {str(e)}")
            return []
    
    def _parse_single_record(self, record_line: str) -> Optional[ASTMRecord]:
        """Parse a single ASTM record"""
        try:
            fields = record_line.split('|')
            record_type = fields[0] if fields else ''
            sequence_number = fields[1] if len(fields) > 1 else ''
            
            # Parse based on record type
            parsed_data = {}
            
            if record_type == 'H':
                parsed_data = self._parse_header_record(fields)
            elif record_type == 'P':
                parsed_data = self._parse_patient_record(fields)
            elif record_type == 'O':
                parsed_data = self._parse_order_record(fields)
            elif record_type == 'R':
                parsed_data = self._parse_result_record(fields)
            elif record_type == 'C':
                parsed_data = self._parse_comment_record(fields)
            elif record_type == 'L':
                parsed_data = self._parse_terminator_record(fields)
            elif record_type == 'M':
                parsed_data = self._parse_manufacturer_record(fields)
            else:
                logger.warning(f"Unknown ASTM record type: {record_type}")
                parsed_data = {'unknown_fields': fields}
            
            return ASTMRecord(
                record_type=record_type,
                sequence_number=sequence_number,
                fields=fields,
                parsed_data=parsed_data,
                raw_data=record_line
            )
            
        except Exception as e:
            logger.error(f"Error parsing single record: {str(e)}")
            return None
    
    def _parse_header_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Header record (H|)"""
        return {
            'delimiter_definition': fields[1] if len(fields) > 1 else '',
            'message_control_id': fields[2] if len(fields) > 2 else '',
            'access_password': fields[3] if len(fields) > 3 else '',
            'sender_name': fields[4] if len(fields) > 4 else '',
            'sender_address': fields[5] if len(fields) > 5 else '',
            'reserved_field': fields[6] if len(fields) > 6 else '',
            'sender_phone': fields[7] if len(fields) > 7 else '',
            'characteristics': fields[8] if len(fields) > 8 else '',
            'receiver_id': fields[9] if len(fields) > 9 else '',
            'comments': fields[10] if len(fields) > 10 else '',
            'processing_id': fields[11] if len(fields) > 11 else '',
            'version': fields[12] if len(fields) > 12 else '',
            'timestamp': fields[13] if len(fields) > 13 else ''
        }
    
    def _parse_patient_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Patient record (P|)"""
        return {
            'practice_patient_id': fields[2] if len(fields) > 2 else '',
            'laboratory_patient_id': fields[3] if len(fields) > 3 else '',
            'patient_id_3': fields[4] if len(fields) > 4 else '',
            'patient_name': fields[5] if len(fields) > 5 else '',
            'mother_maiden_name': fields[6] if len(fields) > 6 else '',
            'birthdate': fields[7] if len(fields) > 7 else '',
            'patient_sex': fields[8] if len(fields) > 8 else '',
            'patient_race': fields[9] if len(fields) > 9 else '',
            'patient_address': fields[10] if len(fields) > 10 else '',
            'reserved_field': fields[11] if len(fields) > 11 else '',
            'patient_phone': fields[12] if len(fields) > 12 else '',
            'attending_physician_id': fields[13] if len(fields) > 13 else '',
            'diagnosis': fields[18] if len(fields) > 18 else '',
            'medications': fields[19] if len(fields) > 19 else '',
            'diet': fields[20] if len(fields) > 20 else '',
            'admission_date': fields[23] if len(fields) > 23 else '',
            'location': fields[25] if len(fields) > 25 else ''
        }
    
    def _parse_order_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Order record (O|)"""
        return {
            'specimen_id': fields[2] if len(fields) > 2 else '',
            'instrument_specimen_id': fields[3] if len(fields) > 3 else '',
            'test_information': self._parse_test_information(fields[4] if len(fields) > 4 else ''),
            'priority': fields[5] if len(fields) > 5 else '',
            'requested_date_time': fields[6] if len(fields) > 6 else '',
            'collection_date_time': fields[7] if len(fields) > 7 else '',
            'collector_id': fields[8] if len(fields) > 8 else '',
            'action_code': fields[9] if len(fields) > 9 else '',
            'danger_code': fields[10] if len(fields) > 10 else '',
            'clinical_info': fields[11] if len(fields) > 11 else '',
            'received_date_time': fields[12] if len(fields) > 12 else '',
            'specimen_descriptor': fields[13] if len(fields) > 13 else '',
            'ordering_physician': fields[14] if len(fields) > 14 else '',
            'physician_phone': fields[15] if len(fields) > 15 else '',
            'reported_date_time': fields[20] if len(fields) > 20 else ''
        }
    
    def _parse_result_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Result record (R|)"""
        return {
            'test_information': self._parse_test_information(fields[2] if len(fields) > 2 else ''),
            'measurement_value': fields[3] if len(fields) > 3 else '',
            'units': fields[4] if len(fields) > 4 else '',
            'reference_ranges': fields[5] if len(fields) > 5 else '',
            'abnormal_flags': fields[6] if len(fields) > 6 else '',
            'nature_abnormal_testing': fields[7] if len(fields) > 7 else '',
            'result_status': fields[8] if len(fields) > 8 else '',
            'operator_id': fields[10] if len(fields) > 10 else '',
            'test_started_date_time': fields[11] if len(fields) > 11 else '',
            'test_completed_date_time': fields[12] if len(fields) > 12 else '',
            'instrument_id': fields[13] if len(fields) > 13 else ''
        }
    
    def _parse_comment_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Comment record (C|)"""
        return {
            'comment_source': fields[2] if len(fields) > 2 else '',
            'comment_text': fields[3] if len(fields) > 3 else '',
            'comment_type': fields[4] if len(fields) > 4 else ''
        }
    
    def _parse_terminator_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Terminator record (L|)"""
        return {
            'termination_code': fields[2] if len(fields) > 2 else ''
        }
    
    def _parse_manufacturer_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Manufacturer record (M|)"""
        return {
            'manufacturer_info': fields[2] if len(fields) > 2 else '',
            'model': fields[3] if len(fields) > 3 else '',
            'version': fields[4] if len(fields) > 4 else ''
        }
    
    def _parse_test_information(self, test_info: str) -> Dict[str, Any]:
        """Parse test information field which may contain multiple components"""
        try:
            if '^' in test_info:
                components = test_info.split('^')
                return {
                    'test_id': components[0] if len(components) > 0 else '',
                    'test_name': components[1] if len(components) > 1 else '',
                    'test_type': components[2] if len(components) > 2 else '',
                    'test_parameters': components[3:] if len(components) > 3 else []
                }
            else:
                return {
                    'test_id': test_info,
                    'test_name': '',
                    'test_type': '',
                    'test_parameters': []
                }
        except Exception as e:
            logger.error(f"Error parsing test information: {str(e)}")
            return {'test_id': test_info, 'test_name': '', 'test_type': '', 'test_parameters': []}
    
    def create_acknowledgment(self, success: bool = True) -> str:
        """Create ASTM acknowledgment message"""
        if success:
            return self.ACK
        else:
            return self.NAK
    
    def create_response_message(self, message_type: str, data: Dict[str, Any]) -> str:
        """Create ASTM response message"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            if message_type == 'ACK':
                return self.create_acknowledgment(True)
            elif message_type == 'NAK':
                return self.create_acknowledgment(False)
            elif message_type == 'RESULT_ACK':
                # Create result acknowledgment
                header = f"H|\\^&|||LIS|||||||||{timestamp}"
                terminator = "L|1|N"
                message = f"{header}\r{terminator}\r"
                checksum = self._calculate_checksum(message)
                return f"\x02{message}\x03{checksum}\r\n"
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return self.NAK
                
        except Exception as e:
            logger.error(f"Error creating response message: {str(e)}")
            return self.NAK
    
    def process_message(self, raw_message: str) -> Dict[str, Any]:
        """Process complete ASTM message and return structured response"""
        try:
            logger.info("Processing ASTM message")
            
            # Parse the message
            astm_message = self.parse_message(raw_message)
            
            # Process each record
            processed_records = []
            
            for record in astm_message.records:
                processed_record = {
                    'type': record.record_type,
                    'sequence': record.sequence_number,
                    'data': record.parsed_data,
                    'raw': record.raw_data
                }
                processed_records.append(processed_record)
                
                # Log important information
                if record.record_type == 'P':
                    patient_name = record.parsed_data.get('patient_name', 'Unknown')
                    patient_id = record.parsed_data.get('practice_patient_id', record.parsed_data.get('laboratory_patient_id', 'Unknown'))
                    logger.info(f"Patient: {patient_name} (ID: {patient_id})")
                elif record.record_type == 'R':
                    test_info = record.parsed_data.get('test_information', {})
                    test_id = test_info.get('test_id', 'Unknown')
                    value = record.parsed_data.get('measurement_value', 'Unknown')
                    logger.info(f"Result: {test_id} = {value}")
            
            response = {
                'status': 'success',
                'message_type': 'ASTM',
                'timestamp': astm_message.timestamp.isoformat(),
                'records_processed': len(processed_records),
                'records': processed_records,
                'checksum_valid': astm_message.checksum_valid,
                'acknowledgment': self.create_acknowledgment(True)
            }
            
            logger.info(f"Successfully processed ASTM message with {len(processed_records)} records")
            return response
            
        except Exception as e:
            logger.error(f"Error processing ASTM message: {str(e)}")
            return {
                'status': 'error',
                'message_type': 'ASTM',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'acknowledgment': self.create_acknowledgment(False)
            }


# Global ASTM handler instance
astm_handler = ASTMHandler() 