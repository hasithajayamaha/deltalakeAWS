"""Configuration models for describing an AWS data lake deployment."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional, List

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
class FirehoseConfig:
    """Configuration parameters for an Amazon Kinesis Data Firehose stream."""

    stream_name: str
    role_name: str
    buffering_interval: int = 300
    buffering_size_mib: int = 5
    compression_format: str = "GZIP"
    prefix: Optional[str] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "FirehoseConfig":
        return cls(
            stream_name=str(data["stream_name"]),
            role_name=str(data["role_name"]),
            buffering_interval=int(data.get("buffering_interval", 300)),
            buffering_size_mib=int(data.get("buffering_size_mib", 5)),
            compression_format=str(data.get("compression_format", "GZIP")),
            prefix=str(data.get("prefix")) if data.get("prefix") is not None else None,
        )


@dataclass
class IamRoleConfig:
    """Definition of an IAM role and the policies it requires."""

    name: str
    assume_role_policy: Dict[str, object]
    managed_policy_arns: List[str] = field(default_factory=list)
    inline_policies: Dict[str, Dict[str, object]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "IamRoleConfig":
        assume_role_policy = data.get("assume_role_policy")
        if not isinstance(assume_role_policy, Mapping):
            raise TypeError("assume_role_policy must be a mapping")
        managed = data.get("managed_policy_arns", [])
        if isinstance(managed, list):
            managed_policy_arns = [str(item) for item in managed]
        elif managed is None:
            managed_policy_arns = []
        else:
            raise TypeError("managed_policy_arns must be a list of ARNs")
        inline = data.get("inline_policies", {})
        if inline and not isinstance(inline, Mapping):
            raise TypeError("inline_policies must be a mapping of policy name to document")
        inline_policies: Dict[str, Dict[str, object]] = {}
        for key, value in dict(inline).items():
            if not isinstance(value, Mapping):
                raise TypeError("inline policy documents must be mappings")
            inline_policies[str(key)] = dict(value)
        return cls(
            name=str(data["name"]),
            assume_role_policy=dict(assume_role_policy),
            managed_policy_arns=managed_policy_arns,
            inline_policies=inline_policies,
        )


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
    table_format: str = "iceberg"
    processing_platform: Optional[str] = None
    enable_transactional_tables: bool = True
    transactional_table_name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    firehose: Optional[FirehoseConfig] = None
    processing_role: Optional[IamRoleConfig] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "DataLakeConfig":
        firehose_cfg = data.get("firehose")
        firehose: Optional[FirehoseConfig] = None
        if isinstance(firehose_cfg, Mapping):
            firehose = FirehoseConfig.from_mapping(firehose_cfg)
        elif firehose_cfg is not None:
            raise TypeError("firehose configuration must be a mapping if provided")

        processing_role_cfg = data.get("processing_role")
        processing_role: Optional[IamRoleConfig] = None
        if isinstance(processing_role_cfg, Mapping):
            processing_role = IamRoleConfig.from_mapping(processing_role_cfg)
        elif processing_role_cfg is not None:
            raise TypeError("processing_role configuration must be a mapping if provided")

        tags = data.get("tags", {})
        if tags and not isinstance(tags, Mapping):
            raise TypeError("tags must be a mapping of key/value pairs")

        return cls(
            region=str(data["region"]),
            bucket_name=str(data["bucket_name"]),
            glue_database=str(data["glue_database"]),
            raw_prefix=str(data.get("raw_prefix", "raw/")),
            processed_prefix=str(data.get("processed_prefix", "processed/")),
            analytics_prefix=str(data.get("analytics_prefix", "analytics/")),
            kms_key_id=str(data.get("kms_key_id")) if data.get("kms_key_id") is not None else None,
            crawler_name=str(data.get("crawler_name")) if data.get("crawler_name") is not None else None,
            crawler_role_arn=str(data.get("crawler_role_arn")) if data.get("crawler_role_arn") is not None else None,
            crawler_schedule=str(data.get("crawler_schedule")) if data.get("crawler_schedule") is not None else None,
            crawler_s3_target_path=str(data.get("crawler_s3_target_path")) if data.get("crawler_s3_target_path") is not None else None,
            athena_workgroup=str(data.get("athena_workgroup", "datalake-workgroup")) if data.get("athena_workgroup", "datalake-workgroup") is not None else None,
            table_format=str(data.get("table_format", "iceberg")),
            processing_platform=str(data.get("processing_platform")) if data.get("processing_platform") is not None else None,
            enable_transactional_tables=bool(data.get("enable_transactional_tables", True)),
            transactional_table_name=str(data.get("transactional_table_name")) if data.get("transactional_table_name") is not None else None,
            tags=dict(tags),
            firehose=firehose,
            processing_role=processing_role,
        )

    @classmethod
    def from_toml(cls, path: Path) -> "DataLakeConfig":
        """Load configuration from a TOML file."""
        payload = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        config_section = payload.get("datalake")
        if not config_section:
            raise ValueError("Expected [datalake] table in configuration file")
        if not isinstance(config_section, Mapping):
            raise TypeError("[datalake] section must be a table")
        return cls.from_mapping(config_section)


__all__ = [
    "AwsCredentials",
    "DataLakeConfig",
    "FirehoseConfig",
    "IamRoleConfig",
]
