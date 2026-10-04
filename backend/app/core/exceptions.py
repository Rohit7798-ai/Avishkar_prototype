"""
Core application and domain exceptions.
Decouples business logic from HTTP transport protocols.
"""


class DomainException(Exception):
    """Base exception for all domain-specific errors."""
    pass


class EntityNotFoundException(DomainException):
    """Raised when a requested domain entity does not exist."""
    def __init__(self, entity_name: str, entity_id: int):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with id {entity_id} not found")


class BusinessRuleViolationException(DomainException):
    """Raised when an operation violates a business-level domain constraint."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
