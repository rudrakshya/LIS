"""
Patient model for the Laboratory Information System
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from typing import Optional

from ..core.database import Base


class Patient(Base):
    """Patient information model"""
    
    __tablename__ = "patients"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Patient identifiers
    patient_id = Column(String(50), unique=True, index=True, nullable=False)
    medical_record_number = Column(String(50), unique=True, index=True)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(10))  # M, F, O, U (Male, Female, Other, Unknown)
    
    # Contact information
    phone = Column(String(20))
    email = Column(String(100))
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    country = Column(String(100), default="USA")
    
    # Additional information
    race = Column(String(50))
    ethnicity = Column(String(50))
    language = Column(String(50), default="English")
    
    # Insurance information
    insurance_provider = Column(String(100))
    insurance_policy_number = Column(String(100))
    insurance_group_number = Column(String(100))
    
    # Emergency contact
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relationship = Column(String(50))
    
    # Status flags
    is_active = Column(Boolean, default=True)
    is_deceased = Column(Boolean, default=False)
    deceased_date = Column(Date)
    
    # Notes and comments
    notes = Column(Text)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    # Relationships
    test_orders = relationship("TestOrder", back_populates="patient")
    samples = relationship("Sample", back_populates="patient")
    
    def __repr__(self):
        return f"<Patient(id={self.id}, patient_id='{self.patient_id}', name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self) -> str:
        """Get patient's full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)
    
    @property
    def age(self) -> Optional[int]:
        """Calculate patient's age"""
        if not self.date_of_birth:
            return None
        
        today = date.today()
        age = today.year - self.date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        
        return age
    
    @property
    def full_address(self) -> str:
        """Get formatted full address"""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        
        return ", ".join(parts)
    
    def to_dict(self) -> dict:
        """Convert patient to dictionary"""
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "medical_record_number": self.medical_record_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "full_address": self.full_address,
            "race": self.race,
            "ethnicity": self.ethnicity,
            "language": self.language,
            "is_active": self.is_active,
            "is_deceased": self.is_deceased,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 