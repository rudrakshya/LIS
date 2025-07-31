"""
Device Manager for Laboratory Information System
Manages connections and communication with medical analyzers and equipment
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import json
from enum import Enum

from ..core.config import settings
from ..core.exceptions import DeviceException, DeviceConnectionException, DeviceTimeoutException
from ..models import Equipment, EquipmentStatus, CommunicationProtocol
from ..communication.hl7_handler import hl7_handler
from .analyzer_interface import AnalyzerInterface
from ..communication.serial_handler import bt1500_manager
from ..database.session import get_session
from ..models import EquipmentType

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class DeviceManager:
    """Main device manager for handling multiple analyzer connections"""
    
    def __init__(self):
        self.devices: Dict[str, AnalyzerInterface] = {}
        self.connection_status: Dict[str, ConnectionStatus] = {}
        self.message_handlers: Dict[str, Callable] = {
            'HL7': self._handle_hl7_message,
            'ASTM': self._handle_astm_message,
            'RAW': self._handle_raw_message
        }
        self.running = False
        self.monitoring_task = None
        
        logger.info("DeviceManager initialized")
    
    async def start(self):
        """Start the device manager"""
        try:
            self.running = True
            logger.info("Starting DeviceManager...")
            
            # Load equipment from database and establish connections
            await self._load_equipment()
            
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitor_devices())
            
            logger.info("DeviceManager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start DeviceManager: {str(e)}")
            raise DeviceException(f"DeviceManager startup failed: {str(e)}")
    
    async def stop(self):
        """Stop the device manager"""
        try:
            logger.info("Stopping DeviceManager...")
            self.running = False
            
            # Cancel monitoring task
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect all devices
            await self._disconnect_all_devices()
            
            logger.info("DeviceManager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping DeviceManager: {str(e)}")
    
    async def add_device(self, equipment: Equipment) -> bool:
        """Add a new device to the manager"""
        try:
            device_id = equipment.equipment_id
            
            if device_id in self.devices:
                logger.warning(f"Device {device_id} already exists")
                return False
            
            # Create analyzer interface
            analyzer = AnalyzerInterface(equipment)
            
            # Set up message callback
            analyzer.set_message_callback(self._on_message_received)
            
            # Add to devices
            self.devices[device_id] = analyzer
            self.connection_status[device_id] = ConnectionStatus.DISCONNECTED
            
            # Attempt to connect
            if equipment.is_active:
                await self._connect_device(device_id)
            
            logger.info(f"Added device: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add device {equipment.equipment_id}: {str(e)}")
            return False
    
    async def remove_device(self, device_id: str) -> bool:
        """Remove a device from the manager"""
        try:
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
            
            # Disconnect the device
            await self._disconnect_device(device_id)
            
            # Remove from devices
            del self.devices[device_id]
            del self.connection_status[device_id]
            
            logger.info(f"Removed device: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove device {device_id}: {str(e)}")
            return False
    
    async def send_order_to_device(self, device_id: str, order_data: Dict[str, Any]) -> bool:
        """Send test order to specific device"""
        try:
            if device_id not in self.devices:
                raise DeviceException(f"Device {device_id} not found")
            
            device = self.devices[device_id]
            
            if self.connection_status[device_id] != ConnectionStatus.CONNECTED:
                raise DeviceConnectionException(f"Device {device_id} not connected")
            
            # Send order to device
            success = await device.send_order(order_data)
            
            if success:
                logger.info(f"Order sent to device {device_id}")
            else:
                logger.warning(f"Failed to send order to device {device_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending order to device {device_id}: {str(e)}")
            return False
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific device"""
        try:
            if device_id not in self.devices:
                return None
            
            device = self.devices[device_id]
            connection_status = self.connection_status[device_id]
            
            status = {
                'device_id': device_id,
                'connection_status': connection_status.value,
                'equipment_status': device.equipment.status.value,
                'is_online': connection_status == ConnectionStatus.CONNECTED,
                'last_communication': device.last_communication.isoformat() if device.last_communication else None,
                'message_count': device.message_count,
                'error_count': device.error_count,
                'configuration': device.get_configuration()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting device status {device_id}: {str(e)}")
            return None
    
    async def get_all_devices_status(self) -> List[Dict[str, Any]]:
        """Get status of all devices"""
        statuses = []
        
        for device_id in self.devices:
            status = await self.get_device_status(device_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    async def add_bt1500_device(self, device_id: str, port: str, baudrate: int = 9600) -> bool:
        """Add a BT-1500 Sensacore analyzer device"""
        try:
            # Add to BT-1500 manager
            success = await bt1500_manager.add_device(device_id, port, baudrate)
            
            if success:
                # Register with main device manager
                equipment = Equipment(
                    equipment_id=device_id,
                    name=f"BT-1500 Sensacore Analyzer ({device_id})",
                    manufacturer="Sensacore",
                    model="BT-1500",
                    equipment_type=EquipmentType.CHEMISTRY_ANALYZER,
                    communication_protocol=CommunicationProtocol.SERIAL,
                    serial_port=port,
                    baud_rate=baudrate
                )
                
                # Store in database
                with get_session() as session:
                    session.add(equipment)
                    session.commit()
                
                logger.info(f"Added BT-1500 device {device_id} on {port}")
                return True
            else:
                logger.error(f"Failed to add BT-1500 device {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding BT-1500 device {device_id}: {str(e)}")
            return False
    
    async def remove_bt1500_device(self, device_id: str):
        """Remove a BT-1500 device"""
        try:
            # Remove from BT-1500 manager
            await bt1500_manager.remove_device(device_id)
            
            # Remove from database
            with get_session() as session:
                equipment = session.query(Equipment).filter_by(equipment_id=device_id).first()
                if equipment:
                    session.delete(equipment)
                    session.commit()
            
            logger.info(f"Removed BT-1500 device {device_id}")
            
        except Exception as e:
            logger.error(f"Error removing BT-1500 device {device_id}: {str(e)}")
    
    def get_bt1500_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all BT-1500 devices"""
        return bt1500_manager.get_all_devices()
    
    def get_bt1500_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific BT-1500 device"""
        return bt1500_manager.get_device_status(device_id)
    
    async def _load_equipment(self):
        """Load equipment from database and create device connections"""
        try:
            # TODO: Load equipment from database
            # For now, we'll use a placeholder
            logger.info("Loading equipment from database...")
            
            # This would typically query the database for active equipment
            # equipment_list = session.query(Equipment).filter_by(is_active=True).all()
            # for equipment in equipment_list:
            #     await self.add_device(equipment)
            
        except Exception as e:
            logger.error(f"Failed to load equipment: {str(e)}")
    
    async def _connect_device(self, device_id: str):
        """Connect to a specific device"""
        try:
            if device_id not in self.devices:
                return
            
            device = self.devices[device_id]
            self.connection_status[device_id] = ConnectionStatus.CONNECTING
            
            logger.info(f"Connecting to device: {device_id}")
            
            # Attempt connection
            success = await device.connect()
            
            if success:
                self.connection_status[device_id] = ConnectionStatus.CONNECTED
                logger.info(f"Successfully connected to device: {device_id}")
            else:
                self.connection_status[device_id] = ConnectionStatus.ERROR
                logger.error(f"Failed to connect to device: {device_id}")
            
        except Exception as e:
            self.connection_status[device_id] = ConnectionStatus.ERROR
            logger.error(f"Error connecting to device {device_id}: {str(e)}")
    
    async def _disconnect_device(self, device_id: str):
        """Disconnect from a specific device"""
        try:
            if device_id not in self.devices:
                return
            
            device = self.devices[device_id]
            
            logger.info(f"Disconnecting from device: {device_id}")
            
            await device.disconnect()
            self.connection_status[device_id] = ConnectionStatus.DISCONNECTED
            
            logger.info(f"Disconnected from device: {device_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from device {device_id}: {str(e)}")
    
    async def _disconnect_all_devices(self):
        """Disconnect from all devices"""
        disconnect_tasks = []
        
        for device_id in list(self.devices.keys()):
            task = asyncio.create_task(self._disconnect_device(device_id))
            disconnect_tasks.append(task)
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    async def _monitor_devices(self):
        """Monitor device connections and health"""
        logger.info("Starting device monitoring...")
        
        while self.running:
            try:
                # Check each device's health
                for device_id, device in self.devices.items():
                    await self._check_device_health(device_id, device)
                
                # Wait for next scan cycle
                await asyncio.sleep(settings.device_scan_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device monitoring: {str(e)}")
                await asyncio.sleep(10)  # Wait before retrying
        
        logger.info("Device monitoring stopped")
    
    async def _check_device_health(self, device_id: str, device: AnalyzerInterface):
        """Check health of a specific device"""
        try:
            current_status = self.connection_status[device_id]
            
            # If device should be connected but isn't, try to reconnect
            if (device.equipment.is_active and 
                current_status == ConnectionStatus.DISCONNECTED):
                await self._connect_device(device_id)
            
            # If connected, check if it's still responding
            elif current_status == ConnectionStatus.CONNECTED:
                is_responsive = await device.ping()
                if not is_responsive:
                    logger.warning(f"Device {device_id} not responding")
                    self.connection_status[device_id] = ConnectionStatus.ERROR
            
        except Exception as e:
            logger.error(f"Error checking device health {device_id}: {str(e)}")
    
    async def _on_message_received(self, device_id: str, message: str, message_type: str = 'HL7'):
        """Handle incoming message from device"""
        try:
            logger.info(f"Received message from device {device_id}: {message[:100]}...")
            
            # Get the appropriate handler
            handler = self.message_handlers.get(message_type, self._handle_raw_message)
            
            # Process the message
            result = await handler(device_id, message)
            
            # Log the result
            if result.get('success'):
                logger.info(f"Successfully processed message from {device_id}")
            else:
                logger.error(f"Failed to process message from {device_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling message from device {device_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_hl7_message(self, device_id: str, message: str) -> Dict[str, Any]:
        """Handle HL7 message from device"""
        try:
            # Process the HL7 message
            response = hl7_handler.process_message(message)
            
            # TODO: Store results in database
            # TODO: Send acknowledgment back to device
            
            return {
                'success': True,
                'message_type': 'HL7',
                'device_id': device_id,
                'response': response
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message_type': 'HL7',
                'device_id': device_id
            }
    
    async def _handle_astm_message(self, device_id: str, message: str) -> Dict[str, Any]:
        """Handle ASTM message from device"""
        try:
            # TODO: Implement ASTM message processing
            logger.info(f"ASTM message processing not implemented yet for device {device_id}")
            
            return {
                'success': True,
                'message_type': 'ASTM',
                'device_id': device_id,
                'note': 'ASTM processing not implemented'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message_type': 'ASTM',
                'device_id': device_id
            }
    
    async def _handle_raw_message(self, device_id: str, message: str) -> Dict[str, Any]:
        """Handle raw/unknown message from device"""
        try:
            logger.info(f"Received raw message from device {device_id}")
            
            # TODO: Implement raw message processing based on device type
            
            return {
                'success': True,
                'message_type': 'RAW',
                'device_id': device_id,
                'message_length': len(message)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message_type': 'RAW',
                'device_id': device_id
            }


# Global device manager instance
device_manager = DeviceManager() 