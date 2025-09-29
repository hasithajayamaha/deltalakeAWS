"""High-level API for provisioning an AWS-based data lake using boto3."""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional, Tuple

from botocore.exceptions import ClientError

from .config import DataLakeConfig, FirehoseConfig, IamRoleConfig
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

        if config.processing_role:
            summary["processing_role"] = self._ensure_iam_role(config.processing_role)
        if config.firehose:
            summary["firehose_stream"] = self._ensure_firehose_stream(config)

        if config.crawler_name:
            summary["glue_crawler"] = self._ensure_glue_crawler(config)
        if config.athena_workgroup:
            summary["athena_workgroup"] = self._ensure_athena_workgroup(config)

        if config.enable_transactional_tables:
            summary["transactional_assets"] = self._ensure_transactional_assets(config)

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

    # --- IAM -----------------------------------------------------------------------

    def _ensure_iam_role(self, role_config: IamRoleConfig) -> str:
        iam_client = self._sessions.client("iam")
        created = False
        try:
            iam_client.get_role(RoleName=role_config.name)
        except ClientError as exc:
            if exc.response["Error"].get("Code") != "NoSuchEntity":
                raise
            self._logger.info("Creating IAM role %s", role_config.name)
            iam_client.create_role(
                RoleName=role_config.name,
                AssumeRolePolicyDocument=json.dumps(role_config.assume_role_policy),
                Description="Managed by DataLakeDeployer",
            )
            created = True
        else:
            self._logger.debug("IAM role %s already exists; refreshing trust policy", role_config.name)
            iam_client.update_assume_role_policy(
                RoleName=role_config.name,
                PolicyDocument=json.dumps(role_config.assume_role_policy),
            )

        attached = iam_client.list_attached_role_policies(RoleName=role_config.name)["AttachedPolicies"]
        attached_arns = {policy["PolicyArn"] for policy in attached}
        for policy_arn in role_config.managed_policy_arns:
            if policy_arn not in attached_arns:
                self._logger.debug("Attaching managed policy %s to %s", policy_arn, role_config.name)
                iam_client.attach_role_policy(RoleName=role_config.name, PolicyArn=policy_arn)

        existing_inline = set(iam_client.list_role_policies(RoleName=role_config.name)["PolicyNames"])
        for policy_name, document in role_config.inline_policies.items():
            self._logger.debug("Upserting inline policy %s on %s", policy_name, role_config.name)
            iam_client.put_role_policy(
                RoleName=role_config.name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(document),
            )
            existing_inline.discard(policy_name)

        for policy_name in existing_inline:
            self._logger.debug("Removing unmanaged inline policy %s from %s", policy_name, role_config.name)
            iam_client.delete_role_policy(RoleName=role_config.name, PolicyName=policy_name)

        return "created" if created else "updated"

    # --- Firehose ------------------------------------------------------------------

    def _ensure_firehose_stream(self, config: DataLakeConfig) -> str:
        firehose_cfg = config.firehose
        if firehose_cfg is None:
            return "skipped"

        self._ensure_firehose_role(config, firehose_cfg)
        firehose_client = self._sessions.client("firehose")
        stream_name = firehose_cfg.stream_name

        try:
            description = firehose_client.describe_delivery_stream(DeliveryStreamName=stream_name)
            exists = True
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code != "ResourceNotFoundException":
                raise
            description = None
            exists = False

        bucket_arn = f"arn:aws:s3:::{config.bucket_name}"
        destination_prefix = (firehose_cfg.prefix or config.raw_prefix).rstrip('/') + '/'
        buffering_hints = {
            "IntervalInSeconds": firehose_cfg.buffering_interval,
            "SizeInMBs": firehose_cfg.buffering_size_mib,
        }
        role_arn = self._role_arn(firehose_cfg.role_name)

        if exists and description is not None:
            version, destination_id = self._firehose_version_and_destination(description)
            self._logger.info("Updating Firehose delivery stream %s", stream_name)
            firehose_client.update_destination(
                DeliveryStreamName=stream_name,
                CurrentDeliveryStreamVersionId=version,
                DestinationId=destination_id,
                ExtendedS3DestinationUpdate={
                    "RoleARN": role_arn,
                    "BucketARN": bucket_arn,
                    "Prefix": destination_prefix,
                    "BufferingHints": buffering_hints,
                    "CompressionFormat": firehose_cfg.compression_format,
                },
            )
            return "updated"

        self._logger.info("Creating Firehose delivery stream %s", stream_name)
        firehose_client.create_delivery_stream(
            DeliveryStreamName=stream_name,
            DeliveryStreamType="DirectPut",
            ExtendedS3DestinationConfiguration={
                "RoleARN": role_arn,
                "BucketARN": bucket_arn,
                "Prefix": destination_prefix,
                "BufferingHints": buffering_hints,
                "CompressionFormat": firehose_cfg.compression_format,
            },
        )
        return "created"

    def _firehose_version_and_destination(self, description: Dict[str, object]) -> Tuple[str, str]:
        desc = description["DeliveryStreamDescription"]
        version = str(desc["VersionId"])
        destinations = desc.get("Destinations", [])
        if not destinations:
            raise ValueError("Firehose stream has no destinations configured")
        destination_id = str(destinations[0]["DestinationId"])
        return version, destination_id

    def _ensure_firehose_role(self, config: DataLakeConfig, firehose_cfg: FirehoseConfig) -> str:
        policy_statements = [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:AbortMultipartUpload",
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                    "s3:PutObject",
                ],
                "Resource": [
                    f"arn:aws:s3:::{config.bucket_name}",
                    f"arn:aws:s3:::{config.bucket_name}/*",
                ],
            }
        ]
        if config.kms_key_id:
            policy_statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
                    "Resource": config.kms_key_id,
                }
            )
        inline_policy = {
            "Version": "2012-10-17",
            "Statement": policy_statements,
        }
        role_config = IamRoleConfig(
            name=firehose_cfg.role_name,
            assume_role_policy={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "firehose.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            managed_policy_arns=[],
            inline_policies={"firehose-access": inline_policy},
        )
        return self._ensure_iam_role(role_config)

    def _role_arn(self, role_name: str) -> str:
        iam_client = self._sessions.client("iam")
        response = iam_client.get_role(RoleName=role_name)
        return response["Role"]["Arn"]

    # --- Transactional (Iceberg/Delta) Assets -------------------------------------

    def _ensure_transactional_assets(self, config: DataLakeConfig) -> str:
        if not config.transactional_table_name:
            self._logger.debug("Transactional tables disabled or not configured")
            return "skipped"

        table_format = config.table_format.lower()
        if table_format not in {"iceberg", "delta"}:
            raise ValueError("table_format must be 'iceberg' or 'delta'")

        glue_client = self._sessions.client("glue")
        table_name = config.transactional_table_name
        database = config.glue_database
        location = f"s3://{config.bucket_name}/{config.analytics_prefix}{table_name}/"

        table_input = {
            "Name": table_name,
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {
                "table_type": table_format.upper(),
                "classification": table_format,
                "EXTERNAL": "TRUE",
            },
            "StorageDescriptor": {
                "Columns": [],
                "Location": location,
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                    "Parameters": {"serialization.format": "1"},
                },
                "Parameters": {
                    "table_type": table_format.upper(),
                },
            },
        }

        try:
            glue_client.get_table(DatabaseName=database, Name=table_name)
            self._logger.info("Updating transactional table %s.%s", database, table_name)
            glue_client.update_table(DatabaseName=database, TableInput=table_input)
            action = "updated"
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code", "")
            if error_code != "EntityNotFoundException":
                raise
            self._logger.info("Creating transactional table %s.%s", database, table_name)
            glue_client.create_table(DatabaseName=database, TableInput=table_input)
            action = "created"
        return action


__all__ = ["DataLakeDeployer"]
