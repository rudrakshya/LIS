"""
REST API for Laboratory Information System
Provides endpoints for external system integration
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

from ..core.config import settings
from ..core.database import get_database_session
from ..core.exceptions import LISException, ValidationException
from ..models import (
    Patient, TestOrder, Sample, TestResult, Equipment,
    OrderStatus, SampleType, EquipmentType, CommunicationProtocol
)
from .schemas import (
    PatientCreate, PatientResponse, PatientUpdate,
    TestOrderCreate, TestOrderResponse, TestOrderUpdate,
    SampleCreate, SampleResponse, SampleUpdate,
    TestResultCreate, TestResultResponse, TestResultUpdate,
    EquipmentCreate, EquipmentResponse, EquipmentUpdate
)
from ..devices.device_manager import device_manager
from ..communication.hl7_handler import hl7_handler
from ..communication.serial_handler import bt1500_manager

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Laboratory Information System API for medical equipment integration",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=settings.api_cors_methods,
    allow_headers=settings.api_cors_headers,
)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment
    }


# Production monitoring endpoints
@app.get("/system/status", tags=["System"])
async def system_status():
    """Get comprehensive system status"""
    try:
        # Check database connection
        db_status = "healthy"
        try:
            from ..core.database import db_manager
            if not db_manager.test_connection():
                db_status = "unhealthy"
        except Exception:
            db_status = "error"
        
        # Check device manager status
        device_status = await device_manager.get_health_status()
        
        return {
            "status": "healthy" if db_status == "healthy" else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "device_manager": device_status,
                "api": "healthy"
            },
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime": datetime.utcnow().isoformat()  # Would track actual uptime in production
        }
    except Exception as e:
        logger.error(f"System status check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@app.get("/system/metrics", tags=["System"])
async def system_metrics(db: Session = Depends(get_database_session)):
    """Get system metrics for monitoring"""
    try:
        # Count records in database
        patient_count = db.query(Patient).count()
        order_count = db.query(TestOrder).count()
        result_count = db.query(TestResult).count()
        equipment_count = db.query(Equipment).count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_orders = db.query(TestOrder).filter(TestOrder.created_at >= yesterday).count()
        recent_results = db.query(TestResult).filter(TestResult.result_date >= yesterday).count()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "patients": patient_count,
                "orders": order_count,
                "results": result_count,
                "equipment": equipment_count
            },
            "activity_24h": {
                "new_orders": recent_orders,
                "new_results": recent_results
            },
            "system": {
                "version": settings.app_version,
                "environment": settings.environment
            }
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}"
        )


@app.get("/system/logs", tags=["System"])
async def get_recent_logs(
    level: str = Query("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    lines: int = Query(100, ge=1, le=1000)
):
    """Get recent log entries"""
    try:
        # This would read from log files in production
        # For now, return a placeholder
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "lines": lines,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "System running normally"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Log retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


# Patient Management Endpoints
@app.post("/patients/", response_model=PatientResponse, tags=["Patients"])
async def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_database_session)
):
    """Create a new patient"""
    try:
        # Check if patient already exists
        existing = db.query(Patient).filter_by(patient_id=patient.patient_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with ID {patient.patient_id} already exists"
            )
        
        # Create new patient
        db_patient = Patient(**patient.dict())
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        
        logger.info(f"Created patient: {db_patient.patient_id}")
        return PatientResponse.from_orm(db_patient)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create patient: {str(e)}"
        )


@app.get("/patients/", response_model=List[PatientResponse], tags=["Patients"])
async def get_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session)
):
    """Get all patients with pagination"""
    try:
        patients = db.query(Patient).offset(skip).limit(limit).all()
        return [PatientResponse.from_orm(patient) for patient in patients]
    except Exception as e:
        logger.error(f"Error fetching patients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patients: {str(e)}"
        )


@app.get("/patients/{patient_id}", response_model=PatientResponse, tags=["Patients"])
async def get_patient(
    patient_id: str,
    db: Session = Depends(get_database_session)
):
    """Get patient by ID"""
    try:
        patient = db.query(Patient).filter_by(patient_id=patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        return PatientResponse.from_orm(patient)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient: {str(e)}"
        )


@app.put("/patients/{patient_id}", response_model=PatientResponse, tags=["Patients"])
async def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    db: Session = Depends(get_database_session)
):
    """Update patient information"""
    try:
        patient = db.query(Patient).filter_by(patient_id=patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # Update patient fields
        for field, value in patient_update.dict(exclude_unset=True).items():
            setattr(patient, field, value)
        
        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        
        logger.info(f"Updated patient: {patient_id}")
        return PatientResponse.from_orm(patient)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patient: {str(e)}"
        )


# Test Order Management Endpoints
@app.post("/orders/", response_model=TestOrderResponse, tags=["Orders"])
async def create_test_order(
    order: TestOrderCreate,
    db: Session = Depends(get_database_session)
):
    """Create a new test order"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter_by(patient_id=order.patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {order.patient_id} not found"
            )
        
        # Check if order number already exists
        if order.order_number:
            existing = db.query(TestOrder).filter_by(order_number=order.order_number).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Order {order.order_number} already exists"
                )
        
        # Create test order
        db_order = TestOrder(**order.dict())
        if not db_order.order_number:
            # Generate order number if not provided
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            db_order.order_number = f"ORD_{timestamp}"
        
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        logger.info(f"Created test order: {db_order.order_number}")
        
        # Send order to appropriate device if available
        await _send_order_to_device(db_order)
        
        return TestOrderResponse.from_orm(db_order)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test order: {str(e)}"
        )


@app.get("/orders/", response_model=List[TestOrderResponse], tags=["Orders"])
async def get_test_orders(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session)
):
    """Get test orders with optional filtering"""
    try:
        query = db.query(TestOrder)
        
        if patient_id:
            query = query.filter(TestOrder.patient_id == patient_id)
        
        if status:
            try:
                order_status = OrderStatus(status)
                query = query.filter(TestOrder.status == order_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
        
        orders = query.offset(skip).limit(limit).all()
        return [TestOrderResponse.from_orm(order) for order in orders]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test orders: {str(e)}"
        )


@app.get("/orders/{order_number}", response_model=TestOrderResponse, tags=["Orders"])
async def get_test_order(
    order_number: str,
    db: Session = Depends(get_database_session)
):
    """Get test order by order number"""
    try:
        order = db.query(TestOrder).filter_by(order_number=order_number).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test order {order_number} not found"
            )
        return TestOrderResponse.from_orm(order)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test order {order_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test order: {str(e)}"
        )


# Equipment Management Endpoints
@app.get("/equipment/", response_model=List[EquipmentResponse], tags=["Equipment"])
async def get_equipment(
    equipment_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_database_session)
):
    """Get all equipment with optional filtering"""
    try:
        query = db.query(Equipment)
        
        if equipment_type:
            try:
                eq_type = EquipmentType(equipment_type)
                query = query.filter(Equipment.equipment_type == eq_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid equipment type: {equipment_type}"
                )
        
        if is_active is not None:
            query = query.filter(Equipment.is_active == is_active)
        
        equipment = query.all()
        return [EquipmentResponse.from_orm(eq) for eq in equipment]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching equipment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equipment: {str(e)}"
        )


@app.get("/equipment/{equipment_id}", response_model=EquipmentResponse, tags=["Equipment"])
async def get_equipment_by_id(
    equipment_id: str,
    db: Session = Depends(get_database_session)
):
    """Get equipment by ID"""
    try:
        equipment = db.query(Equipment).filter_by(equipment_id=equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment {equipment_id} not found"
            )
        return EquipmentResponse.from_orm(equipment)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching equipment {equipment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equipment: {str(e)}"
        )


@app.get("/equipment/{equipment_id}/status", tags=["Equipment"])
async def get_equipment_status(equipment_id: str):
    """Get real-time equipment status"""
    try:
        status = await device_manager.get_device_status(equipment_id)
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment {equipment_id} not found or not connected"
            )
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equipment status {equipment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get equipment status: {str(e)}"
        )


# Result Management Endpoints
@app.get("/results/", response_model=List[TestResultResponse], tags=["Results"])
async def get_test_results(
    order_number: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    test_code: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session)
):
    """Get test results with optional filtering"""
    try:
        query = db.query(TestResult)
        
        if order_number:
            # Join with TestOrder to filter by order_number
            query = query.join(TestOrder).filter(TestOrder.order_number == order_number)
        
        if patient_id:
            # Join with TestOrder and Patient to filter by patient_id
            query = query.join(TestOrder).join(Patient).filter(Patient.patient_id == patient_id)
        
        if test_code:
            query = query.filter(TestResult.test_code == test_code)
        
        results = query.offset(skip).limit(limit).all()
        return [TestResultResponse.from_orm(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error fetching test results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test results: {str(e)}"
        )


@app.post("/results/", response_model=TestResultResponse, tags=["Results"])
async def create_test_result(
    result: TestResultCreate,
    db: Session = Depends(get_database_session)
):
    """Create a new test result"""
    try:
        # Verify test order exists
        test_order = db.query(TestOrder).filter_by(id=result.test_order_id).first()
        if not test_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test order {result.test_order_id} not found"
            )
        
        # Create test result
        db_result = TestResult(**result.dict())
        if not db_result.result_id:
            # Generate result ID if not provided
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            db_result.result_id = f"RES_{timestamp}"
        
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        
        logger.info(f"Created test result: {db_result.result_id}")
        return TestResultResponse.from_orm(db_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test result: {str(e)}"
        )


# Communication Endpoints
@app.post("/hl7/message", tags=["Communication"])
async def process_hl7_message(
    message: Dict[str, str]
):
    """Process incoming HL7 message"""
    try:
        raw_message = message.get("message", "")
        if not raw_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content is required"
            )
        
        response = hl7_handler.process_message(raw_message)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing HL7 message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process HL7 message: {str(e)}"
        )


@app.get("/devices/status", tags=["Devices"])
async def get_all_device_status():
    """Get status of all connected devices"""
    try:
        statuses = await device_manager.get_all_devices_status()
        return {"devices": statuses, "total_devices": len(statuses)}
    except Exception as e:
        logger.error(f"Error getting device statuses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device statuses: {str(e)}"
        )


@app.post("/devices/bt1500/")
async def add_bt1500_device(
    device_id: str = Form(..., description="Unique device identifier"),
    port: str = Form(..., description="Serial port (e.g., COM1, /dev/ttyUSB0)"),
    baudrate: int = Form(9600, description="Baud rate (default: 9600)")
):
    """Add a BT-1500 Sensacore analyzer device"""
    try:
        success = await device_manager.add_bt1500_device(device_id, port, baudrate)
        
        if success:
            return {
                "status": "success",
                "message": f"BT-1500 device {device_id} added successfully",
                "device_id": device_id,
                "port": port,
                "baudrate": baudrate
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to add BT-1500 device {device_id}")
            
    except Exception as e:
        logger.error(f"Error adding BT-1500 device: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/devices/bt1500/{device_id}")
async def remove_bt1500_device(device_id: str):
    """Remove a BT-1500 device"""
    try:
        await device_manager.remove_bt1500_device(device_id)
        
        return {
            "status": "success",
            "message": f"BT-1500 device {device_id} removed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error removing BT-1500 device: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/devices/bt1500/")
async def get_bt1500_devices():
    """Get status of all BT-1500 devices"""
    try:
        devices = device_manager.get_bt1500_devices()
        
        return {
            "status": "success",
            "devices": devices,
            "count": len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error getting BT-1500 devices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/devices/bt1500/{device_id}")
async def get_bt1500_device_status(device_id: str):
    """Get status of a specific BT-1500 device"""
    try:
        status = device_manager.get_bt1500_device_status(device_id)
        
        if status:
            return {
                "status": "success",
                "device_id": device_id,
                "device_status": status
            }
        else:
            raise HTTPException(status_code=404, detail=f"BT-1500 device {device_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BT-1500 device status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/devices/bt1500/{device_id}/command")
async def send_bt1500_command(
    device_id: str,
    command: str = Form(..., description="Command to send to BT-1500")
):
    """Send a command to a BT-1500 device"""
    try:
        # Get device handler
        devices = bt1500_manager.devices
        if device_id not in devices:
            raise HTTPException(status_code=404, detail=f"BT-1500 device {device_id} not found")
        
        handler = devices[device_id]
        success = await handler.send_command(command)
        
        if success:
            return {
                "status": "success",
                "message": f"Command sent to BT-1500 device {device_id}",
                "command": command
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to send command to BT-1500 device {device_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending command to BT-1500: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/devices/bt1500/{device_id}/buffer")
async def get_bt1500_buffer(device_id: str):
    """Get current buffer content from a BT-1500 device (for debugging)"""
    try:
        devices = bt1500_manager.devices
        if device_id not in devices:
            raise HTTPException(status_code=404, detail=f"BT-1500 device {device_id} not found")
        
        handler = devices[device_id]
        buffer_content = handler.get_buffer_content()
        
        return {
            "status": "success",
            "device_id": device_id,
            "buffer_content": buffer_content,
            "buffer_size": len(buffer_content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BT-1500 buffer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Exception handlers
@app.exception_handler(LISException)
async def lis_exception_handler(request, exc: LISException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "error_code": exc.error_code}
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request, exc: ValidationException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message, "error_code": exc.error_code}
    )


# Helper functions
async def _send_order_to_device(order: TestOrder):
    """Send test order to appropriate device"""
    try:
        # Find equipment that can perform this test
        # This is a simplified version - in practice, you'd have more sophisticated routing
        order_data = {
            "patient_id": order.patient.patient_id if order.patient else "UNKNOWN",
            "order_number": order.order_number,
            "test_code": order.test_code,
            "test_name": order.test_name
        }
        
        # For now, just log that we would send to a device
        logger.info(f"Would send order {order.order_number} to appropriate device")
        
    except Exception as e:
        logger.error(f"Error sending order to device: {str(e)}")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting LIS API server...")
    try:
        # Start device manager
        await device_manager.start()
        logger.info("LIS API server started successfully")
    except Exception as e:
        logger.error(f"Failed to start LIS API server: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down LIS API server...")
    try:
        # Stop device manager
        await device_manager.stop()
        logger.info("LIS API server shut down successfully")
    except Exception as e:
        logger.error(f"Error during LIS API server shutdown: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    ) 