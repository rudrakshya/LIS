"""
Test Result model for the Laboratory Information System
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from ..core.database import Base


class ResultStatus(PyEnum):
    """Test result status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    ERROR = "error"


class ResultFlag(PyEnum):
    """Result abnormal flag enumeration"""
    NORMAL = "N"  # Normal
    LOW = "L"     # Below low normal
    HIGH = "H"    # Above high normal
    CRITICAL_LOW = "LL"   # Below low panic values
    CRITICAL_HIGH = "HH"  # Above high panic values
    ABNORMAL = "A"        # Abnormal
    VERY_ABNORMAL = "AA"  # Very abnormal


class TestResult(Base):
    """Test result model"""
    
    __tablename__ = "test_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Result identifiers
    result_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # References
    test_order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    
    # Test information
    test_code = Column(String(20), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    test_method = Column(String(100))
    
    # Result values
    result_value = Column(Text, nullable=False)
    numeric_result = Column(Float)  # For numeric results
    text_result = Column(Text)      # For text results
    
    # Reference ranges and units
    reference_range = Column(String(100))
    units = Column(String(20))
    normal_range_low = Column(Float)
    normal_range_high = Column(Float)
    panic_range_low = Column(Float)
    panic_range_high = Column(Float)
    
    # Result status and flags
    status = Column(Enum(ResultStatus), default=ResultStatus.PENDING, nullable=False)
    abnormal_flag = Column(Enum(ResultFlag), default=ResultFlag.NORMAL)
    
    # Quality control
    is_critical = Column(Boolean, default=False)
    requires_verification = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100))
    verified_at = Column(DateTime)
    
    # Equipment and processing
    analyzer_id = Column(String(100))
    analyzer_name = Column(String(200))
    run_number = Column(String(50))
    well_position = Column(String(20))
    
    # Timing information
    tested_at = Column(DateTime)
    resulted_at = Column(DateTime, default=datetime.utcnow)
    reported_at = Column(DateTime)
    
    # Personnel
    performed_by = Column(String(100))
    reviewed_by = Column(String(100))
    authorized_by = Column(String(100))
    
    # Quality metrics
    coefficient_of_variation = Column(Float)  # CV%
    standard_deviation = Column(Float)
    measurement_uncertainty = Column(Float)
    
    # Dilution and processing
    dilution_factor = Column(Float, default=1.0)
    rerun_count = Column(Integer, default=0)
    is_repeat = Column(Boolean, default=False)
    original_result_id = Column(String(50))  # Reference to original if repeat
    
    # Interpretation
    interpretation = Column(Text)
    clinical_significance = Column(Text)
    recommendations = Column(Text)
    
    # Delta checking (comparison with previous results)
    previous_result = Column(Float)
    delta_value = Column(Float)
    delta_percentage = Column(Float)
    delta_flag = Column(Boolean, default=False)
    
    # External references
    external_result_id = Column(String(100))
    lis_message_id = Column(String(100))
    
    # Notes and comments
    comments = Column(Text)
    technical_notes = Column(Text)
    quality_notes = Column(Text)
    
    # Correction information
    corrected_at = Column(DateTime)
    corrected_by = Column(String(100))
    correction_reason = Column(Text)
    original_value = Column(Text)  # Store original value if corrected
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    # Relationships
    test_order = relationship("TestOrder", back_populates="results")
    sample = relationship("Sample", back_populates="results")
    
    def __repr__(self):
        return f"<TestResult(id={self.id}, result_id='{self.result_id}', test_code='{self.test_code}', value='{self.result_value}', status='{self.status.value}')>"
    
    @property
    def is_numeric(self) -> bool:
        """Check if result is numeric"""
        return self.numeric_result is not None
    
    @property
    def is_abnormal(self) -> bool:
        """Check if result is abnormal"""
        return self.abnormal_flag != ResultFlag.NORMAL
    
    @property
    def is_critical(self) -> bool:
        """Check if result is in critical range"""
        return self.abnormal_flag in [ResultFlag.CRITICAL_LOW, ResultFlag.CRITICAL_HIGH]
    
    @property
    def is_final(self) -> bool:
        """Check if result is final"""
        return self.status == ResultStatus.FINAL
    
    @property
    def is_corrected(self) -> bool:
        """Check if result has been corrected"""
        return self.status == ResultStatus.CORRECTED
    
    @property
    def turnaround_time_hours(self) -> Optional[float]:
        """Calculate turnaround time in hours"""
        if not self.test_order or not self.test_order.ordered_at or not self.resulted_at:
            return None
        return (self.resulted_at - self.test_order.ordered_at).total_seconds() / 3600
    
    def is_within_normal_range(self) -> Optional[bool]:
        """Check if numeric result is within normal range"""
        if not self.is_numeric or not self.normal_range_low or not self.normal_range_high:
            return None
        return self.normal_range_low <= self.numeric_result <= self.normal_range_high
    
    def is_within_panic_range(self) -> Optional[bool]:
        """Check if numeric result is within panic range"""
        if not self.is_numeric:
            return None
        
        if self.panic_range_low and self.numeric_result < self.panic_range_low:
            return True
        if self.panic_range_high and self.numeric_result > self.panic_range_high:
            return True
        return False
    
    def calculate_delta(self, previous_value: float) -> dict:
        """Calculate delta values compared to previous result"""
        if not self.is_numeric:
            return {"delta_value": None, "delta_percentage": None}
        
        delta_value = self.numeric_result - previous_value
        delta_percentage = ((self.numeric_result - previous_value) / previous_value * 100) if previous_value != 0 else None
        
        return {
            "delta_value": delta_value,
            "delta_percentage": delta_percentage
        }
    
    def to_dict(self) -> dict:
        """Convert result to dictionary"""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "test_order_id": self.test_order_id,
            "sample_id": self.sample_id,
            "test_code": self.test_code,
            "test_name": self.test_name,
            "result_value": self.result_value,
            "numeric_result": self.numeric_result,
            "units": self.units,
            "reference_range": self.reference_range,
            "status": self.status.value,
            "abnormal_flag": self.abnormal_flag.value if self.abnormal_flag else None,
            "is_numeric": self.is_numeric,
            "is_abnormal": self.is_abnormal,
            "is_critical": self.is_critical,
            "is_final": self.is_final,
            "is_verified": self.is_verified,
            "analyzer_name": self.analyzer_name,
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
            "resulted_at": self.resulted_at.isoformat() if self.resulted_at else None,
            "turnaround_time_hours": self.turnaround_time_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 