"""Top-level package for AWS data lake deployment utilities."""

from .config import (
    DataLakeConfig,
    AwsCredentials,
    FirehoseConfig,
    IamRoleConfig,
    VpcEndpointConfig,
    LakeFormationConfig,
    LakeFormationPermission,
)
from .deployer import DataLakeDeployer
from .sessions import SessionFactory
from .exceptions import (
    DataLakeError,
    ValidationError,
    DeploymentError,
    ResourceNotFoundError,
)

__all__ = [
    "DataLakeConfig",
    "AwsCredentials",
    "FirehoseConfig",
    "IamRoleConfig",
    "VpcEndpointConfig",
    "LakeFormationConfig",
    "LakeFormationPermission",
    "DataLakeDeployer",
    "SessionFactory",
    "DataLakeError",
    "ValidationError",
    "DeploymentError",
    "ResourceNotFoundError",
]
