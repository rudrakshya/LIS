"""
Sample model for the Laboratory Information System
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from ..core.database import Base


class SampleStatus(PyEnum):
    """Sample status enumeration"""
    COLLECTED = "collected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    ACCESSIONED = "accessioned"
    IN_TESTING = "in_testing"
    TESTED = "tested"
    REJECTED = "rejected"
    DISPOSED = "disposed"


class SampleType(PyEnum):
    """Sample type enumeration"""
    BLOOD = "blood"
    SERUM = "serum"
    PLASMA = "plasma"
    URINE = "urine"
    STOOL = "stool"
    SPUTUM = "sputum"
    CSF = "csf"  # Cerebrospinal fluid
    TISSUE = "tissue"
    SWAB = "swab"
    OTHER = "other"


class Sample(Base):
    """Sample/Specimen model"""
    
    __tablename__ = "samples"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Sample identifiers
    sample_id = Column(String(50), unique=True, index=True, nullable=False)
    barcode = Column(String(100), unique=True, index=True)
    
    # References
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    test_order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False, index=True)
    
    # Sample information
    sample_type = Column(Enum(SampleType), nullable=False)
    container_type = Column(String(50))  # Tube type, container
    volume_collected = Column(Float)  # in mL
    volume_remaining = Column(Float)  # in mL
    
    # Collection information
    collected_at = Column(DateTime)
    collected_by = Column(String(100))
    collection_site = Column(String(100))  # Arm, finger, etc.
    collection_method = Column(String(100))  # Venipuncture, finger stick, etc.
    
    # Transport and receipt
    received_at = Column(DateTime)
    received_by = Column(String(100))
    temperature_at_receipt = Column(Float)  # in Celsius
    
    # Processing information
    status = Column(Enum(SampleStatus), default=SampleStatus.COLLECTED, nullable=False)
    accessioned_at = Column(DateTime)
    accessioned_by = Column(String(100))
    
    # Quality information
    is_hemolyzed = Column(Boolean, default=False)
    is_lipemic = Column(Boolean, default=False)
    is_icteric = Column(Boolean, default=False)
    quality_notes = Column(Text)
    
    # Storage information
    storage_location = Column(String(100))  # Freezer, refrigerator, room temp
    storage_temperature = Column(Float)  # in Celsius
    expiration_date = Column(DateTime)
    
    # Rejection information
    is_rejected = Column(Boolean, default=False)
    rejection_reason = Column(Text)
    rejected_at = Column(DateTime)
    rejected_by = Column(String(100))
    
    # Chain of custody
    custody_log = Column(Text)  # JSON string of custody transfers
    
    # Processing tracking
    aliquots_created = Column(Integer, default=0)
    tests_remaining = Column(Integer, default=0)
    
    # External references
    external_sample_id = Column(String(100))
    lab_equipment_id = Column(String(100))
    
    # Notes and comments
    collection_notes = Column(Text)
    processing_notes = Column(Text)
    comments = Column(Text)
    
    # Disposal information
    disposed_at = Column(DateTime)
    disposed_by = Column(String(100))
    disposal_method = Column(String(100))
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    # Relationships
    patient = relationship("Patient", back_populates="samples")
    test_order = relationship("TestOrder", back_populates="samples")
    results = relationship("TestResult", back_populates="sample")
    
    def __repr__(self):
        return f"<Sample(id={self.id}, sample_id='{self.sample_id}', type='{self.sample_type.value}', status='{self.status.value}')>"
    
    @property
    def age_in_hours(self) -> Optional[float]:
        """Calculate sample age in hours since collection"""
        if not self.collected_at:
            return None
        return (datetime.utcnow() - self.collected_at).total_seconds() / 3600
    
    @property
    def age_in_days(self) -> Optional[int]:
        """Calculate sample age in days since collection"""
        if not self.collected_at:
            return None
        return (datetime.utcnow() - self.collected_at).days
    
    @property
    def is_expired(self) -> bool:
        """Check if sample has expired"""
        if not self.expiration_date:
            return False
        return datetime.utcnow() > self.expiration_date
    
    @property
    def has_quality_issues(self) -> bool:
        """Check if sample has quality issues"""
        return self.is_hemolyzed or self.is_lipemic or self.is_icteric
    
    @property
    def volume_percentage_remaining(self) -> Optional[float]:
        """Calculate percentage of volume remaining"""
        if not self.volume_collected or self.volume_collected == 0:
            return None
        if not self.volume_remaining:
            return 0.0
        return (self.volume_remaining / self.volume_collected) * 100
    
    def can_be_tested(self) -> bool:
        """Check if sample can be tested"""
        return (self.status in [SampleStatus.RECEIVED, SampleStatus.ACCESSIONED] and
                not self.is_rejected and
                not self.is_expired and
                self.volume_remaining and self.volume_remaining > 0)
    
    def to_dict(self) -> dict:
        """Convert sample to dictionary"""
        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "barcode": self.barcode,
            "patient_id": self.patient_id,
            "test_order_id": self.test_order_id,
            "sample_type": self.sample_type.value,
            "container_type": self.container_type,
            "volume_collected": self.volume_collected,
            "volume_remaining": self.volume_remaining,
            "status": self.status.value,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "age_in_hours": self.age_in_hours,
            "age_in_days": self.age_in_days,
            "is_expired": self.is_expired,
            "has_quality_issues": self.has_quality_issues,
            "is_rejected": self.is_rejected,
            "volume_percentage_remaining": self.volume_percentage_remaining,
            "can_be_tested": self.can_be_tested(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 