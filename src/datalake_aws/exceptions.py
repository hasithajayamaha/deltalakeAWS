"""Custom exceptions and error handling utilities for datalake-aws."""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Any

from botocore.exceptions import ClientError

_LOGGER = logging.getLogger(__name__)

T = TypeVar('T')


class DataLakeError(Exception):
    """Base exception for data lake deployment errors."""
    pass


class ValidationError(DataLakeError):
    """Raised when configuration validation fails."""
    pass


class DeploymentError(DataLakeError):
    """Raised when resource deployment fails."""
    pass


class ResourceNotFoundError(DataLakeError):
    """Raised when a required AWS resource is not found."""
    pass


def retry_on_throttle(max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    """
    Decorator to retry AWS API calls on throttling errors.
    
    Uses exponential backoff to handle rate limiting gracefully.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles with each retry)
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_on_throttle(max_retries=5, base_delay=2.0)
        def create_bucket(client, bucket_name):
            client.create_bucket(Bucket=bucket_name)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ClientError as exc:
                    error_code = exc.response.get('Error', {}).get('Code', '')
                    
                    # Retry on throttling errors
                    if error_code in [
                        'ThrottlingException',
                        'TooManyRequestsException',
                        'RequestLimitExceeded',
                        'Throttling',
                        'ProvisionedThroughputExceededException',
                    ]:
                        last_exception = exc
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            _LOGGER.warning(
                                "Throttled by AWS (attempt %d/%d), retrying in %.1fs: %s",
                                attempt + 1,
                                max_retries,
                                delay,
                                error_code
                            )
                            time.sleep(delay)
                            continue
                    
                    # Don't retry on other errors
                    raise
            
            # All retries exhausted
            if last_exception:
                raise DeploymentError(
                    f"Failed after {max_retries} retries due to throttling"
                ) from last_exception
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def handle_client_error(operation: str) -> Callable:
    """
    Decorator to handle and log AWS ClientError exceptions.
    
    Args:
        operation: Description of the operation being performed
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except ClientError as exc:
                error_code = exc.response.get('Error', {}).get('Code', 'Unknown')
                error_message = exc.response.get('Error', {}).get('Message', 'No message')
                
                _LOGGER.error(
                    "AWS API error during %s: [%s] %s",
                    operation,
                    error_code,
                    error_message
                )
                
                raise DeploymentError(
                    f"Failed to {operation}: [{error_code}] {error_message}"
                ) from exc
        
        return wrapper
    return decorator


__all__ = [
    'DataLakeError',
    'ValidationError',
    'DeploymentError',
    'ResourceNotFoundError',
    'retry_on_throttle',
    'handle_client_error',
]
