"""Input validation utilities for security."""
import re
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, validator, ValidationError

from chakravyuh.core.logging import logger


class QueryParamsValidator(BaseModel):
    """Validator for API query parameters."""
    
    service: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    @validator('service')
    def validate_service(cls, v):
        """Validate service name - must be alphanumeric with hyphens/underscores."""
        if v is None:
            return v
        
        # Only allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Service name must contain only alphanumeric characters, hyphens, and underscores")
        
        # Limit length
        if len(v) > 50:
            raise ValueError("Service name must be 50 characters or less")
        
        return v.lower()
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        """Validate date format - must be ISO format (YYYY-MM-DD)."""
        if v is None:
            return v
        
        # Try to parse ISO date format
        try:
            # Accept YYYY-MM-DD format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                datetime.strptime(v, '%Y-%m-%d')
                return v
            else:
                raise ValueError("Date must be in ISO format (YYYY-MM-DD)")
        except ValueError as e:
            if "Date must be" in str(e):
                raise
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date if both are provided."""
        if v and values.get('start_date'):
            try:
                start = datetime.strptime(values['start_date'], '%Y-%m-%d')
                end = datetime.strptime(v, '%Y-%m-%d')
                if end < start:
                    raise ValueError("end_date must be after or equal to start_date")
            except (ValueError, KeyError):
                pass  # Let other validators handle format errors
        return v


def validate_query_params(
    service: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Validate query parameters and return sanitized values.
    
    Args:
        service: Service name to validate
        start_date: Start date to validate
        end_date: End date to validate
        
    Returns:
        Dictionary with validated parameters
        
    Raises:
        ValueError: If validation fails
    """
    try:
        validator = QueryParamsValidator(
            service=service,
            start_date=start_date,
            end_date=end_date,
        )
        return validator.dict(exclude_none=True)
    except ValidationError as e:
        error_messages = [err['msg'] for err in e.errors()]
        raise ValueError(f"Validation error: {', '.join(error_messages)}")


def validate_service_name(service: str) -> str:
    """
    Validate and sanitize service name.
    
    Args:
        service: Service name to validate
        
    Returns:
        Sanitized service name
        
    Raises:
        ValueError: If service name is invalid
    """
    if not service:
        raise ValueError("Service name cannot be empty")
    
    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', service):
        raise ValueError("Service name contains invalid characters")
    
    # Limit length
    if len(service) > 50:
        raise ValueError("Service name exceeds maximum length")
    
    return service.lower()


def validate_date_string(date_str: str, field_name: str = "date") -> str:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated date string
        
    Raises:
        ValueError: If date format is invalid
    """
    if not date_str:
        raise ValueError(f"{field_name} cannot be empty")
    
    # Must match YYYY-MM-DD format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(f"{field_name} must be in ISO format (YYYY-MM-DD)")
    
    # Try to parse to ensure it's a valid date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"{field_name} is not a valid date")
    
    return date_str
