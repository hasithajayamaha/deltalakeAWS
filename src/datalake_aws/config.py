"""Configuration models for describing an AWS data lake deployment."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[assignment]


@dataclass
class AwsCredentials:
    """Static AWS credentials used to build a boto3 session."""

    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None

    def as_dict(self) -> Dict[str, str]:
        """Return a mapping compatible with boto3 Session kwargs."""
        data = {
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
        }
        if self.session_token:
            data["aws_session_token"] = self.session_token
        return data


@dataclass
class DataLakeConfig:
    """Configuration values controlling how the data lake should be provisioned."""

    region: str
    bucket_name: str
    glue_database: str
    raw_prefix: str = "raw/"
    processed_prefix: str = "processed/"
    analytics_prefix: str = "analytics/"
    kms_key_id: Optional[str] = None
    crawler_name: Optional[str] = None
    crawler_role_arn: Optional[str] = None
    crawler_schedule: Optional[str] = None
    crawler_s3_target_path: Optional[str] = None
    athena_workgroup: Optional[str] = "datalake-workgroup"
    tags: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "DataLakeConfig":
        """Build a DataLakeConfig from a mapping (dict, INI section, etc.)."""

        return cls(
            region=data["region"],
            bucket_name=data["bucket_name"],
            glue_database=data["glue_database"],
            raw_prefix=data.get("raw_prefix", "raw/"),
            processed_prefix=data.get("processed_prefix", "processed/"),
            analytics_prefix=data.get("analytics_prefix", "analytics/"),
            kms_key_id=data.get("kms_key_id"),
            crawler_name=data.get("crawler_name"),
            crawler_role_arn=data.get("crawler_role_arn"),
            crawler_schedule=data.get("crawler_schedule"),
            crawler_s3_target_path=data.get("crawler_s3_target_path"),
            athena_workgroup=data.get("athena_workgroup", "datalake-workgroup"),
            tags=dict(data.get("tags", {})),
        )

    @classmethod
    def from_toml(cls, path: Path) -> "DataLakeConfig":
        """Load configuration from a TOML file."""
        payload = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        config_section = payload.get("datalake")
        if not config_section:
            raise ValueError("Expected [datalake] table in configuration file")
        tags = config_section.get("tags", {})
        if tags and not isinstance(tags, dict):
            raise TypeError("datalake.tags must be a table of key/value pairs")
        config_section = {**config_section, "tags": tags}
        return cls.from_mapping(config_section)


__all__ = ["AwsCredentials", "DataLakeConfig"]
