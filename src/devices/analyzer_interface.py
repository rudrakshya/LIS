"""
Analyzer Interface for Laboratory Information System
Handles communication with individual medical analyzers and devices
"""

import asyncio
import logging
import socket
import serial_asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import json

from ..core.config import settings
from ..core.exceptions import DeviceException, DeviceConnectionException, DeviceTimeoutException
from ..models import Equipment, CommunicationProtocol
from ..communication.hl7_handler import hl7_handler

logger = logging.getLogger(__name__)


class AnalyzerInterface:
    """Interface for communicating with a single medical analyzer"""
    
    def __init__(self, equipment: Equipment):
        self.equipment = equipment
        self.connection = None
        self.is_connected = False
        self.last_communication = None
        self.message_count = 0
        self.error_count = 0
        self.message_callback: Optional[Callable] = None
        
        # Communication settings
        self.protocol = equipment.communication_protocol
        self.host = equipment.ip_address
        self.port = equipment.port
        self.serial_port = equipment.serial_port
        self.baud_rate = equipment.baud_rate or 9600
        
        logger.info(f"AnalyzerInterface initialized for {equipment.equipment_id}")
    
    def set_message_callback(self, callback: Callable):
        """Set callback function for incoming messages"""
        self.message_callback = callback
    
    async def connect(self) -> bool:
        """Establish connection to the analyzer"""
        try:
            if self.is_connected:
                logger.info(f"Device {self.equipment.equipment_id} already connected")
                return True
            
            if self.protocol == CommunicationProtocol.TCP_IP:
                return await self._connect_tcp()
            elif self.protocol == CommunicationProtocol.SERIAL:
                return await self._connect_serial()
            else:
                logger.warning(f"Unsupported protocol: {self.protocol}")
                return False
                
        except Exception as e:
            logger.error(f"Connection failed for {self.equipment.equipment_id}: {str(e)}")
            self.error_count += 1
            return False
    
    async def disconnect(self):
        """Disconnect from the analyzer"""
        try:
            if not self.is_connected:
                return
            
            if self.connection:
                if hasattr(self.connection, 'close'):
                    self.connection.close()
                elif hasattr(self.connection, 'writer') and self.connection.writer:
                    self.connection.writer.close()
                    await self.connection.writer.wait_closed()
            
            self.connection = None
            self.is_connected = False
            
            logger.info(f"Disconnected from device {self.equipment.equipment_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from {self.equipment.equipment_id}: {str(e)}")
    
    async def send_message(self, message: str) -> bool:
        """Send message to the analyzer"""
        try:
            if not self.is_connected:
                raise DeviceConnectionException(f"Device {self.equipment.equipment_id} not connected")
            
            if self.protocol == CommunicationProtocol.TCP_IP:
                return await self._send_tcp_message(message)
            elif self.protocol == CommunicationProtocol.SERIAL:
                return await self._send_serial_message(message)
            else:
                logger.error(f"Unsupported protocol for sending: {self.protocol}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {self.equipment.equipment_id}: {str(e)}")
            self.error_count += 1
            return False
    
    async def send_order(self, order_data: Dict[str, Any]) -> bool:
        """Send test order to the analyzer"""
        try:
            # Convert order data to appropriate message format
            if self.protocol in [CommunicationProtocol.TCP_IP, CommunicationProtocol.HL7]:
                # Generate HL7 order message
                hl7_message = self._create_hl7_order(order_data)
                return await self.send_message(hl7_message)
            else:
                # For other protocols, send as JSON for now
                json_message = json.dumps(order_data)
                return await self.send_message(json_message)
                
        except Exception as e:
            logger.error(f"Error sending order to {self.equipment.equipment_id}: {str(e)}")
            return False
    
    async def ping(self) -> bool:
        """Check if device is responsive"""
        try:
            if not self.is_connected:
                return False
            
            # Send a simple ping/heartbeat message
            ping_message = "PING\r\n"
            success = await self.send_message(ping_message)
            
            if success:
                self.last_communication = datetime.utcnow()
            
            return success
            
        except Exception as e:
            logger.error(f"Ping failed for {self.equipment.equipment_id}: {str(e)}")
            return False
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get device configuration"""
        return {
            'equipment_id': self.equipment.equipment_id,
            'name': self.equipment.name,
            'manufacturer': self.equipment.manufacturer,
            'model': self.equipment.model,
            'protocol': self.protocol.value if self.protocol else None,
            'host': self.host,
            'port': self.port,
            'serial_port': self.serial_port,
            'baud_rate': self.baud_rate,
            'supported_tests': self.equipment.supported_tests,
            'sample_types': self.equipment.sample_types
        }
    
    async def _connect_tcp(self) -> bool:
        """Establish TCP/IP connection"""
        try:
            if not self.host or not self.port:
                raise DeviceConnectionException(f"Missing TCP connection parameters for {self.equipment.equipment_id}")
            
            logger.info(f"Connecting to {self.equipment.equipment_id} at {self.host}:{self.port}")
            
            # Create TCP connection with timeout
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=settings.device_timeout
            )
            
            self.connection = {'reader': reader, 'writer': writer}
            self.is_connected = True
            self.last_communication = datetime.utcnow()
            
            # Start listening for incoming messages
            asyncio.create_task(self._listen_tcp())
            
            logger.info(f"TCP connection established for {self.equipment.equipment_id}")
            return True
            
        except asyncio.TimeoutError:
            raise DeviceTimeoutException(f"Connection timeout for {self.equipment.equipment_id}")
        except Exception as e:
            raise DeviceConnectionException(f"TCP connection failed for {self.equipment.equipment_id}: {str(e)}")
    
    async def _connect_serial(self) -> bool:
        """Establish serial connection"""
        try:
            if not self.serial_port:
                raise DeviceConnectionException(f"Missing serial port for {self.equipment.equipment_id}")
            
            logger.info(f"Connecting to {self.equipment.equipment_id} on {self.serial_port}")
            
            # Create serial connection
            reader, writer = await serial_asyncio.open_serial_connection(
                url=self.serial_port,
                baudrate=self.baud_rate,
                timeout=settings.comm_serial_timeout
            )
            
            self.connection = {'reader': reader, 'writer': writer}
            self.is_connected = True
            self.last_communication = datetime.utcnow()
            
            # Start listening for incoming messages
            asyncio.create_task(self._listen_serial())
            
            logger.info(f"Serial connection established for {self.equipment.equipment_id}")
            return True
            
        except Exception as e:
            raise DeviceConnectionException(f"Serial connection failed for {self.equipment.equipment_id}: {str(e)}")
    
    async def _send_tcp_message(self, message: str) -> bool:
        """Send message via TCP"""
        try:
            writer = self.connection['writer']
            
            # Add message terminators if needed
            if not message.endswith('\r\n'):
                message += '\r\n'
            
            writer.write(message.encode('utf-8'))
            await writer.drain()
            
            self.message_count += 1
            self.last_communication = datetime.utcnow()
            
            logger.debug(f"Sent TCP message to {self.equipment.equipment_id}: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"TCP send error for {self.equipment.equipment_id}: {str(e)}")
            return False
    
    async def _send_serial_message(self, message: str) -> bool:
        """Send message via serial"""
        try:
            writer = self.connection['writer']
            
            # Add message terminators if needed
            if not message.endswith('\r\n'):
                message += '\r\n'
            
            writer.write(message.encode('utf-8'))
            await writer.drain()
            
            self.message_count += 1
            self.last_communication = datetime.utcnow()
            
            logger.debug(f"Sent serial message to {self.equipment.equipment_id}: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Serial send error for {self.equipment.equipment_id}: {str(e)}")
            return False
    
    async def _listen_tcp(self):
        """Listen for incoming TCP messages"""
        try:
            reader = self.connection['reader']
            
            while self.is_connected:
                try:
                    # Read message with timeout
                    data = await asyncio.wait_for(
                        reader.readuntil(b'\r\n'),
                        timeout=settings.device_response_timeout
                    )
                    
                    if data:
                        message = data.decode('utf-8').strip()
                        await self._handle_incoming_message(message)
                    
                except asyncio.TimeoutError:
                    # Timeout is normal, continue listening
                    continue
                except asyncio.IncompleteReadError:
                    # Connection closed
                    break
                    
        except Exception as e:
            logger.error(f"TCP listen error for {self.equipment.equipment_id}: {str(e)}")
        finally:
            self.is_connected = False
    
    async def _listen_serial(self):
        """Listen for incoming serial messages"""
        try:
            reader = self.connection['reader']
            
            while self.is_connected:
                try:
                    # Read message with timeout
                    data = await asyncio.wait_for(
                        reader.readuntil(b'\r\n'),
                        timeout=settings.device_response_timeout
                    )
                    
                    if data:
                        message = data.decode('utf-8').strip()
                        await self._handle_incoming_message(message)
                    
                except asyncio.TimeoutError:
                    # Timeout is normal, continue listening
                    continue
                except asyncio.IncompleteReadError:
                    # Connection closed
                    break
                    
        except Exception as e:
            logger.error(f"Serial listen error for {self.equipment.equipment_id}: {str(e)}")
        finally:
            self.is_connected = False
    
    async def _handle_incoming_message(self, message: str):
        """Handle incoming message from analyzer"""
        try:
            self.last_communication = datetime.utcnow()
            self.message_count += 1
            
            logger.debug(f"Received message from {self.equipment.equipment_id}: {message[:50]}...")
            
            # Determine message type
            message_type = self._detect_message_type(message)
            
            # Call message callback if set
            if self.message_callback:
                await self.message_callback(self.equipment.equipment_id, message, message_type)
            
        except Exception as e:
            logger.error(f"Error handling incoming message from {self.equipment.equipment_id}: {str(e)}")
            self.error_count += 1
    
    def _detect_message_type(self, message: str) -> str:
        """Detect the type of incoming message"""
        message = message.strip()
        
        # Check for HL7 message
        if message.startswith('MSH|'):
            return 'HL7'
        
        # Check for ASTM message
        if message.startswith('H|') or message.startswith('P|') or message.startswith('O|') or message.startswith('R|'):
            return 'ASTM'
        
        # Check for JSON
        if message.startswith('{') and message.endswith('}'):
            return 'JSON'
        
        # Default to raw
        return 'RAW'
    
    def _create_hl7_order(self, order_data: Dict[str, Any]) -> str:
        """Create HL7 order message from order data"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            control_id = f"ORD_{timestamp}"
            
            # Extract order information
            patient_id = order_data.get('patient_id', 'UNKNOWN')
            order_number = order_data.get('order_number', control_id)
            test_code = order_data.get('test_code', 'UNKNOWN')
            test_name = order_data.get('test_name', 'Unknown Test')
            
            # Build HL7 ORM message
            msh = f"MSH|^~\\&|LIS|LAB|{self.equipment.equipment_id}|ANALYZER|{timestamp}||ORM^O01|{control_id}|P|2.5"
            pid = f"PID|1||{patient_id}||||||||||||||||||||||||||||"
            orc = f"ORC|NW|{order_number}|||||||{timestamp}"
            obr = f"OBR|1|{order_number}||{test_code}^{test_name}|||{timestamp}"
            
            # Combine segments
            hl7_message = f"{msh}\r{pid}\r{orc}\r{obr}\r"
            
            return hl7_message
            
        except Exception as e:
            logger.error(f"Error creating HL7 order message: {str(e)}")
            raise DeviceException(f"Failed to create HL7 order: {str(e)}") 