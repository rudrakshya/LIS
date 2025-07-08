"""
Test Order model for the Laboratory Information System
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from ..core.database import Base


class OrderStatus(PyEnum):
    """Test order status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"
    REJECTED = "rejected"


class OrderPriority(PyEnum):
    """Test order priority enumeration"""
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"
    ASAP = "asap"


class TestOrder(Base):
    """Test order model"""
    
    __tablename__ = "test_orders"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Order identifiers
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    accession_number = Column(String(50), unique=True, index=True)
    
    # Patient reference
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    
    # Order information
    test_code = Column(String(20), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    test_description = Column(Text)
    
    # Status and priority
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    priority = Column(Enum(OrderPriority), default=OrderPriority.ROUTINE, nullable=False)
    
    # Ordering information
    ordering_physician = Column(String(200))
    ordering_physician_id = Column(String(50))
    ordering_department = Column(String(100))
    ordering_facility = Column(String(200))
    
    # Clinical information
    clinical_notes = Column(Text)
    diagnosis_code = Column(String(20))  # ICD-10 code
    diagnosis_description = Column(Text)
    
    # Sample requirements
    sample_type = Column(String(50))  # Blood, Urine, Serum, etc.
    sample_volume = Column(String(20))
    collection_instructions = Column(Text)
    
    # Timing information
    ordered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    scheduled_collection_time = Column(DateTime)
    collection_deadline = Column(DateTime)
    report_deadline = Column(DateTime)
    
    # Processing information
    assigned_to = Column(String(100))  # Lab technician
    processed_by = Column(String(100))
    reviewed_by = Column(String(100))
    
    # Quality control
    is_critical = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    
    # Billing information
    billing_code = Column(String(20))  # CPT code
    insurance_authorization = Column(String(100))
    
    # External references
    external_order_id = Column(String(100))  # Reference to external system
    hl7_message_id = Column(String(100))  # HL7 message control ID
    
    # Notes and comments
    comments = Column(Text)
    internal_notes = Column(Text)
    
    # Status tracking
    cancelled_at = Column(DateTime)
    cancelled_by = Column(String(100))
    cancellation_reason = Column(Text)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    # Relationships
    patient = relationship("Patient", back_populates="test_orders")
    samples = relationship("Sample", back_populates="test_order")
    results = relationship("TestResult", back_populates="test_order")
    
    def __repr__(self):
        return f"<TestOrder(id={self.id}, order_number='{self.order_number}', test_code='{self.test_code}', status='{self.status.value}')>"
    
    @property
    def is_urgent(self) -> bool:
        """Check if order is urgent"""
        return self.priority in [OrderPriority.URGENT, OrderPriority.STAT, OrderPriority.ASAP]
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed"""
        return self.status == OrderStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """Check if order is cancelled"""
        return self.status == OrderStatus.CANCELLED
    
    @property
    def days_since_ordered(self) -> int:
        """Calculate days since order was placed"""
        return (datetime.utcnow() - self.ordered_at).days
    
    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.ON_HOLD]
    
    def can_be_processed(self) -> bool:
        """Check if order can be processed"""
        return self.status == OrderStatus.PENDING and not self.is_cancelled
    
    def to_dict(self) -> dict:
        """Convert order to dictionary"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "accession_number": self.accession_number,
            "patient_id": self.patient_id,
            "test_code": self.test_code,
            "test_name": self.test_name,
            "test_description": self.test_description,
            "status": self.status.value,
            "priority": self.priority.value,
            "ordering_physician": self.ordering_physician,
            "clinical_notes": self.clinical_notes,
            "sample_type": self.sample_type,
            "ordered_at": self.ordered_at.isoformat() if self.ordered_at else None,
            "is_urgent": self.is_urgent,
            "is_completed": self.is_completed,
            "is_cancelled": self.is_cancelled,
            "days_since_ordered": self.days_since_ordered,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 