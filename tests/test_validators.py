"""Tests for validation utilities."""
import pytest

from datalake_aws.validators import (
    validate_bucket_name,
    validate_region,
    validate_database_name,
    validate_prefix,
    validate_table_format,
    validate_arn,
    validate_tags,
)
from datalake_aws.exceptions import ValidationError


class TestBucketNameValidation:
    """Tests for S3 bucket name validation."""

    def test_valid_bucket_names(self):
        """Test that valid bucket names pass validation."""
        valid_names = [
            "my-bucket",
            "my.bucket",
            "my-bucket-123",
            "abc",
            "a" * 63,  # Max length
        ]
        for name in valid_names:
            validate_bucket_name(name)  # Should not raise

    def test_invalid_bucket_name_too_short(self):
        """Test that bucket names shorter than 3 characters are rejected."""
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            validate_bucket_name("ab")

    def test_invalid_bucket_name_too_long(self):
        """Test that bucket names longer than 63 characters are rejected."""
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            validate_bucket_name("a" * 64)

    def test_invalid_bucket_name_uppercase(self):
        """Test that bucket names with uppercase letters are rejected."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_bucket_name("MyBucket")

    def test_invalid_bucket_name_special_chars(self):
        """Test that bucket names with special characters are rejected."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_bucket_name("my_bucket!")

    def test_invalid_bucket_name_consecutive_dots(self):
        """Test that bucket names with consecutive dots are rejected."""
        with pytest.raises(ValidationError, match="consecutive dots"):
            validate_bucket_name("my..bucket")

    def test_invalid_bucket_name_dot_hyphen(self):
        """Test that bucket names with dots adjacent to hyphens are rejected."""
        with pytest.raises(ValidationError, match="dots adjacent to hyphens"):
            validate_bucket_name("my.-bucket")
        with pytest.raises(ValidationError, match="dots adjacent to hyphens"):
            validate_bucket_name("my-.bucket")

    def test_invalid_bucket_name_ip_address(self):
        """Test that bucket names formatted as IP addresses are rejected."""
        with pytest.raises(ValidationError, match="IP address"):
            validate_bucket_name("192.168.1.1")

    def test_empty_bucket_name(self):
        """Test that empty bucket names are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_bucket_name("")


class TestRegionValidation:
    """Tests for AWS region validation."""

    def test_valid_regions(self):
        """Test that valid region formats pass validation."""
        valid_regions = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-south-1",
            "ca-central-1",
        ]
        for region in valid_regions:
            validate_region(region)  # Should not raise

    def test_invalid_region_format(self):
        """Test that invalid region formats are rejected."""
        with pytest.raises(ValidationError, match="Invalid region format"):
            validate_region("invalid-region")

    def test_empty_region(self):
        """Test that empty regions are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_region("")


class TestDatabaseNameValidation:
    """Tests for Glue database name validation."""

    def test_valid_database_names(self):
        """Test that valid database names pass validation."""
        valid_names = [
            "my_database",
            "MyDatabase123",
            "database_123",
            "a",
            "a" * 255,  # Max length
        ]
        for name in valid_names:
            validate_database_name(name)  # Should not raise

    def test_invalid_database_name_special_chars(self):
        """Test that database names with special characters are rejected."""
        with pytest.raises(ValidationError, match="letters, numbers, and underscores"):
            validate_database_name("my-database")

    def test_invalid_database_name_too_long(self):
        """Test that database names longer than 255 characters are rejected."""
        with pytest.raises(ValidationError, match="between 1 and 255 characters"):
            validate_database_name("a" * 256)

    def test_empty_database_name(self):
        """Test that empty database names are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_database_name("")


class TestPrefixValidation:
    """Tests for S3 prefix validation."""

    def test_valid_prefixes(self):
        """Test that valid prefixes pass validation."""
        assert validate_prefix("raw/") == "raw/"
        assert validate_prefix("data/processed/") == "data/processed/"
        assert validate_prefix("my-prefix/") == "my-prefix/"

    def test_prefix_normalization(self):
        """Test that prefixes without trailing slash are normalized."""
        assert validate_prefix("raw") == "raw/"
        assert validate_prefix("data/processed") == "data/processed/"

    def test_invalid_prefix_special_chars(self):
        """Test that prefixes with invalid characters are rejected."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_prefix("my prefix!")

    def test_empty_prefix(self):
        """Test that empty prefixes are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_prefix("")


class TestTableFormatValidation:
    """Tests for table format validation."""

    def test_valid_table_formats(self):
        """Test that valid table formats pass validation."""
        validate_table_format("iceberg")
        validate_table_format("delta")
        validate_table_format("ICEBERG")  # Case insensitive
        validate_table_format("DELTA")

    def test_invalid_table_format(self):
        """Test that invalid table formats are rejected."""
        with pytest.raises(ValidationError, match="Invalid table_format"):
            validate_table_format("parquet")


class TestArnValidation:
    """Tests for AWS ARN validation."""

    def test_valid_arns(self):
        """Test that valid ARNs pass validation."""
        valid_arns = [
            "arn:aws:iam::123456789012:role/MyRole",
            "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "arn:aws:s3:::my-bucket",
        ]
        for arn in valid_arns:
            validate_arn(arn)  # Should not raise

    def test_valid_arn_with_resource_type(self):
        """Test ARN validation with specific resource type."""
        validate_arn("arn:aws:iam::123456789012:role/MyRole", "role")
        validate_arn("arn:aws:kms:us-east-1:123456789012:key/abc", "key")

    def test_invalid_arn_format(self):
        """Test that invalid ARN formats are rejected."""
        with pytest.raises(ValidationError, match="Invalid ARN format"):
            validate_arn("not-an-arn")

    def test_invalid_arn_resource_type(self):
        """Test that ARNs with wrong resource type are rejected."""
        with pytest.raises(ValidationError, match="does not appear to be a key ARN"):
            validate_arn("arn:aws:iam::123456789012:role/MyRole", "key")

    def test_empty_arn(self):
        """Test that empty ARNs are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_arn("")


class TestTagsValidation:
    """Tests for AWS tags validation."""

    def test_valid_tags(self):
        """Test that valid tags pass validation."""
        valid_tags = {
            "Environment": "dev",
            "Owner": "data-team",
            "Project": "data-lake",
        }
        validate_tags(valid_tags)  # Should not raise

    def test_invalid_tags_not_dict(self):
        """Test that non-dictionary tags are rejected."""
        with pytest.raises(ValidationError, match="must be a dictionary"):
            validate_tags(["tag1", "tag2"])  # type: ignore

    def test_invalid_tag_key_too_long(self):
        """Test that tag keys longer than 128 characters are rejected."""
        with pytest.raises(ValidationError, match="exceeds 128 characters"):
            validate_tags({"a" * 129: "value"})

    def test_invalid_tag_value_too_long(self):
        """Test that tag values longer than 256 characters are rejected."""
        with pytest.raises(ValidationError, match="exceeds 256 characters"):
            validate_tags({"key": "a" * 257})

    def test_invalid_tag_value_not_string(self):
        """Test that non-string tag values are rejected."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_tags({"key": 123})  # type: ignore

    def test_empty_tag_key(self):
        """Test that empty tag keys are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_tags({"": "value"})
