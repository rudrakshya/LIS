"""
HL7 Message Handler for the Laboratory Information System
Handles parsing, processing, and generation of HL7 messages for medical equipment communication
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import json

try:
    from hl7apy.core import Message, Segment, Field
    from hl7apy.parser import parse_message
    from hl7apy import parse_segment
    import hl7
except ImportError:
    # Fallback if hl7apy is not available
    import hl7

from ..core.config import settings
from ..core.exceptions import HL7Exception, ValidationException
from ..models import Patient, TestOrder, TestResult, Sample

logger = logging.getLogger(__name__)


class HL7MessageType:
    """HL7 Message type constants"""
    
    # Order Management
    ORM_O01 = "ORM^O01"  # Order message
    ORR_O02 = "ORR^O02"  # Order response
    
    # Result Reporting
    ORU_R01 = "ORU^R01"  # Unsolicited transmission of observation
    ORU_R30 = "ORU^R30"  # Unsolicited point-of-care observation
    
    # Patient Management
    ADT_A01 = "ADT^A01"  # Admit patient
    ADT_A03 = "ADT^A03"  # Discharge patient
    ADT_A08 = "ADT^A08"  # Update patient information
    
    # Query
    QRY_A19 = "QRY^A19"  # Patient query
    QRY_R02 = "QRY^R02"  # Query for results
    
    # Acknowledgment
    ACK = "ACK"          # General acknowledgment


class HL7Handler:
    """Main HL7 message handler"""
    
    def __init__(self):
        # HL7 configuration from settings
        self.encoding = 'utf-8'
        self.separators = {
            'field_separator': settings.comm_hl7_field_separator,
            'component_separator': settings.comm_hl7_component_separator,
            'repetition_separator': settings.comm_hl7_repetition_separator,
            'escape_character': settings.comm_hl7_escape_character,
            'subcomponent_separator': settings.comm_hl7_subcomponent_separator
        }
        
        # Message handlers mapping
        self.message_handlers = {
            'ORM': self.handle_order_message,
            'ORU': self.handle_result_message,
            'ADT': self.handle_patient_message,
            'QRY': self.handle_query_message,
            'ACK': self.handle_acknowledgment
        }
        
        logger.info("HL7Handler initialized")
    
    def parse_message(self, raw_message: str) -> Dict[str, Any]:
        """Parse raw HL7 message into structured data"""
        try:
            # Clean up the message
            raw_message = raw_message.strip()
            if not raw_message:
                raise HL7Exception("Empty HL7 message")
            
            # Parse using hl7apy if available, otherwise use python-hl7
            try:
                parsed = parse_message(raw_message)
                return self._extract_hl7apy_data(parsed)
            except:
                # Fallback to python-hl7
                parsed = hl7.parse(raw_message)
                return self._extract_hl7_data(parsed)
                
        except Exception as e:
            logger.error(f"Failed to parse HL7 message: {str(e)}")
            raise HL7Exception(f"Failed to parse HL7 message: {str(e)}")
    
    def _extract_hl7apy_data(self, message: Message) -> Dict[str, Any]:
        """Extract data from hl7apy Message object"""
        try:
            msh = message.MSH
            
            return {
                'message_type': msh.MSH_9.MSH_9_1.value,
                'trigger_event': msh.MSH_9.MSH_9_2.value,
                'message_control_id': msh.MSH_10.value,
                'sending_application': msh.MSH_3.value,
                'sending_facility': msh.MSH_4.value,
                'receiving_application': msh.MSH_5.value,
                'receiving_facility': msh.MSH_6.value,
                'timestamp': msh.MSH_7.value,
                'processing_id': msh.MSH_11.value,
                'version_id': msh.MSH_12.value,
                'raw_message': str(message),
                'segments': self._extract_segments_hl7apy(message)
            }
        except Exception as e:
            raise HL7Exception(f"Failed to extract HL7apy data: {str(e)}")
    
    def _extract_hl7_data(self, message) -> Dict[str, Any]:
        """Extract data from python-hl7 message object"""
        try:
            msh = message.segment('MSH')
            
            return {
                'message_type': str(msh[9][0][0]) if msh[9] else None,
                'trigger_event': str(msh[9][0][1]) if msh[9] and len(msh[9][0]) > 1 else None,
                'message_control_id': str(msh[10]) if msh[10] else None,
                'sending_application': str(msh[3]) if msh[3] else None,
                'sending_facility': str(msh[4]) if msh[4] else None,
                'receiving_application': str(msh[5]) if msh[5] else None,
                'receiving_facility': str(msh[6]) if msh[6] else None,
                'timestamp': str(msh[7]) if msh[7] else None,
                'processing_id': str(msh[11]) if msh[11] else None,
                'version_id': str(msh[12]) if msh[12] else None,
                'raw_message': str(message),
                'segments': self._extract_segments_hl7(message)
            }
        except Exception as e:
            raise HL7Exception(f"Failed to extract HL7 data: {str(e)}")
    
    def _extract_segments_hl7apy(self, message: Message) -> Dict[str, Any]:
        """Extract segments from hl7apy message"""
        segments = {}
        for segment in message.children:
            segment_name = segment.name
            if segment_name not in segments:
                segments[segment_name] = []
            segments[segment_name].append(self._segment_to_dict_hl7apy(segment))
        return segments
    
    def _extract_segments_hl7(self, message) -> Dict[str, Any]:
        """Extract segments from python-hl7 message"""
        segments = {}
        for segment in message:
            segment_name = str(segment[0])
            if segment_name not in segments:
                segments[segment_name] = []
            segments[segment_name].append(self._segment_to_dict_hl7(segment))
        return segments
    
    def _segment_to_dict_hl7apy(self, segment) -> Dict[str, Any]:
        """Convert hl7apy segment to dictionary"""
        result = {'segment_type': segment.name}
        for i, field in enumerate(segment.children, 1):
            result[f'field_{i}'] = str(field.value) if field.value else None
        return result
    
    def _segment_to_dict_hl7(self, segment) -> Dict[str, Any]:
        """Convert python-hl7 segment to dictionary"""
        result = {'segment_type': str(segment[0])}
        for i, field in enumerate(segment[1:], 1):
            result[f'field_{i}'] = str(field) if field else None
        return result
    
    def process_message(self, raw_message: str) -> Dict[str, Any]:
        """Process incoming HL7 message"""
        try:
            logger.info(f"Processing HL7 message: {raw_message[:100]}...")
            
            # Parse the message
            parsed_data = self.parse_message(raw_message)
            
            # Determine message type and route to appropriate handler
            message_type = parsed_data.get('message_type', '').upper()
            
            # Get the handler for this message type
            handler = self.message_handlers.get(message_type)
            if not handler:
                logger.warning(f"No handler found for message type: {message_type}")
                return self.create_nak_response(parsed_data, f"Unsupported message type: {message_type}")
            
            # Process the message
            response = handler(parsed_data)
            
            logger.info(f"Successfully processed {message_type} message")
            return response
            
        except Exception as e:
            logger.error(f"Error processing HL7 message: {str(e)}")
            return self.create_nak_response({}, str(e))
    
    def handle_order_message(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Order Management (ORM) messages"""
        try:
            logger.info("Processing order message (ORM)")
            
            segments = parsed_data.get('segments', {})
            
            # Extract patient information (PID segment)
            pid_segments = segments.get('PID', [])
            if not pid_segments:
                raise HL7Exception("Missing PID segment in order message")
            
            patient_data = self._extract_patient_from_pid(pid_segments[0])
            
            # Extract order information (ORC/OBR segments)
            orc_segments = segments.get('ORC', [])
            obr_segments = segments.get('OBR', [])
            
            if not orc_segments and not obr_segments:
                raise HL7Exception("Missing ORC/OBR segments in order message")
            
            # Process each order
            orders_processed = []
            for i, obr in enumerate(obr_segments):
                order_data = self._extract_order_from_obr(obr)
                if i < len(orc_segments):
                    order_control = self._extract_order_control_from_orc(orc_segments[i])
                    order_data.update(order_control)
                
                # TODO: Save to database
                orders_processed.append(order_data)
            
            return self.create_ack_response(parsed_data, f"Processed {len(orders_processed)} orders")
            
        except Exception as e:
            logger.error(f"Error handling order message: {str(e)}")
            raise HL7Exception(f"Order processing failed: {str(e)}")
    
    def handle_result_message(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Observation Result (ORU) messages"""
        try:
            logger.info("Processing result message (ORU)")
            
            segments = parsed_data.get('segments', {})
            
            # Extract patient information
            pid_segments = segments.get('PID', [])
            if not pid_segments:
                raise HL7Exception("Missing PID segment in result message")
            
            patient_data = self._extract_patient_from_pid(pid_segments[0])
            
            # Extract observation results (OBR/OBX segments)
            obr_segments = segments.get('OBR', [])
            obx_segments = segments.get('OBX', [])
            
            if not obx_segments:
                raise HL7Exception("Missing OBX segments in result message")
            
            # Process results
            results_processed = []
            for obx in obx_segments:
                result_data = self._extract_result_from_obx(obx)
                # TODO: Save result to database
                results_processed.append(result_data)
            
            return self.create_ack_response(parsed_data, f"Processed {len(results_processed)} results")
            
        except Exception as e:
            logger.error(f"Error handling result message: {str(e)}")
            raise HL7Exception(f"Result processing failed: {str(e)}")
    
    def handle_patient_message(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Patient Administration (ADT) messages"""
        try:
            logger.info("Processing patient message (ADT)")
            
            segments = parsed_data.get('segments', {})
            
            # Extract patient information
            pid_segments = segments.get('PID', [])
            if not pid_segments:
                raise HL7Exception("Missing PID segment in patient message")
            
            patient_data = self._extract_patient_from_pid(pid_segments[0])
            
            # TODO: Save/update patient in database
            
            return self.create_ack_response(parsed_data, "Patient information processed")
            
        except Exception as e:
            logger.error(f"Error handling patient message: {str(e)}")
            raise HL7Exception(f"Patient processing failed: {str(e)}")
    
    def handle_query_message(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Query (QRY) messages"""
        try:
            logger.info("Processing query message (QRY)")
            
            # TODO: Implement query processing
            
            return self.create_ack_response(parsed_data, "Query processed")
            
        except Exception as e:
            logger.error(f"Error handling query message: {str(e)}")
            raise HL7Exception(f"Query processing failed: {str(e)}")
    
    def handle_acknowledgment(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Acknowledgment (ACK) messages"""
        try:
            logger.info("Processing acknowledgment message (ACK)")
            
            # Log the acknowledgment
            ack_code = parsed_data.get('segments', {}).get('MSA', [{}])[0].get('field_1')
            logger.info(f"Received ACK with code: {ack_code}")
            
            return {"status": "acknowledged", "ack_code": ack_code}
            
        except Exception as e:
            logger.error(f"Error handling acknowledgment: {str(e)}")
            raise HL7Exception(f"ACK processing failed: {str(e)}")
    
    def _extract_patient_from_pid(self, pid_segment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patient data from PID segment"""
        return {
            'patient_id': pid_segment.get('field_3'),  # Patient identifier
            'name': pid_segment.get('field_5'),        # Patient name
            'date_of_birth': pid_segment.get('field_7'), # Date of birth
            'gender': pid_segment.get('field_8'),      # Gender
            'address': pid_segment.get('field_11'),    # Address
            'phone': pid_segment.get('field_13'),      # Phone
        }
    
    def _extract_order_from_obr(self, obr_segment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order data from OBR segment"""
        return {
            'order_number': obr_segment.get('field_3'),        # Filler order number
            'test_code': obr_segment.get('field_4'),          # Universal service ID
            'ordered_datetime': obr_segment.get('field_6'),   # Requested date/time
            'collected_datetime': obr_segment.get('field_7'),  # Observation date/time
            'ordering_physician': obr_segment.get('field_16'), # Ordering provider
        }
    
    def _extract_order_control_from_orc(self, orc_segment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order control data from ORC segment"""
        return {
            'order_control': orc_segment.get('field_1'),      # Order control
            'placer_order_number': orc_segment.get('field_2'), # Placer order number
            'order_status': orc_segment.get('field_5'),       # Order status
        }
    
    def _extract_result_from_obx(self, obx_segment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract result data from OBX segment"""
        return {
            'set_id': obx_segment.get('field_1'),          # Set ID
            'value_type': obx_segment.get('field_2'),      # Value type
            'identifier': obx_segment.get('field_3'),      # Observation identifier
            'sub_id': obx_segment.get('field_4'),          # Observation sub-ID
            'value': obx_segment.get('field_5'),           # Observation value
            'units': obx_segment.get('field_6'),           # Units
            'reference_range': obx_segment.get('field_7'), # Reference range
            'abnormal_flags': obx_segment.get('field_8'),  # Abnormal flags
            'result_status': obx_segment.get('field_11'),  # Observation result status
            'datetime': obx_segment.get('field_14'),       # Date/time of observation
        }
    
    def create_ack_response(self, original_message: Dict[str, Any], text: str = None) -> Dict[str, Any]:
        """Create ACK (acknowledgment) response message"""
        try:
            control_id = original_message.get('message_control_id', 'UNKNOWN')
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Build ACK message
            ack_message = self._build_ack_message(
                control_id=control_id,
                ack_code="AA",  # Application Accept
                text=text or "Message processed successfully"
            )
            
            return {
                'status': 'success',
                'message_type': 'ACK',
                'response_message': ack_message,
                'original_control_id': control_id
            }
            
        except Exception as e:
            logger.error(f"Error creating ACK response: {str(e)}")
            raise HL7Exception(f"Failed to create ACK response: {str(e)}")
    
    def create_nak_response(self, original_message: Dict[str, Any], error_text: str) -> Dict[str, Any]:
        """Create NAK (negative acknowledgment) response message"""
        try:
            control_id = original_message.get('message_control_id', 'UNKNOWN')
            
            # Build NAK message
            nak_message = self._build_ack_message(
                control_id=control_id,
                ack_code="AE",  # Application Error
                text=error_text
            )
            
            return {
                'status': 'error',
                'message_type': 'ACK',
                'response_message': nak_message,
                'original_control_id': control_id,
                'error': error_text
            }
            
        except Exception as e:
            logger.error(f"Error creating NAK response: {str(e)}")
            return {
                'status': 'error',
                'error': f"Failed to create NAK response: {str(e)}"
            }
    
    def _build_ack_message(self, control_id: str, ack_code: str, text: str) -> str:
        """Build HL7 ACK message"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # MSH segment
        msh = f"MSH|^~\\&|LIS|LAB|SENDER|FACILITY|{timestamp}||ACK^R01|{control_id}_ACK|P|2.5"
        
        # MSA segment  
        msa = f"MSA|{ack_code}|{control_id}|{text}"
        
        # Combine segments
        ack_message = f"{msh}\r{msa}\r"
        
        return ack_message
    
    def generate_result_message(self, patient_data: Dict[str, Any], 
                              results: List[Dict[str, Any]]) -> str:
        """Generate HL7 ORU^R01 result message"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            control_id = f"LIS_{timestamp}"
            
            # MSH segment
            msh = f"MSH|^~\\&|LIS|LAB|EMR|HOSPITAL|{timestamp}||ORU^R01|{control_id}|P|2.5"
            
            # PID segment
            pid = self._build_pid_segment(patient_data)
            
            # OBR segment (order information)
            obr = self._build_obr_segment(results[0] if results else {})
            
            # OBX segments (results)
            obx_segments = []
            for i, result in enumerate(results, 1):
                obx = self._build_obx_segment(result, i)
                obx_segments.append(obx)
            
            # Combine all segments
            message_parts = [msh, pid, obr] + obx_segments
            message = '\r'.join(message_parts) + '\r'
            
            logger.info(f"Generated ORU^R01 message with {len(results)} results")
            return message
            
        except Exception as e:
            logger.error(f"Error generating result message: {str(e)}")
            raise HL7Exception(f"Failed to generate result message: {str(e)}")
    
    def _build_pid_segment(self, patient_data: Dict[str, Any]) -> str:
        """Build PID segment from patient data"""
        return f"PID|1||{patient_data.get('patient_id', '')}||{patient_data.get('name', '')}||{patient_data.get('date_of_birth', '')}|{patient_data.get('gender', '')}"
    
    def _build_obr_segment(self, result_data: Dict[str, Any]) -> str:
        """Build OBR segment from result data"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"OBR|1|{result_data.get('order_number', '')}||{result_data.get('test_code', '')}|||{timestamp}"
    
    def _build_obx_segment(self, result_data: Dict[str, Any], set_id: int) -> str:
        """Build OBX segment from result data"""
        return f"OBX|{set_id}|NM|{result_data.get('test_code', '')}^{result_data.get('test_name', '')}||{result_data.get('value', '')}|{result_data.get('units', '')}|{result_data.get('reference_range', '')}|{result_data.get('abnormal_flag', '')}|||F"


# Global HL7 handler instance
hl7_handler = HL7Handler() 