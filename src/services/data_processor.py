"""
Data Processor Service - Automatic processing of laboratory data
Handles incoming HL7/ASTM messages and automatically processes them into the database.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.database import db_manager
from ..communication.hl7_handler import HL7Handler
from ..communication.astm_handler import ASTMHandler
from ..models.sample import Sample
from ..models.test_result import TestResult
from ..models.test_order import TestOrder
from ..models.patient import Patient
from ..models.equipment import Equipment

logger = logging.getLogger(__name__)


class DataProcessor:
    """Automatic data processor for laboratory information"""
    
    def __init__(self):
        self.running = False
        self.message_queue = asyncio.Queue()
        self.hl7_handler = HL7Handler()
        self.astm_handler = ASTMHandler()
        self.processed_count = 0
        self.error_count = 0
        self.last_processed = None
        
        logger.info("DataProcessor initialized")
    
    async def start(self):
        """Start the data processor service"""
        self.running = True
        
        # Start the message processing loop
        asyncio.create_task(self._process_messages())
        
        # Start periodic maintenance tasks
        asyncio.create_task(self._maintenance_loop())
        
        logger.info("DataProcessor service started")
    
    async def stop(self):
        """Stop the data processor service"""
        self.running = False
        logger.info("DataProcessor service stopped")
    
    async def queue_message(self, message_data: Dict[str, Any]):
        """Queue a message for processing"""
        await self.message_queue.put(message_data)
        logger.debug(f"Message queued for processing: {message_data.get('type', 'unknown')}")
    
    async def _process_messages(self):
        """Main message processing loop"""
        logger.info("Starting message processing loop")
        
        while self.running:
            try:
                # Wait for messages with timeout
                message_data = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_single_message(message_data)
                
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in message processing loop: {str(e)}")
                self.error_count += 1
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_single_message(self, message_data: Dict[str, Any]):
        """Process a single message"""
        try:
            message_type = message_data.get('type', '').upper()
            message_content = message_data.get('content', '')
            equipment_id = message_data.get('equipment_id')
            timestamp = message_data.get('timestamp', datetime.now().isoformat())
            
            logger.info(f"Processing {message_type} message from equipment {equipment_id}")
            
            if message_type == 'HL7':
                await self._process_hl7_message(message_content, equipment_id, timestamp)
            elif message_type == 'ASTM':
                await self._process_astm_message(message_content, equipment_id, timestamp)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return
            
            self.processed_count += 1
            self.last_processed = datetime.now()
            logger.info(f"Successfully processed message #{self.processed_count}")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self.error_count += 1
            
            # Store failed message for later analysis
            await self._store_failed_message(message_data, str(e))
    
    async def _process_hl7_message(self, content: str, equipment_id: str, timestamp: str):
        """Process HL7 message and store results"""
        try:
            # Parse HL7 message
            parsed_data = self.hl7_handler.parse_message(content)
            
            if not parsed_data:
                raise ValueError("Failed to parse HL7 message")
            
            # Extract patient information
            patient_data = parsed_data.get('patient', {})
            if patient_data:
                patient = await self._ensure_patient_exists(patient_data)
            else:
                patient = None
            
            # Extract sample information
            sample_data = parsed_data.get('sample', {})
            if sample_data:
                sample = await self._ensure_sample_exists(sample_data, patient)
            else:
                sample = None
            
            # Process test results
            results = parsed_data.get('results', [])
            for result_data in results:
                await self._store_test_result(result_data, sample, equipment_id, timestamp)
            
            logger.info(f"HL7 message processed: {len(results)} results stored")
            
        except Exception as e:
            logger.error(f"Error processing HL7 message: {str(e)}")
            raise
    
    async def _process_astm_message(self, content: str, equipment_id: str, timestamp: str):
        """Process ASTM message and store results"""
        try:
            # Parse ASTM message
            parsed_data = self.astm_handler.parse_message(content)
            
            if not parsed_data:
                raise ValueError("Failed to parse ASTM message")
            
            # Extract patient information
            patient_data = parsed_data.get('patient', {})
            if patient_data:
                patient = await self._ensure_patient_exists(patient_data)
            else:
                patient = None
            
            # Extract sample information
            sample_data = parsed_data.get('sample', {})
            if sample_data:
                sample = await self._ensure_sample_exists(sample_data, patient)
            else:
                sample = None
            
            # Process test results
            results = parsed_data.get('results', [])
            for result_data in results:
                await self._store_test_result(result_data, sample, equipment_id, timestamp)
            
            logger.info(f"ASTM message processed: {len(results)} results stored")
            
        except Exception as e:
            logger.error(f"Error processing ASTM message: {str(e)}")
            raise
    
    async def _ensure_patient_exists(self, patient_data: Dict[str, Any]) -> Optional[Patient]:
        """Ensure patient exists in database, create if not found"""
        try:
            patient_id = patient_data.get('patient_id')
            if not patient_id:
                logger.warning("No patient ID provided")
                return None
            
            # Try to find existing patient
            with db_manager.get_session() as session:
                existing = session.query(Patient).filter_by(patient_id=patient_id).first()
                
                if existing:
                    # Update patient data if needed
                    if patient_data.get('first_name'):
                        existing.first_name = patient_data['first_name']
                    if patient_data.get('last_name'):
                        existing.last_name = patient_data['last_name']
                    if patient_data.get('date_of_birth'):
                        existing.date_of_birth = patient_data['date_of_birth']
                    if patient_data.get('gender'):
                        existing.gender = patient_data['gender']
                    
                    session.commit()
                    return existing
                
                # Create new patient
                patient = Patient(
                    patient_id=patient_id,
                    first_name=patient_data.get('first_name', ''),
                    last_name=patient_data.get('last_name', ''),
                    date_of_birth=patient_data.get('date_of_birth'),
                    gender=patient_data.get('gender', 'U'),
                    medical_record_number=patient_data.get('mrn'),
                    phone=patient_data.get('phone'),
                    email=patient_data.get('email'),
                    address=patient_data.get('address')
                )
                
                session.add(patient)
                session.commit()
                session.refresh(patient)
                
                logger.info(f"Created new patient: {patient_id}")
                return patient
                
        except Exception as e:
            logger.error(f"Error ensuring patient exists: {str(e)}")
            return None
    
    async def _ensure_sample_exists(self, sample_data: Dict[str, Any], patient: Optional[Patient]) -> Optional[Sample]:
        """Ensure sample exists in database, create if not found"""
        try:
            sample_id = sample_data.get('sample_id')
            if not sample_id:
                sample_id = str(uuid4())
            
            # Try to find existing sample
            with db_manager.get_session() as session:
                existing = session.query(Sample).filter_by(sample_id=sample_id).first()
                
                if existing:
                    return existing
                
                # Create new sample
                sample = Sample(
                    sample_id=sample_id,
                    patient_id=patient.id if patient else None,
                    sample_type=sample_data.get('sample_type', 'Unknown'),
                    collection_date=sample_data.get('collection_date', datetime.now()),
                    received_date=sample_data.get('received_date', datetime.now()),
                    status='received',
                    priority=sample_data.get('priority', 'routine'),
                    comments=sample_data.get('comments')
                )
                
                session.add(sample)
                session.commit()
                session.refresh(sample)
                
                logger.info(f"Created new sample: {sample_id}")
                return sample
                
        except Exception as e:
            logger.error(f"Error ensuring sample exists: {str(e)}")
            return None
    
    async def _store_test_result(self, result_data: Dict[str, Any], sample: Optional[Sample], 
                               equipment_id: str, timestamp: str):
        """Store test result in database"""
        try:
            with db_manager.get_session() as session:
                # Create test result
                result = TestResult(
                    sample_id=sample.id if sample else None,
                    test_code=result_data.get('test_code', ''),
                    test_name=result_data.get('test_name', ''),
                    result_value=result_data.get('result_value', ''),
                    units=result_data.get('units', ''),
                    reference_range=result_data.get('reference_range', ''),
                    status=result_data.get('status', 'final'),
                    abnormal_flag=result_data.get('abnormal_flag', ''),
                    result_date=datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else datetime.now(),
                    equipment_id=equipment_id,
                    operator_id=result_data.get('operator_id', 'auto'),
                    comments=result_data.get('comments', ''),
                    raw_data=json.dumps(result_data)
                )
                
                session.add(result)
                session.commit()
                
                logger.debug(f"Stored test result: {result_data.get('test_code')} = {result_data.get('result_value')}")
                
        except Exception as e:
            logger.error(f"Error storing test result: {str(e)}")
            raise
    
    async def _store_failed_message(self, message_data: Dict[str, Any], error: str):
        """Store failed message for later analysis"""
        try:
            with db_manager.get_session() as session:
                # Store in a failed_messages table (would need to create this table)
                # For now, just log the failure
                logger.error(f"Failed message stored for analysis: {json.dumps(message_data, default=str)}")
                logger.error(f"Error: {error}")
                
        except Exception as e:
            logger.error(f"Error storing failed message: {str(e)}")
    
    async def _maintenance_loop(self):
        """Periodic maintenance tasks"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Log statistics
                logger.info(f"DataProcessor stats - Processed: {self.processed_count}, Errors: {self.error_count}")
                
                # Cleanup old temporary data, etc.
                await self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {str(e)}")
    
    async def _cleanup_old_data(self):
        """Clean up old temporary data"""
        try:
            # Clean up old temporary records older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            with db_manager.get_session() as session:
                # Add cleanup logic here as needed
                pass
                
        except Exception as e:
            logger.error(f"Error in data cleanup: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'last_processed': self.last_processed.isoformat() if self.last_processed else None,
            'queue_size': self.message_queue.qsize(),
            'running': self.running
        } 