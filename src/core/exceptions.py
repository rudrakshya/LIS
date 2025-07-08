"""
Custom exceptions for the Laboratory Information System (LIS)
"""


class LISException(Exception):
    """Base exception for all LIS-related errors"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseException(LISException):
    """Database-related exceptions"""
    pass


class CommunicationException(LISException):
    """Communication protocol exceptions"""
    pass


class HL7Exception(CommunicationException):
    """HL7 message processing exceptions"""
    pass


class ASTMException(CommunicationException):
    """ASTM protocol exceptions"""
    pass


class DeviceException(LISException):
    """Medical device communication exceptions"""
    pass


class DeviceConnectionException(DeviceException):
    """Device connection failures"""
    pass


class DeviceTimeoutException(DeviceException):
    """Device communication timeout"""
    pass


class AuthenticationException(LISException):
    """Authentication and authorization exceptions"""
    pass


class ValidationException(LISException):
    """Data validation exceptions"""
    pass


class ConfigurationException(LISException):
    """Configuration-related exceptions"""
    pass


class TestOrderException(LISException):
    """Test order processing exceptions"""
    pass


class ResultProcessingException(LISException):
    """Test result processing exceptions"""
    pass 