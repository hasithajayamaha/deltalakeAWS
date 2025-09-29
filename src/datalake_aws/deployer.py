"""High-level API for provisioning an AWS-based data lake using boto3."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from botocore.exceptions import ClientError

from .config import DataLakeConfig
from .sessions import SessionFactory

_LOGGER = logging.getLogger(__name__)


class DataLakeDeployer:
    """Coordinates provisioning of the core AWS primitives backing a data lake."""

    def __init__(self, session_factory: SessionFactory, logger: Optional[logging.Logger] = None) -> None:
        self._sessions = session_factory
        self._logger = logger or _LOGGER

    def deploy(self, config: DataLakeConfig) -> Dict[str, str]:
        """Ensure data lake resources exist and are configured."""
        summary: Dict[str, str] = {}
        summary["s3_bucket"] = self._ensure_bucket(config)
        summary["glue_database"] = self._ensure_glue_database(config)
        if config.crawler_name:
            summary["glue_crawler"] = self._ensure_glue_crawler(config)
        if config.athena_workgroup:
            summary["athena_workgroup"] = self._ensure_athena_workgroup(config)
        return summary

    # --- S3 bucket -----------------------------------------------------------------

    def _ensure_bucket(self, config: DataLakeConfig) -> str:
        s3_client = self._sessions.client("s3")
        bucket = config.bucket_name

        created = False
        if not self._bucket_exists(s3_client, bucket):
            create_args = {"Bucket": bucket}
            if config.region != "us-east-1":
                create_args["CreateBucketConfiguration"] = {"LocationConstraint": config.region}
            self._logger.info("Creating S3 bucket %s", bucket)
            s3_client.create_bucket(**create_args)
            created = True
        else:
            self._logger.debug("S3 bucket %s already exists", bucket)

        self._logger.debug("Configuring S3 bucket %s for block public access", bucket)
        s3_client.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        self._logger.debug("Enabling versioning on bucket %s", bucket)
        s3_client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})

        if config.kms_key_id:
            self._logger.debug("Enabling SSE-KMS on bucket %s", bucket)
            s3_client.put_bucket_encryption(
                Bucket=bucket,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "aws:kms",
                                "KMSMasterKeyID": config.kms_key_id,
                            }
                        }
                    ]
                },
            )

        if config.tags:
            self._logger.debug("Applying bucket tags to %s", bucket)
            tag_set = [{"Key": key, "Value": value} for key, value in sorted(config.tags.items())]
            s3_client.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tag_set})

        self._ensure_prefixes(s3_client, config)
        return "created" if created else "updated"

    def _ensure_prefixes(self, s3_client, config: DataLakeConfig) -> None:
        prefixes = [
            config.raw_prefix,
            config.processed_prefix,
            config.analytics_prefix,
        ]
        for prefix in prefixes:
            key = prefix.rstrip("/") + "/"
            self._logger.debug("Ensuring key %s exists in bucket %s", key, config.bucket_name)
            s3_client.put_object(Bucket=config.bucket_name, Key=key)

    def _bucket_exists(self, s3_client, bucket: str) -> bool:
        try:
            s3_client.head_bucket(Bucket=bucket)
            return True
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code in ("NoSuchBucket", "404"):
                return False
            if error_code == "301":  # wrong region
                return True
            raise

    # --- Glue ----------------------------------------------------------------------

    def _ensure_glue_database(self, config: DataLakeConfig) -> str:
        glue_client = self._sessions.client("glue")
        try:
            glue_client.get_database(Name=config.glue_database)
            created = False
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code != "EntityNotFoundException":
                raise
            self._logger.info("Creating Glue database %s", config.glue_database)
            storage_location = f"s3://{config.bucket_name}/{config.analytics_prefix}"
            glue_client.create_database(
                DatabaseInput={
                    "Name": config.glue_database,
                    "Description": "Data lake analytics catalog",
                    "LocationUri": storage_location,
                }
            )
            created = True
        return "created" if created else "updated"

    def _ensure_glue_crawler(self, config: DataLakeConfig) -> str:
        if not config.crawler_role_arn:
            raise ValueError("crawler_role_arn is required when crawler_name is set")

        glue_client = self._sessions.client("glue")
        exists = False
        try:
            glue_client.get_crawler(Name=config.crawler_name)
            exists = True
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code != "EntityNotFoundException":
                raise

        target_path = config.crawler_s3_target_path or f"s3://{config.bucket_name}/{config.raw_prefix}"
        targets = {"S3Targets": [{"Path": target_path}]}
        if exists:
            self._logger.info("Updating Glue crawler %s", config.crawler_name)
            update_args = {
                "Name": config.crawler_name,
                "Role": config.crawler_role_arn,
                "DatabaseName": config.glue_database,
                "Targets": targets,
            }
            if config.crawler_schedule:
                update_args["Schedule"] = config.crawler_schedule
            glue_client.update_crawler(**update_args)
            action = "updated"
        else:
            self._logger.info("Creating Glue crawler %s", config.crawler_name)
            create_args = {
                "Name": config.crawler_name,
                "Role": config.crawler_role_arn,
                "DatabaseName": config.glue_database,
                "Targets": targets,
            }
            if config.crawler_schedule:
                create_args["Schedule"] = config.crawler_schedule
            glue_client.create_crawler(**create_args)
            action = "created"
        return action

    # --- Athena --------------------------------------------------------------------

    def _ensure_athena_workgroup(self, config: DataLakeConfig) -> str:
        athena_client = self._sessions.client("athena")
        workgroup = config.athena_workgroup
        result_output = f"s3://{config.bucket_name}/{config.analytics_prefix}athena-results/"
        try:
            athena_client.get_work_group(WorkGroup=workgroup)
            self._logger.info("Updating Athena workgroup %s", workgroup)
            configuration_updates = {
                "EnforceWorkGroupConfiguration": True,
                "ResultConfigurationUpdates": {
                    "OutputLocation": result_output,
                    "RemoveOutputLocation": False,
                },
            }
            if config.kms_key_id:
                configuration_updates["ResultConfigurationUpdates"]["EncryptionConfiguration"] = {
                    "EncryptionOption": "SSE_KMS",
                    "KmsKey": config.kms_key_id,
                }
            else:
                configuration_updates["ResultConfigurationUpdates"]["EncryptionConfiguration"] = {
                    "EncryptionOption": "SSE_S3",
                }
            athena_client.update_work_group(
                WorkGroup=workgroup,
                Description="Managed by DataLakeDeployer",
                ConfigurationUpdates=configuration_updates,
            )
            return "updated"
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code != "InvalidRequestException":
                raise
            if "not found" not in exc.response["Error"].get("Message", "").lower():
                raise

        self._logger.info("Creating Athena workgroup %s", workgroup)
        encryption = {
            "EncryptionOption": "SSE_S3",
        }
        if config.kms_key_id:
            encryption = {
                "EncryptionOption": "SSE_KMS",
                "KmsKey": config.kms_key_id,
            }
        create_args = {
            "Name": workgroup,
            "Configuration": {
                "ResultConfiguration": {
                    "OutputLocation": result_output,
                    "EncryptionConfiguration": encryption,
                },
                "EnforceWorkGroupConfiguration": True,
            },
            "Description": "Managed by DataLakeDeployer",
        }
        athena_client.create_work_group(**create_args)
        return "created"


__all__ = ["DataLakeDeployer"]
