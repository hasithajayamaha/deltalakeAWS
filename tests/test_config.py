"""Tests for configuration models."""
import tempfile
from pathlib import Path

import pytest

from datalake_aws.config import DataLakeConfig
from datalake_aws.exceptions import ValidationError


class TestDataLakeConfig:
    """Tests for DataLakeConfig class."""

    def test_valid_config_creation(self):
        """Test creating a valid configuration."""
        config = DataLakeConfig(
            region="us-east-1",
            bucket_name="my-data-lake",
            glue_database="analytics_db",
        )
        assert config.region == "us-east-1"
        assert config.bucket_name == "my-data-lake"
        assert config.glue_database == "analytics_db"
        assert config.raw_prefix == "raw/"
        assert config.dry_run is False

    def test_prefix_normalization(self):
        """Test that prefixes are normalized with trailing slashes."""
        config = DataLakeConfig(
            region="us-east-1",
            bucket_name="my-data-lake",
            glue_database="analytics_db",
            raw_prefix="raw",
            processed_prefix="processed",
            analytics_prefix="analytics",
        )
        assert config.raw_prefix == "raw/"
        assert config.processed_prefix == "processed/"
        assert config.analytics_prefix == "analytics/"

    def test_invalid_bucket_name(self):
        """Test that invalid bucket names raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="Invalid_Bucket_Name",
                glue_database="analytics_db",
            )

    def test_invalid_region(self):
        """Test that invalid regions raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="invalid-region",
                bucket_name="my-data-lake",
                glue_database="analytics_db",
            )

    def test_invalid_database_name(self):
        """Test that invalid database names raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="my-data-lake",
                glue_database="invalid-database!",
            )

    def test_invalid_table_format(self):
        """Test that invalid table formats raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="my-data-lake",
                glue_database="analytics_db",
                table_format="parquet",
            )

    def test_invalid_kms_key_arn(self):
        """Test that invalid KMS key ARNs raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="my-data-lake",
                glue_database="analytics_db",
                kms_key_id="not-an-arn",
            )

    def test_invalid_crawler_role_arn(self):
        """Test that invalid crawler role ARNs raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="my-data-lake",
                glue_database="analytics_db",
                crawler_role_arn="not-an-arn",
            )

    def test_invalid_tags(self):
        """Test that invalid tags raise ValidationError."""
        with pytest.raises(ValidationError):
            DataLakeConfig(
                region="us-east-1",
                bucket_name="my-data-lake",
                glue_database="analytics_db",
                tags={"": "value"},  # Empty key
            )

    def test_from_toml_valid(self):
        """Test loading configuration from a valid TOML file."""
        toml_content = """
[datalake]
region = "us-east-1"
bucket_name = "my-data-lake"
glue_database = "analytics_db"
raw_prefix = "raw/"
processed_prefix = "processed/"
analytics_prefix = "analytics/"
table_format = "iceberg"

[datalake.tags]
Environment = "dev"
Owner = "data-team"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = DataLakeConfig.from_toml(temp_path)
            assert config.region == "us-east-1"
            assert config.bucket_name == "my-data-lake"
            assert config.glue_database == "analytics_db"
            assert config.tags == {"Environment": "dev", "Owner": "data-team"}
        finally:
            temp_path.unlink()

    def test_from_toml_missing_section(self):
        """Test that missing [datalake] section raises ValueError."""
        toml_content = """
[other_section]
key = "value"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Expected \\[datalake\\] table"):
                DataLakeConfig.from_toml(temp_path)
        finally:
            temp_path.unlink()

    def test_from_toml_invalid_bucket_name(self):
        """Test that invalid bucket name in TOML raises ValidationError."""
        toml_content = """
[datalake]
region = "us-east-1"
bucket_name = "Invalid_Bucket"
glue_database = "analytics_db"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                DataLakeConfig.from_toml(temp_path)
        finally:
            temp_path.unlink()

    def test_dry_run_mode(self):
        """Test that dry_run mode can be enabled."""
        config = DataLakeConfig(
            region="us-east-1",
            bucket_name="my-data-lake",
            glue_database="analytics_db",
            dry_run=True,
        )
        assert config.dry_run is True

    def test_config_with_all_optional_fields(self):
        """Test configuration with all optional fields set."""
        config = DataLakeConfig(
            region="us-east-1",
            bucket_name="my-data-lake",
            glue_database="analytics_db",
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            crawler_name="my-crawler",
            crawler_role_arn="arn:aws:iam::123456789012:role/GlueCrawlerRole",
            crawler_schedule="cron(0 6 * * ? *)",
            athena_workgroup="my-workgroup",
            table_format="delta",
            enable_transactional_tables=True,
            transactional_table_name="transactions",
            tags={"Environment": "prod", "Owner": "data-eng"},
        )
        assert config.kms_key_id is not None
        assert config.crawler_name == "my-crawler"
        assert config.table_format == "delta"
        assert config.enable_transactional_tables is True
        assert len(config.tags) == 2
