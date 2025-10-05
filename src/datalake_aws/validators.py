"""Validation utilities for configuration and inputs."""
from __future__ import annotations

import re
from typing import Optional

from .exceptions import ValidationError


def validate_bucket_name(bucket_name: str) -> None:
    """
    Validate S3 bucket name according to AWS naming rules.
    
    Rules:
    - Between 3 and 63 characters long
    - Only lowercase letters, numbers, dots, and hyphens
    - Must start and end with a letter or number
    - Cannot contain consecutive dots, or dots adjacent to hyphens
    - Cannot be formatted as an IP address
    
    Args:
        bucket_name: The bucket name to validate
        
    Raises:
        ValidationError: If bucket name is invalid
    """
    if not bucket_name:
        raise ValidationError("Bucket name cannot be empty")
    
    if not (3 <= len(bucket_name) <= 63):
        raise ValidationError(
            f"Bucket name must be between 3 and 63 characters, got {len(bucket_name)}"
        )
    
    if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket_name):
        raise ValidationError(
            f"Bucket name '{bucket_name}' contains invalid characters or format. "
            "Must start and end with lowercase letter or number, and contain only "
            "lowercase letters, numbers, dots, and hyphens."
        )
    
    # Check for invalid patterns
    if '..' in bucket_name:
        raise ValidationError(f"Bucket name '{bucket_name}' cannot contain consecutive dots")
    
    if '.-' in bucket_name or '-.' in bucket_name:
        raise ValidationError(
            f"Bucket name '{bucket_name}' cannot have dots adjacent to hyphens"
        )
    
    # Check if it looks like an IP address
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', bucket_name):
        raise ValidationError(f"Bucket name '{bucket_name}' cannot be formatted as an IP address")


def validate_region(region: str) -> None:
    """
    Validate AWS region format.
    
    Args:
        region: AWS region identifier
        
    Raises:
        ValidationError: If region format is invalid
    """
    if not region:
        raise ValidationError("Region cannot be empty")
    
    # Basic region format validation (e.g., us-east-1, eu-west-2)
    if not re.match(r'^[a-z]{2}-[a-z]+-\d{1}$', region):
        raise ValidationError(
            f"Invalid region format: '{region}'. "
            "Expected format like 'us-east-1' or 'eu-west-2'"
        )


def validate_database_name(database_name: str) -> None:
    """
    Validate Glue database name.
    
    Args:
        database_name: Glue database name
        
    Raises:
        ValidationError: If database name is invalid
    """
    if not database_name:
        raise ValidationError("Database name cannot be empty")
    
    if not (1 <= len(database_name) <= 255):
        raise ValidationError(
            f"Database name must be between 1 and 255 characters, got {len(database_name)}"
        )
    
    # Glue database names can contain alphanumeric and underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', database_name):
        raise ValidationError(
            f"Database name '{database_name}' can only contain letters, numbers, and underscores"
        )


def validate_prefix(prefix: str, prefix_name: str = "prefix") -> str:
    """
    Validate and normalize S3 prefix.
    
    Ensures prefix ends with a forward slash.
    
    Args:
        prefix: S3 prefix to validate
        prefix_name: Name of the prefix for error messages
        
    Returns:
        Normalized prefix ending with /
        
    Raises:
        ValidationError: If prefix is invalid
    """
    if not prefix:
        raise ValidationError(f"{prefix_name} cannot be empty")
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9/_-]+$', prefix):
        raise ValidationError(
            f"{prefix_name} '{prefix}' contains invalid characters. "
            "Only letters, numbers, forward slashes, hyphens, and underscores are allowed."
        )
    
    # Ensure it ends with /
    if not prefix.endswith('/'):
        prefix = prefix + '/'
    
    return prefix


def validate_table_format(table_format: str) -> None:
    """
    Validate table format.
    
    Args:
        table_format: Table format (iceberg or delta)
        
    Raises:
        ValidationError: If table format is invalid
    """
    valid_formats = {'iceberg', 'delta'}
    if table_format.lower() not in valid_formats:
        raise ValidationError(
            f"Invalid table_format: '{table_format}'. "
            f"Must be one of: {', '.join(valid_formats)}"
        )


def validate_arn(arn: str, resource_type: Optional[str] = None) -> None:
    """
    Validate AWS ARN format.
    
    Args:
        arn: AWS ARN to validate
        resource_type: Optional specific resource type to check (e.g., 'role', 'key')
        
    Raises:
        ValidationError: If ARN format is invalid
    """
    if not arn:
        raise ValidationError("ARN cannot be empty")
    
    # Basic ARN format: arn:partition:service:region:account-id:resource
    arn_pattern = r'^arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:\d{12}:.+$'
    if not re.match(arn_pattern, arn):
        raise ValidationError(
            f"Invalid ARN format: '{arn}'. "
            "Expected format: arn:partition:service:region:account-id:resource"
        )
    
    if resource_type:
        # Check if ARN contains the expected resource type
        if f':{resource_type}/' not in arn and not arn.endswith(f':{resource_type}'):
            raise ValidationError(
                f"ARN '{arn}' does not appear to be a {resource_type} ARN"
            )


def validate_tags(tags: dict) -> None:
    """
    Validate AWS resource tags.
    
    Args:
        tags: Dictionary of tag key-value pairs
        
    Raises:
        ValidationError: If tags are invalid
    """
    if not isinstance(tags, dict):
        raise ValidationError("Tags must be a dictionary")
    
    for key, value in tags.items():
        # Tag key validation
        if not key:
            raise ValidationError("Tag key cannot be empty")
        
        if len(key) > 128:
            raise ValidationError(f"Tag key '{key}' exceeds 128 characters")
        
        # Tag value validation
        if not isinstance(value, str):
            raise ValidationError(f"Tag value for key '{key}' must be a string")
        
        if len(value) > 256:
            raise ValidationError(
                f"Tag value for key '{key}' exceeds 256 characters"
            )


__all__ = [
    'validate_bucket_name',
    'validate_region',
    'validate_database_name',
    'validate_prefix',
    'validate_table_format',
    'validate_arn',
    'validate_tags',
]
