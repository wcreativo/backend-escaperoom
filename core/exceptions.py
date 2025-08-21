"""
Custom exceptions for the escape rooms project.
"""

class EscapeRoomException(Exception):
    """Base exception for escape room related errors."""
    pass


class ReservationException(EscapeRoomException):
    """Exception raised for reservation related errors."""
    pass


class TimeSlotUnavailableException(ReservationException):
    """Exception raised when trying to book an unavailable time slot."""
    pass


class ReservationExpiredException(ReservationException):
    """Exception raised when trying to operate on an expired reservation."""
    pass