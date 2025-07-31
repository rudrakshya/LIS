"""
Serial Communication Handler for BT-1500 Sensacore Analyzer
Handles RS-232 and USB serial communication with BT-1500 machine
"""

import asyncio
import logging
import serial_asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import re

from ..core.config import settings
from ..core.exceptions import SerialCommunicationException
from ..devices.parsers.bt1500_parser import BT1500Parser

logger = logging.getLogger(__name__)


class BT1500SerialHandler:
    """Serial communication handler for BT-1500 Sensacore analyzer"""
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: int = 30):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parser = BT1500Parser()
        
        # Serial connection
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False
        
        # Message handling
        self.message_callback: Optional[Callable] = None
        self.buffer = ""
        self.last_communication = datetime.utcnow()
        
        # BT-1500 specific settings
        self.expected_terminator = '\r\n'
        self.max_buffer_size = 8192
        
        logger.info(f"BT1500SerialHandler initialized for port {port}")
    
    async def connect(self) -> bool:
        """Establish serial connection to BT-1500"""
        try:
            logger.info(f"Connecting to BT-1500 on {self.port}")
            
            # Create serial connection with BT-1500 specific settings
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.port,
                baudrate=self.baudrate,
                bytesize=8,  # BT-1500 uses 8 data bits
                parity='N',   # No parity
                stopbits=1,   # 1 stop bit
                timeout=self.timeout
            )
            
            self.is_connected = True
            self.last_communication = datetime.utcnow()
            
            # Start listening for data
            asyncio.create_task(self._listen_for_data())
            
            logger.info(f"Successfully connected to BT-1500 on {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to BT-1500 on {self.port}: {str(e)}")
            raise SerialCommunicationException(f"Connection failed: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from BT-1500"""
        try:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            
            self.is_connected = False
            self.reader = None
            self.writer = None
            
            logger.info(f"Disconnected from BT-1500 on {self.port}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from BT-1500: {str(e)}")
    
    def set_message_callback(self, callback: Callable):
        """Set callback for received messages"""
        self.message_callback = callback
    
    async def _listen_for_data(self):
        """Listen for incoming data from BT-1500"""
        try:
            while self.is_connected and self.reader:
                try:
                    # Read data with timeout
                    data = await asyncio.wait_for(
                        self.reader.readuntil(self.expected_terminator.encode()),
                        timeout=self.timeout
                    )
                    
                    if data:
                        message = data.decode('utf-8', errors='ignore').strip()
                        await self._process_message(message)
                        self.last_communication = datetime.utcnow()
                    
                except asyncio.TimeoutError:
                    # Timeout is normal, continue listening
                    continue
                except asyncio.IncompleteReadError:
                    # Connection closed
                    break
                except Exception as e:
                    logger.error(f"Error reading from BT-1500: {str(e)}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error in BT-1500 listener: {str(e)}")
        finally:
            self.is_connected = False
    
    async def _process_message(self, message: str):
        """Process received message from BT-1500"""
        try:
            logger.debug(f"Received BT-1500 message: {message[:100]}...")
            
            # Add to buffer
            self.buffer += message + '\n'
            
            # Check if we have a complete BT-1500 report
            if self._is_complete_report():
                await self._process_complete_report()
                
        except Exception as e:
            logger.error(f"Error processing BT-1500 message: {str(e)}")
    
    def _is_complete_report(self) -> bool:
        """Check if buffer contains a complete BT-1500 report"""
        # Look for end markers that indicate complete reports
        end_markers = [
            'Oct-31-13 12:18:29',
            'Oct-31-13 12:27:32',
            '_ _ _ _ _ _ _ _ _ _ _',
            '_ _ _ _ _ _ _ _ _'
        ]
        
        # Check for timestamp patterns
        timestamp_pattern = r'\d{2}-\w{3}-\d{2} \d{2}:\d{2}:\d{2}'
        
        # Check for separator lines
        separator_pattern = r'_ _ _ _ _ _ _ _ _'
        
        has_timestamp = re.search(timestamp_pattern, self.buffer)
        has_separator = re.search(separator_pattern, self.buffer)
        
        return has_timestamp and has_separator
    
    async def _process_complete_report(self):
        """Process a complete BT-1500 report"""
        try:
            logger.info("Processing complete BT-1500 report")
            
            # Validate the data format
            if not self.parser.validate_data(self.buffer):
                logger.warning("Invalid BT-1500 data format")
                self.buffer = ""
                return
            
            # Parse the raw data
            results = self.parser.parse_raw_data(self.buffer)
            
            # Process each result
            for result in results:
                await self._handle_bt1500_result(result)
            
            # Clear buffer after processing
            self.buffer = ""
            
        except Exception as e:
            logger.error(f"Error processing BT-1500 report: {str(e)}")
            self.buffer = ""
    
    async def _handle_bt1500_result(self, result):
        """Handle a parsed BT-1500 result"""
        try:
            logger.info(f"Handling BT-1500 result: {result.test_type}")
            
            # Convert to HL7 if it's an analyze sample result
            if result.test_type == 'ANALYZE_SAMPLE':
                hl7_message = self.parser.convert_to_hl7(result)
                
                # Call message callback if set
                if self.message_callback:
                    await self.message_callback({
                        'type': 'hl7',
                        'message': hl7_message,
                        'source': 'BT-1500',
                        'timestamp': result.timestamp,
                        'raw_data': result.raw_data
                    })
                else:
                    logger.info(f"Generated HL7 message for BT-1500 result")
                    logger.debug(f"HL7 Message: {hl7_message}")
            
            # Store calibration data for reference
            elif result.test_type in ['CALIBRATION_REPORT', 'CALIBRATION_SLOPE']:
                logger.info(f"Stored calibration data: {result.test_type}")
                # Could store calibration data for quality control
            
        except Exception as e:
            logger.error(f"Error handling BT-1500 result: {str(e)}")
    
    async def send_command(self, command: str) -> bool:
        """Send command to BT-1500 (if supported)"""
        try:
            if not self.is_connected or not self.writer:
                raise SerialCommunicationException("Not connected to BT-1500")
            
            # Add terminator if needed
            if not command.endswith('\r\n'):
                command += '\r\n'
            
            # Send command
            self.writer.write(command.encode('utf-8'))
            await self.writer.drain()
            
            logger.info(f"Sent command to BT-1500: {command.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending command to BT-1500: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of BT-1500 connection"""
        return {
            'connected': self.is_connected,
            'port': self.port,
            'baudrate': self.baudrate,
            'last_communication': self.last_communication.isoformat(),
            'buffer_size': len(self.buffer),
            'has_callback': self.message_callback is not None
        }
    
    def get_buffer_content(self) -> str:
        """Get current buffer content for debugging"""
        return self.buffer


class BT1500DeviceManager:
    """Manager for BT-1500 device connections"""
    
    def __init__(self):
        self.devices: Dict[str, BT1500SerialHandler] = {}
        self.logger = logging.getLogger(__name__)
    
    async def add_device(self, device_id: str, port: str, baudrate: int = 9600) -> bool:
        """Add and connect to a BT-1500 device"""
        try:
            handler = BT1500SerialHandler(port, baudrate)
            
            # Set message callback
            handler.set_message_callback(self._handle_device_message)
            
            # Connect to device
            success = await handler.connect()
            
            if success:
                self.devices[device_id] = handler
                self.logger.info(f"Added BT-1500 device {device_id} on {port}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to add BT-1500 device {device_id}: {str(e)}")
            return False
    
    async def remove_device(self, device_id: str):
        """Remove and disconnect a BT-1500 device"""
        try:
            if device_id in self.devices:
                handler = self.devices[device_id]
                await handler.disconnect()
                del self.devices[device_id]
                self.logger.info(f"Removed BT-1500 device {device_id}")
                
        except Exception as e:
            self.logger.error(f"Error removing BT-1500 device {device_id}: {str(e)}")
    
    async def _handle_device_message(self, message_data: Dict[str, Any]):
        """Handle messages from BT-1500 devices"""
        try:
            self.logger.info(f"Received message from BT-1500: {message_data['type']}")
            
            # Here you would integrate with the main LIS system
            # For example, store results in database, forward to HL7 handler, etc.
            
        except Exception as e:
            self.logger.error(f"Error handling BT-1500 message: {str(e)}")
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device"""
        if device_id in self.devices:
            return self.devices[device_id].get_status()
        return None
    
    def get_all_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all devices"""
        return {device_id: handler.get_status() 
                for device_id, handler in self.devices.items()}


# Global BT-1500 device manager instance
bt1500_manager = BT1500DeviceManager() 