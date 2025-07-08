"""
TCP Server for Laboratory Information System
Handles incoming connections and data from medical equipment
"""

import asyncio
import logging
import socket
from datetime import datetime
from typing import Dict, List, Optional, Callable, Set, Any
import json

from src.core.config import settings
from src.core.exceptions import LISException
from src.communication.astm_handler import astm_handler
from src.communication.hl7_handler import hl7_handler
from src.devices.device_manager import device_manager

logger = logging.getLogger(__name__)


class TCPClientHandler:
    """Handles individual TCP client connections"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server: 'TCPServer'):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.client_address = writer.get_extra_info('peername')
        self.device_id: Optional[str] = None
        self.connected_at = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0
        self.is_authenticated = False
        self.buffer = b""
        
        logger.info(f"New TCP client connected from {self.client_address}")
    
    async def handle_connection(self):
        """Handle the client connection"""
        try:
            # Send welcome message
            await self._send_message("LIS_READY\r\n")
            
            # Handle incoming messages
            while True:
                try:
                    # Read data with timeout and buffer limit
                    data = await asyncio.wait_for(
                        self.reader.read(settings.comm_tcp_buffer_size),
                        timeout=settings.comm_serial_timeout
                    )
                    
                    if not data:
                        logger.info(f"Client {self.client_address} disconnected")
                        break
                    
                    # Process the received data
                    await self._process_received_data(data)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for data from {self.client_address}")
                    await self._send_message("TIMEOUT\r\n")
                    break
                except Exception as e:
                    logger.error(f"Error handling client {self.client_address}: {str(e)}")
                    self.error_count += 1
                    # Check for maximum error threshold
                    if self.error_count > 5:  # max_client_errors setting
                        await self.disconnect_client("Too many errors")
                        return
                    
        except Exception as e:
            logger.error(f"Fatal error handling client {self.client_address}: {str(e)}")
        finally:
            await self._cleanup()
    
    async def _process_received_data(self, data: bytes):
        """Process received data from client"""
        try:
            # Add to buffer
            self.buffer += data
            
            # Process complete messages in buffer
            while b'\r\n' in self.buffer:
                # Extract one complete message
                message_bytes, self.buffer = self.buffer.split(b'\r\n', 1)
                
                if message_bytes:
                    message = message_bytes.decode('utf-8', errors='ignore').strip()
                    await self._handle_message(message)
                    
        except Exception as e:
            logger.error(f"Error processing data from {self.client_address}: {str(e)}")
            self.error_count += 1
    
    async def _handle_message(self, message: str):
        """Handle a complete message from client"""
        try:
            self.message_count += 1
            logger.debug(f"Received message from {self.client_address}: {message[:100]}...")
            
            # Check if this is an authentication message
            if message.startswith("AUTH:"):
                await self._handle_authentication(message)
                return
            
            # Check if this is a device identification message
            if message.startswith("DEVICE_ID:"):
                await self._handle_device_identification(message)
                return
            
            # For non-authenticated clients, reject other messages
            if not self.is_authenticated:
                await self._send_message("AUTH_REQUIRED\r\n")
                return
            
            # Determine message type and process
            message_type = self._detect_message_type(message)
            
            if message_type == "HL7":
                await self._handle_hl7_message(message)
            elif message_type == "ASTM":
                await self._handle_astm_message(message)
            elif message_type == "JSON":
                await self._handle_json_message(message)
            elif message_type == "COMMAND":
                await self._handle_command_message(message)
            else:
                await self._handle_raw_message(message)
            
        except Exception as e:
            logger.error(f"Error handling message from {self.client_address}: {str(e)}")
            self.error_count += 1
            await self._send_message(f"ERROR: {str(e)}\r\n")
    
    async def _handle_authentication(self, message: str):
        """Handle authentication message"""
        try:
            # Extract authentication token
            auth_token = message.split(":", 1)[1].strip()
            
            # Simple token-based authentication
            if auth_token == "tcp_auth_token_placeholder":  # settings value placeholder
                self.is_authenticated = True
                await self._send_message("AUTH_OK\r\n")
                logger.info(f"Client {self.client_address} authenticated successfully")
            else:
                await self._send_message("AUTH_FAILED\r\n")
                logger.warning(f"Authentication failed for client {self.client_address}")
                
        except Exception as e:
            logger.error(f"Authentication error for {self.client_address}: {str(e)}")
            await self._send_message("AUTH_ERROR\r\n")
    
    async def _handle_device_identification(self, message: str):
        """Handle device identification message"""
        try:
            # Extract device ID
            device_id = message.split(":", 1)[1].strip()
            
            # Validate device ID exists in our system
            device_status = await device_manager.get_device_status(device_id)
            if device_status:
                self.device_id = device_id
                await self._send_message("DEVICE_OK\r\n")
                logger.info(f"Device {device_id} identified for client {self.client_address}")
                
                # Register this connection with the server
                self.server.register_device_connection(device_id, self)
            else:
                await self._send_message("DEVICE_UNKNOWN\r\n")
                logger.warning(f"Unknown device ID {device_id} from {self.client_address}")
                
        except Exception as e:
            logger.error(f"Device identification error for {self.client_address}: {str(e)}")
            await self._send_message("DEVICE_ERROR\r\n")
    
    async def _handle_hl7_message(self, message: str):
        """Handle HL7 message"""
        try:
            logger.info(f"Processing HL7 message from {self.client_address}")
            
            # Queue message for automatic processing
            message_data = {
                'type': 'HL7',
                'content': message,
                'equipment_id': self.device_id or f"tcp_{self.client_address[0]}",
                'timestamp': datetime.utcnow().isoformat(),
                'client_address': str(self.client_address)
            }
            
            # Send to data processor for automatic handling
            if self.server.data_processor:
                await self.server.data_processor.queue_message(message_data)
                
                # Send acknowledgment - assume success for queuing
                ack_message = self._create_hl7_ack(message, "AA")  # Application Accept
                await self._send_message(ack_message)
                logger.info(f"HL7 message queued for processing from {self.client_address}")
            else:
                # Fallback to old processing if no data processor
                response = hl7_handler.process_message(message)
                
                # Send acknowledgment
                if response.get('success'):
                    ack_message = self._create_hl7_ack(message, "AA")  # Application Accept
                    await self._send_message(ack_message)
                    logger.info(f"HL7 message processed successfully from {self.client_address}")
                else:
                    ack_message = self._create_hl7_ack(message, "AE")  # Application Error
                    await self._send_message(ack_message)
                    logger.error(f"HL7 message processing failed from {self.client_address}")
            
            # Notify device manager if device is identified
            if self.device_id:
                await device_manager._on_message_received(self.device_id, message, "HL7")
                
        except Exception as e:
            logger.error(f"HL7 processing error from {self.client_address}: {str(e)}")
            ack_message = self._create_hl7_ack(message, "AR")  # Application Reject
            await self._send_message(ack_message)
    
    async def _handle_astm_message(self, message: str):
        """Handle ASTM message (E1381/E1394 format)"""
        try:
            logger.info(f"Processing ASTM message from {self.client_address}")
            
            # Queue message for automatic processing
            message_data = {
                'type': 'ASTM',
                'content': message,
                'equipment_id': self.device_id or f"tcp_{self.client_address[0]}",
                'timestamp': datetime.utcnow().isoformat(),
                'client_address': str(self.client_address)
            }
            
            # Send to data processor for automatic handling
            if self.server.data_processor:
                await self.server.data_processor.queue_message(message_data)
                
                # Send ASTM acknowledgment - assume success for queuing
                await self._send_message(astm_handler.create_acknowledgment(True))
                logger.info(f"ASTM message queued for processing from {self.client_address}")
            else:
                # Fallback to old processing if no data processor
                response = astm_handler.process_message(message)
                
                if response.get('status') != 'success':
                    logger.error(f"Failed to process ASTM message from {self.client_address}: {response.get('error', 'Unknown error')}")
                    await self._send_message(astm_handler.create_acknowledgment(False))
                    return
                
                # Log processed records
                records_processed = response.get('records_processed', 0)
                logger.info(f"Successfully processed {records_processed} ASTM records from {self.client_address}")
                
                # Process each record for integration with LIS database
                for record_data in response.get('records', []):
                    await self._integrate_astm_record(record_data)
                
                # Send ASTM acknowledgment
                await self._send_message(astm_handler.create_acknowledgment(True))
            
            # Notify device manager if device is identified
            if self.device_id:
                await device_manager._on_message_received(self.device_id, message, "ASTM")
                
        except Exception as e:
            logger.error(f"ASTM processing error from {self.client_address}: {str(e)}")
            await self._send_message(astm_handler.create_acknowledgment(False))
    
    async def _integrate_astm_record(self, record_data: Dict[str, Any]):
        """Integrate ASTM record data with LIS database"""
        try:
            record_type = record_data.get('type')
            data = record_data.get('data', {})
            
            if record_type == 'P':  # Patient record
                await self._process_astm_patient_data(data)
            elif record_type == 'O':  # Order record
                await self._process_astm_order_data(data)
            elif record_type == 'R':  # Result record
                await self._process_astm_result_data(data)
            elif record_type == 'C':  # Comment record
                await self._process_astm_comment_data(data)
            elif record_type == 'H':  # Header record
                await self._process_astm_header_data(data)
            
        except Exception as e:
            logger.error(f"Error integrating ASTM record: {str(e)}")
    
    async def _process_astm_patient_data(self, data: Dict[str, Any]):
        """Process ASTM patient data for database integration"""
        try:
            patient_id = data.get('practice_patient_id') or data.get('laboratory_patient_id')
            patient_name = data.get('patient_name', '')
            
            if patient_id:
                logger.info(f"ASTM Patient data received - ID: {patient_id}, Name: {patient_name}")
                # TODO: Create or update Patient record in database
                # This would use the Patient model to create/update patient information
            
        except Exception as e:
            logger.error(f"Error processing ASTM patient data: {str(e)}")
    
    async def _process_astm_order_data(self, data: Dict[str, Any]):
        """Process ASTM order data for database integration"""
        try:
            specimen_id = data.get('specimen_id', '')
            test_info = data.get('test_information', {})
            test_id = test_info.get('test_id', '') if isinstance(test_info, dict) else str(test_info)
            
            if specimen_id and test_id:
                logger.info(f"ASTM Order data received - Specimen: {specimen_id}, Test: {test_id}")
                # TODO: Create TestOrder record in database
                # This would use the TestOrder and Sample models
            
        except Exception as e:
            logger.error(f"Error processing ASTM order data: {str(e)}")
    
    async def _process_astm_result_data(self, data: Dict[str, Any]):
        """Process ASTM result data for database integration"""
        try:
            test_info = data.get('test_information', {})
            test_id = test_info.get('test_id', '') if isinstance(test_info, dict) else str(test_info)
            value = data.get('measurement_value', '')
            units = data.get('units', '')
            flags = data.get('abnormal_flags', '')
            
            if test_id and value:
                logger.info(f"ASTM Result data received - Test: {test_id}, Value: {value} {units}, Flags: {flags}")
                # TODO: Create TestResult record in database
                # This would use the TestResult model
            
        except Exception as e:
            logger.error(f"Error processing ASTM result data: {str(e)}")
    
    async def _process_astm_comment_data(self, data: Dict[str, Any]):
        """Process ASTM comment data"""
        try:
            comment_text = data.get('comment_text', '')
            comment_type = data.get('comment_type', '')
            
            if comment_text:
                logger.info(f"ASTM Comment received - Type: {comment_type}, Text: {comment_text}")
                # TODO: Store comment with related record
            
        except Exception as e:
            logger.error(f"Error processing ASTM comment data: {str(e)}")
    
    async def _process_astm_header_data(self, data: Dict[str, Any]):
        """Process ASTM header data"""
        try:
            sender_name = data.get('sender_name', '')
            version = data.get('version', '')
            
            logger.info(f"ASTM Header processed - Sender: {sender_name}, Version: {version}")
            # Store header information for session context if needed
            
        except Exception as e:
            logger.error(f"Error processing ASTM header data: {str(e)}")
    
    async def _handle_json_message(self, message: str):
        """Handle JSON message"""
        try:
            logger.info(f"Processing JSON message from {self.client_address}")
            
            # Parse JSON
            data = json.loads(message)
            
            # Process based on message type
            msg_type = data.get('type', 'unknown')
            
            if msg_type == 'test_result':
                await self._process_test_result(data)
            elif msg_type == 'order_status':
                await self._process_order_status(data)
            elif msg_type == 'equipment_status':
                await self._process_equipment_status(data)
            else:
                logger.warning(f"Unknown JSON message type '{msg_type}' from {self.client_address}")
            
            # Send acknowledgment
            await self._send_message(json.dumps({"status": "received", "timestamp": datetime.utcnow().isoformat()}) + "\r\n")
            
            # Notify device manager if device is identified
            if self.device_id:
                await device_manager._on_message_received(self.device_id, message, "JSON")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {self.client_address}")
            await self._send_message(json.dumps({"error": "Invalid JSON"}) + "\r\n")
        except Exception as e:
            logger.error(f"JSON processing error from {self.client_address}: {str(e)}")
            await self._send_message(json.dumps({"error": str(e)}) + "\r\n")
    
    async def _handle_command_message(self, message: str):
        """Handle command message"""
        try:
            logger.info(f"Processing command from {self.client_address}: {message}")
            
            command = message.strip().upper()
            
            if command == "PING":
                await self._send_message("PONG\r\n")
            elif command == "STATUS":
                status = {
                    "device_id": self.device_id,
                    "connected_at": self.connected_at.isoformat(),
                    "message_count": self.message_count,
                    "error_count": self.error_count,
                    "authenticated": self.is_authenticated
                }
                await self._send_message(json.dumps(status) + "\r\n")
            elif command == "DISCONNECT":
                await self._send_message("BYE\r\n")
                raise ConnectionError("Client requested disconnection")
            else:
                await self._send_message(f"UNKNOWN_COMMAND: {command}\r\n")
                
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Command processing error from {self.client_address}: {str(e)}")
            await self._send_message(f"COMMAND_ERROR: {str(e)}\r\n")
    
    async def _handle_raw_message(self, message: str):
        """Handle raw/unknown message"""
        try:
            logger.info(f"Processing raw message from {self.client_address}")
            
            # Log the message for debugging
            logger.debug(f"Raw message content: {message}")
            
            # Send basic acknowledgment
            await self._send_message("RECEIVED\r\n")
            
            # Notify device manager if device is identified
            if self.device_id:
                await device_manager._on_message_received(self.device_id, message, "RAW")
                
        except Exception as e:
            logger.error(f"Raw message processing error from {self.client_address}: {str(e)}")
    
    def _detect_message_type(self, message: str) -> str:
        """Detect the type of message"""
        message = message.strip()
        
        # Check for HL7 message
        if message.startswith('MSH|'):
            return 'HL7'
        
        # Check for ASTM message
        if any(message.startswith(prefix) for prefix in ['H|', 'P|', 'O|', 'R|', 'L|']):
            return 'ASTM'
        
        # Check for JSON
        if message.startswith('{') and message.endswith('}'):
            return 'JSON'
        
        # Check for commands
        if message.upper() in ['PING', 'STATUS', 'DISCONNECT']:
            return 'COMMAND'
        
        # Default to raw
        return 'RAW'
    
    def _create_hl7_ack(self, original_message: str, ack_code: str) -> str:
        """Create HL7 acknowledgment message"""
        try:
            # Extract control ID from original message
            control_id = "UNKNOWN"
            if '|' in original_message:
                segments = original_message.split('\r')
                msh_segment = segments[0] if segments else original_message
                fields = msh_segment.split('|')
                if len(fields) > 9:
                    control_id = fields[9]
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Build ACK message
            msh = f"MSH|^~\\&|LIS|LAB|DEVICE|ANALYZER|{timestamp}||ACK|{control_id}|P|2.5"
            msa = f"MSA|{ack_code}|{control_id}"
            
            return f"{msh}\r{msa}\r"
            
        except Exception as e:
            logger.error(f"Error creating HL7 ACK: {str(e)}")
            return f"MSH|^~\\&|LIS|LAB|DEVICE|ANALYZER|{datetime.now().strftime('%Y%m%d%H%M%S')}||ACK|ERROR|P|2.5\rMSA|AR|ERROR\r"
    
    async def _process_test_result(self, data: Dict):
        """Process test result from JSON message"""
        try:
            # TODO: Store test result in database
            logger.info(f"Test result received: {data.get('test_code', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error processing test result: {str(e)}")
    
    async def _process_order_status(self, data: Dict):
        """Process order status update from JSON message"""
        try:
            # TODO: Update order status in database
            logger.info(f"Order status update: {data.get('order_number', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error processing order status: {str(e)}")
    
    async def _process_equipment_status(self, data: Dict):
        """Process equipment status update from JSON message"""
        try:
            # TODO: Update equipment status
            logger.info(f"Equipment status update: {data.get('equipment_id', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error processing equipment status: {str(e)}")
    
    async def _send_message(self, message: str):
        """Send message to client"""
        try:
            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()
            logger.debug(f"Sent message to {self.client_address}: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error sending message to {self.client_address}: {str(e)}")
            raise
    
    async def _cleanup(self):
        """Clean up connection"""
        try:
            # Unregister from server
            if self.device_id:
                self.server.unregister_device_connection(self.device_id)
            
            # Close writer
            if self.writer and not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
            
            logger.info(f"Client {self.client_address} disconnected, processed {self.message_count} messages")
            
        except Exception as e:
            logger.error(f"Error during cleanup for {self.client_address}: {str(e)}")


class TCPServer:
    """TCP server for handling medical equipment connections"""
    
    def __init__(self, data_processor=None):
        """Initialize TCP server"""
        self.host = settings.comm_tcp_host
        self.port = settings.comm_tcp_port
        self.server: Optional[asyncio.Server] = None
        self.clients: Set[TCPClientHandler] = set()
        self.device_connections: Dict[str, TCPClientHandler] = {}
        self.running = False
        self.data_processor = data_processor  # Reference to DataProcessor for automatic message handling
        
        logger.info(f"TCPServer initialized on {self.host}:{self.port}")
    
    async def start(self):
        """Start the TCP server"""
        try:
            logger.info(f"Starting TCP server on {self.host}:{self.port}...")
            
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
                reuse_address=True
            )
            
            self.running = True
            
            # Log server information
            addr = self.server.sockets[0].getsockname()
            logger.info(f"TCP server started on {addr[0]}:{addr[1]}")
            
            # Start serving
            await self.server.start_serving()
            
        except Exception as e:
            logger.error(f"Failed to start TCP server: {str(e)}")
            raise LISException(f"TCP server startup failed: {str(e)}")
    
    async def stop(self):
        """Stop the TCP server"""
        try:
            logger.info("Stopping TCP server...")
            self.running = False
            
            # Close all client connections
            for client in list(self.clients):
                await client._cleanup()
            
            # Close server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            logger.info("TCP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping TCP server: {str(e)}")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle new client connection"""
        client = None
        try:
            client = TCPClientHandler(reader, writer, self)
            self.clients.add(client)
            
            await client.handle_connection()
            
        except Exception as e:
            logger.error(f"Error handling client: {str(e)}")
        finally:
            if client:
                self.clients.discard(client)
                await client._cleanup()
    
    def register_device_connection(self, device_id: str, client: TCPClientHandler):
        """Register a device connection"""
        self.device_connections[device_id] = client
        logger.info(f"Registered device connection: {device_id}")
    
    def unregister_device_connection(self, device_id: str):
        """Unregister a device connection"""
        if device_id in self.device_connections:
            del self.device_connections[device_id]
            logger.info(f"Unregistered device connection: {device_id}")
    
    async def send_to_device(self, device_id: str, message: str) -> bool:
        """Send message to specific device"""
        try:
            if device_id in self.device_connections:
                client = self.device_connections[device_id]
                await client._send_message(message)
                return True
            else:
                logger.warning(f"Device {device_id} not connected")
                return False
        except Exception as e:
            logger.error(f"Error sending message to device {device_id}: {str(e)}")
            return False
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "total_clients": len(self.clients),
            "device_connections": len(self.device_connections),
            "connected_devices": list(self.device_connections.keys())
        }


# Global TCP server instance
tcp_server = TCPServer() 