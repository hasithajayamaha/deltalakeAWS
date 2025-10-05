"""Configuration models for describing an AWS data lake deployment."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional, List

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[assignment]

from .validators import (
    validate_bucket_name,
    validate_region,
    validate_database_name,
    validate_prefix,
    validate_table_format,
    validate_arn,
    validate_tags,
)


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
class VpcEndpointConfig:
    """Configuration for VPC endpoints to access AWS services privately."""

    vpc_id: str
    subnet_ids: List[str] = field(default_factory=list)
    security_group_ids: List[str] = field(default_factory=list)
    route_table_ids: List[str] = field(default_factory=list)
    enable_s3: bool = True
    enable_glue: bool = True
    enable_athena: bool = True
    enable_dns_support: bool = True
    enable_private_dns: bool = True

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "VpcEndpointConfig":
        subnet_ids = data.get("subnet_ids", [])
        if not isinstance(subnet_ids, list):
            raise TypeError("subnet_ids must be a list")
        
        security_group_ids = data.get("security_group_ids", [])
        if not isinstance(security_group_ids, list):
            raise TypeError("security_group_ids must be a list")
        
        route_table_ids = data.get("route_table_ids", [])
        if not isinstance(route_table_ids, list):
            raise TypeError("route_table_ids must be a list")
        
        return cls(
            vpc_id=str(data["vpc_id"]),
            subnet_ids=[str(sid) for sid in subnet_ids],
            security_group_ids=[str(sgid) for sgid in security_group_ids],
            route_table_ids=[str(rtid) for rtid in route_table_ids],
            enable_s3=bool(data.get("enable_s3", True)),
            enable_glue=bool(data.get("enable_glue", True)),
            enable_athena=bool(data.get("enable_athena", True)),
            enable_dns_support=bool(data.get("enable_dns_support", True)),
            enable_private_dns=bool(data.get("enable_private_dns", True)),
        )


@dataclass
class LakeFormationPermission:
    """A single Lake Formation permission grant."""

    principal: str
    resource_type: str  # DATABASE, TABLE, DATA_LOCATION
    database_name: Optional[str] = None
    table_name: Optional[str] = None
    table_wildcard: bool = False
    permissions: List[str] = field(default_factory=list)
    permissions_with_grant_option: List[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "LakeFormationPermission":
        permissions = data.get("permissions", [])
        if not isinstance(permissions, list):
            raise TypeError("permissions must be a list")
        
        permissions_with_grant = data.get("permissions_with_grant_option", [])
        if not isinstance(permissions_with_grant, list):
            raise TypeError("permissions_with_grant_option must be a list")
        
        return cls(
            principal=str(data["principal"]),
            resource_type=str(data["resource_type"]),
            database_name=str(data.get("database_name")) if data.get("database_name") is not None else None,
            table_name=str(data.get("table_name")) if data.get("table_name") is not None else None,
            table_wildcard=bool(data.get("table_wildcard", False)),
            permissions=[str(p) for p in permissions],
            permissions_with_grant_option=[str(p) for p in permissions_with_grant],
        )


@dataclass
class LakeFormationConfig:
    """Configuration for AWS Lake Formation integration."""

    enable_lake_formation: bool = False
    data_lake_admins: List[str] = field(default_factory=list)
    register_s3_location: bool = True
    use_lake_formation_credentials: bool = True
    permissions: List[LakeFormationPermission] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "LakeFormationConfig":
        admins = data.get("data_lake_admins", [])
        if not isinstance(admins, list):
            raise TypeError("data_lake_admins must be a list")
        
        permissions_data = data.get("permissions", [])
        if not isinstance(permissions_data, list):
            raise TypeError("permissions must be a list")
        
        permissions = []
        for perm_data in permissions_data:
            if isinstance(perm_data, Mapping):
                permissions.append(LakeFormationPermission.from_mapping(perm_data))
        
        return cls(
            enable_lake_formation=bool(data.get("enable_lake_formation", False)),
            data_lake_admins=[str(admin) for admin in admins],
            register_s3_location=bool(data.get("register_s3_location", True)),
            use_lake_formation_credentials=bool(data.get("use_lake_formation_credentials", True)),
            permissions=permissions,
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
    vpc_endpoints: Optional[VpcEndpointConfig] = None
    lake_formation: Optional[LakeFormationConfig] = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate required fields
        validate_region(self.region)
        validate_bucket_name(self.bucket_name)
        validate_database_name(self.glue_database)
        
        # Validate and normalize prefixes
        self.raw_prefix = validate_prefix(self.raw_prefix, "raw_prefix")
        self.processed_prefix = validate_prefix(self.processed_prefix, "processed_prefix")
        self.analytics_prefix = validate_prefix(self.analytics_prefix, "analytics_prefix")
        
        # Validate table format
        validate_table_format(self.table_format)
        
        # Validate optional ARNs
        if self.kms_key_id:
            validate_arn(self.kms_key_id, "key")
        
        if self.crawler_role_arn:
            validate_arn(self.crawler_role_arn, "role")
        
        # Validate tags
        if self.tags:
            validate_tags(self.tags)

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

        vpc_endpoints_cfg = data.get("vpc_endpoints")
        vpc_endpoints: Optional[VpcEndpointConfig] = None
        if isinstance(vpc_endpoints_cfg, Mapping):
            vpc_endpoints = VpcEndpointConfig.from_mapping(vpc_endpoints_cfg)
        elif vpc_endpoints_cfg is not None:
            raise TypeError("vpc_endpoints configuration must be a mapping if provided")

        lake_formation_cfg = data.get("lake_formation")
        lake_formation: Optional[LakeFormationConfig] = None
        if isinstance(lake_formation_cfg, Mapping):
            lake_formation = LakeFormationConfig.from_mapping(lake_formation_cfg)
        elif lake_formation_cfg is not None:
            raise TypeError("lake_formation configuration must be a mapping if provided")

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
            vpc_endpoints=vpc_endpoints,
            lake_formation=lake_formation,
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
    "VpcEndpointConfig",
    "LakeFormationConfig",
    "LakeFormationPermission",
]
