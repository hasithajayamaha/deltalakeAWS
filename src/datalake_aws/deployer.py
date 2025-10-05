"""High-level API for provisioning an AWS-based data lake using boto3."""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional, Tuple

from botocore.exceptions import ClientError

from .config import DataLakeConfig, FirehoseConfig, IamRoleConfig, LakeFormationConfig, LakeFormationPermission
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
        
        # VPC endpoints should be created first if configured
        if config.vpc_endpoints:
            summary["vpc_endpoints"] = self._ensure_vpc_endpoints(config)
        
        summary["s3_bucket"] = self._ensure_bucket(config)
        summary["glue_database"] = self._ensure_glue_database(config)

        if config.processing_role:
            summary["processing_role"] = self._ensure_iam_role(config.processing_role, config.tags)
        if config.firehose:
            summary["firehose_stream"] = self._ensure_firehose_stream(config)

        if config.crawler_name:
            summary["glue_crawler"] = self._ensure_glue_crawler(config)
        if config.athena_workgroup:
            summary["athena_workgroup"] = self._ensure_athena_workgroup(config)

        if config.enable_transactional_tables:
            summary["transactional_assets"] = self._ensure_transactional_assets(config)

        if config.lake_formation and config.lake_formation.enable_lake_formation:
            summary["lake_formation"] = self._ensure_lake_formation(config)

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
            # Update tags on existing database
            if config.tags:
                self._logger.debug("Updating tags on Glue database %s", config.glue_database)
                self._tag_glue_resource(
                    glue_client,
                    f"arn:aws:glue:{config.region}:{self._get_account_id()}:database/{config.glue_database}",
                    config.tags
                )
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
            # Tag newly created database
            if config.tags:
                self._logger.debug("Tagging Glue database %s", config.glue_database)
                self._tag_glue_resource(
                    glue_client,
                    f"arn:aws:glue:{config.region}:{self._get_account_id()}:database/{config.glue_database}",
                    config.tags
                )
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
            # Update tags on existing crawler
            if config.tags:
                self._logger.debug("Updating tags on Glue crawler %s", config.crawler_name)
                self._tag_glue_resource(
                    glue_client,
                    f"arn:aws:glue:{config.region}:{self._get_account_id()}:crawler/{config.crawler_name}",
                    config.tags
                )
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
            if config.tags:
                create_args["Tags"] = config.tags
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
            # Update tags on existing workgroup
            if config.tags:
                self._logger.debug("Updating tags on Athena workgroup %s", workgroup)
                athena_client.tag_resource(
                    ResourceARN=f"arn:aws:athena:{config.region}:{self._get_account_id()}:workgroup/{workgroup}",
                    Tags=[{"Key": k, "Value": v} for k, v in config.tags.items()]
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
        if config.tags:
            create_args["Tags"] = [{"Key": k, "Value": v} for k, v in config.tags.items()]
        athena_client.create_work_group(**create_args)
        return "created"

    # --- IAM -----------------------------------------------------------------------

    def _ensure_iam_role(self, role_config: IamRoleConfig, tags: Optional[Dict[str, str]] = None) -> str:
        iam_client = self._sessions.client("iam")
        created = False
        try:
            iam_client.get_role(RoleName=role_config.name)
        except ClientError as exc:
            if exc.response["Error"].get("Code") != "NoSuchEntity":
                raise
            self._logger.info("Creating IAM role %s", role_config.name)
            create_args = {
                "RoleName": role_config.name,
                "AssumeRolePolicyDocument": json.dumps(role_config.assume_role_policy),
                "Description": "Managed by DataLakeDeployer",
            }
            if tags:
                create_args["Tags"] = [{"Key": k, "Value": v} for k, v in tags.items()]
            iam_client.create_role(**create_args)
            created = True
        else:
            self._logger.debug("IAM role %s already exists; refreshing trust policy", role_config.name)
            iam_client.update_assume_role_policy(
                RoleName=role_config.name,
                PolicyDocument=json.dumps(role_config.assume_role_policy),
            )
            # Update tags on existing role
            if tags:
                self._logger.debug("Updating tags on IAM role %s", role_config.name)
                # Remove old tags and add new ones
                try:
                    existing_tags = iam_client.list_role_tags(RoleName=role_config.name).get("Tags", [])
                    if existing_tags:
                        iam_client.untag_role(
                            RoleName=role_config.name,
                            TagKeys=[tag["Key"] for tag in existing_tags]
                        )
                except ClientError:
                    pass
                iam_client.tag_role(
                    RoleName=role_config.name,
                    Tags=[{"Key": k, "Value": v} for k, v in tags.items()]
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
        create_args = {
            "DeliveryStreamName": stream_name,
            "DeliveryStreamType": "DirectPut",
            "ExtendedS3DestinationConfiguration": {
                "RoleARN": role_arn,
                "BucketARN": bucket_arn,
                "Prefix": destination_prefix,
                "BufferingHints": buffering_hints,
                "CompressionFormat": firehose_cfg.compression_format,
            },
        }
        if config.tags:
            create_args["Tags"] = [{"Key": k, "Value": v} for k, v in config.tags.items()]
        firehose_client.create_delivery_stream(**create_args)
        
        # Tag existing stream if updating
        if exists:
            try:
                self._logger.debug("Updating tags on Firehose stream %s", stream_name)
                firehose_client.tag_delivery_stream(
                    DeliveryStreamName=stream_name,
                    Tags=[{"Key": k, "Value": v} for k, v in config.tags.items()]
                )
            except ClientError:
                pass
        
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
        return self._ensure_iam_role(role_config, config.tags)

    def _role_arn(self, role_name: str) -> str:
        iam_client = self._sessions.client("iam")
        response = iam_client.get_role(RoleName=role_name)
        return response["Role"]["Arn"]

    # --- VPC Endpoints -------------------------------------------------------------

    def _ensure_vpc_endpoints(self, config: DataLakeConfig) -> str:
        """Ensure VPC endpoints for S3, Glue, and Athena are configured."""
        vpc_config = config.vpc_endpoints
        if vpc_config is None:
            return "skipped"

        ec2_client = self._sessions.client("ec2")
        created_count = 0
        updated_count = 0

        # S3 Gateway Endpoint (uses route tables)
        if vpc_config.enable_s3:
            s3_status = self._ensure_s3_gateway_endpoint(ec2_client, config)
            if s3_status == "created":
                created_count += 1
            elif s3_status == "updated":
                updated_count += 1

        # Glue Interface Endpoint (uses subnets and security groups)
        if vpc_config.enable_glue:
            glue_status = self._ensure_interface_endpoint(
                ec2_client, config, "glue", f"com.amazonaws.{config.region}.glue"
            )
            if glue_status == "created":
                created_count += 1
            elif glue_status == "updated":
                updated_count += 1

        # Athena Interface Endpoint
        if vpc_config.enable_athena:
            athena_status = self._ensure_interface_endpoint(
                ec2_client, config, "athena", f"com.amazonaws.{config.region}.athena"
            )
            if athena_status == "created":
                created_count += 1
            elif athena_status == "updated":
                updated_count += 1

        if created_count > 0:
            return f"created ({created_count} endpoints)"
        elif updated_count > 0:
            return f"updated ({updated_count} endpoints)"
        else:
            return "skipped"

    def _ensure_s3_gateway_endpoint(self, ec2_client, config: DataLakeConfig) -> str:
        """Ensure S3 gateway endpoint exists."""
        vpc_config = config.vpc_endpoints
        if vpc_config is None:
            return "skipped"

        service_name = f"com.amazonaws.{config.region}.s3"
        
        # Check if endpoint already exists
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_config.vpc_id]},
                    {"Name": "service-name", "Values": [service_name]},
                    {"Name": "vpc-endpoint-type", "Values": ["Gateway"]},
                ]
            )
            endpoints = response.get("VpcEndpoints", [])
            
            if endpoints:
                endpoint_id = endpoints[0]["VpcEndpointId"]
                self._logger.info("S3 gateway endpoint %s already exists, updating route tables", endpoint_id)
                
                # Update route tables if needed
                if vpc_config.route_table_ids:
                    ec2_client.modify_vpc_endpoint(
                        VpcEndpointId=endpoint_id,
                        AddRouteTableIds=vpc_config.route_table_ids,
                    )
                return "updated"
        except ClientError as exc:
            self._logger.debug("Error checking S3 endpoint: %s", exc)

        # Create new endpoint
        self._logger.info("Creating S3 gateway endpoint in VPC %s", vpc_config.vpc_id)
        create_args = {
            "VpcId": vpc_config.vpc_id,
            "ServiceName": service_name,
            "VpcEndpointType": "Gateway",
        }
        
        if vpc_config.route_table_ids:
            create_args["RouteTableIds"] = vpc_config.route_table_ids
        
        if config.tags:
            tag_specs = [
                {
                    "ResourceType": "vpc-endpoint",
                    "Tags": [{"Key": k, "Value": v} for k, v in config.tags.items()],
                }
            ]
            create_args["TagSpecifications"] = tag_specs

        ec2_client.create_vpc_endpoint(**create_args)
        return "created"

    def _ensure_interface_endpoint(
        self, ec2_client, config: DataLakeConfig, service_type: str, service_name: str
    ) -> str:
        """Ensure interface endpoint exists for a service."""
        vpc_config = config.vpc_endpoints
        if vpc_config is None:
            return "skipped"

        # Check if endpoint already exists
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_config.vpc_id]},
                    {"Name": "service-name", "Values": [service_name]},
                    {"Name": "vpc-endpoint-type", "Values": ["Interface"]},
                ]
            )
            endpoints = response.get("VpcEndpoints", [])
            
            if endpoints:
                endpoint_id = endpoints[0]["VpcEndpointId"]
                self._logger.info("%s interface endpoint %s already exists", service_type, endpoint_id)
                
                # Update security groups and subnets if needed
                modify_args = {"VpcEndpointId": endpoint_id}
                needs_update = False
                
                if vpc_config.security_group_ids:
                    modify_args["AddSecurityGroupIds"] = vpc_config.security_group_ids
                    needs_update = True
                
                if vpc_config.subnet_ids:
                    modify_args["AddSubnetIds"] = vpc_config.subnet_ids
                    needs_update = True
                
                if needs_update:
                    ec2_client.modify_vpc_endpoint(**modify_args)
                    return "updated"
                return "skipped"
        except ClientError as exc:
            self._logger.debug("Error checking %s endpoint: %s", service_type, exc)

        # Create new endpoint
        self._logger.info("Creating %s interface endpoint in VPC %s", service_type, vpc_config.vpc_id)
        create_args = {
            "VpcId": vpc_config.vpc_id,
            "ServiceName": service_name,
            "VpcEndpointType": "Interface",
            "PrivateDnsEnabled": vpc_config.enable_private_dns,
        }
        
        if vpc_config.subnet_ids:
            create_args["SubnetIds"] = vpc_config.subnet_ids
        
        if vpc_config.security_group_ids:
            create_args["SecurityGroupIds"] = vpc_config.security_group_ids
        
        if config.tags:
            tag_specs = [
                {
                    "ResourceType": "vpc-endpoint",
                    "Tags": [{"Key": k, "Value": v} for k, v in config.tags.items()],
                }
            ]
            create_args["TagSpecifications"] = tag_specs

        ec2_client.create_vpc_endpoint(**create_args)
        return "created"

    # --- Lake Formation ------------------------------------------------------------

    def _ensure_lake_formation(self, config: DataLakeConfig) -> str:
        """Configure AWS Lake Formation for fine-grained access control."""
        lf_config = config.lake_formation
        if lf_config is None or not lf_config.enable_lake_formation:
            return "skipped"

        lf_client = self._sessions.client("lakeformation")
        actions_taken = []

        # Configure data lake administrators
        if lf_config.data_lake_admins:
            self._logger.info("Configuring Lake Formation data lake administrators")
            self._set_data_lake_admins(lf_client, lf_config.data_lake_admins)
            actions_taken.append("admins")

        # Register S3 location with Lake Formation
        if lf_config.register_s3_location:
            self._logger.info("Registering S3 location with Lake Formation")
            s3_location = f"s3://{config.bucket_name}/"
            self._register_s3_location(lf_client, s3_location, config)
            actions_taken.append("s3_location")

        # Update Glue database to use Lake Formation permissions
        if lf_config.use_lake_formation_credentials:
            self._logger.info("Updating Glue database for Lake Formation")
            self._update_database_for_lake_formation(config)
            actions_taken.append("database_settings")

        # Grant Lake Formation permissions
        if lf_config.permissions:
            self._logger.info("Granting Lake Formation permissions")
            granted = self._grant_lake_formation_permissions(lf_client, config, lf_config.permissions)
            actions_taken.append(f"permissions({granted})")

        return f"configured: {', '.join(actions_taken)}" if actions_taken else "configured"

    def _set_data_lake_admins(self, lf_client, admins: List[str]) -> None:
        """Set Lake Formation data lake administrators."""
        try:
            # Get current settings
            current_settings = lf_client.get_data_lake_settings()
            
            # Build admin list
            admin_principals = []
            for admin in admins:
                if admin.startswith("arn:"):
                    admin_principals.append({"DataLakePrincipalIdentifier": admin})
                else:
                    # Assume it's an IAM user/role name, construct ARN
                    account_id = self._get_account_id()
                    if "/" in admin:
                        # Role with path
                        admin_arn = f"arn:aws:iam::{account_id}:role/{admin}"
                    else:
                        # Simple role name
                        admin_arn = f"arn:aws:iam::{account_id}:role/{admin}"
                    admin_principals.append({"DataLakePrincipalIdentifier": admin_arn})
            
            # Update settings
            lf_client.put_data_lake_settings(
                DataLakeSettings={
                    "DataLakeAdmins": admin_principals,
                    "CreateDatabaseDefaultPermissions": [],
                    "CreateTableDefaultPermissions": [],
                }
            )
            self._logger.debug("Set %d Lake Formation administrators", len(admin_principals))
        except ClientError as exc:
            self._logger.warning("Failed to set Lake Formation administrators: %s", exc)

    def _register_s3_location(self, lf_client, s3_location: str, config: DataLakeConfig) -> None:
        """Register S3 location with Lake Formation."""
        try:
            # Check if already registered
            response = lf_client.list_resources(
                FilterConditionList=[
                    {
                        "Field": "RESOURCE_ARN",
                        "ComparisonOperator": "EQ",
                        "StringValueList": [f"arn:aws:s3:::{config.bucket_name}"]
                    }
                ]
            )
            
            if response.get("ResourceInfoList"):
                self._logger.debug("S3 location already registered with Lake Formation")
                return
            
            # Register the location
            # Need an IAM role for Lake Formation to access S3
            role_arn = self._get_or_create_lf_service_role(config)
            
            lf_client.register_resource(
                ResourceArn=f"arn:aws:s3:::{config.bucket_name}",
                UseServiceLinkedRole=False,
                RoleArn=role_arn
            )
            self._logger.debug("Registered S3 location with Lake Formation")
        except ClientError as exc:
            self._logger.warning("Failed to register S3 location: %s", exc)

    def _get_or_create_lf_service_role(self, config: DataLakeConfig) -> str:
        """Get or create IAM role for Lake Formation service."""
        role_name = f"{config.bucket_name}-lakeformation-role"
        iam_client = self._sessions.client("iam")
        
        try:
            response = iam_client.get_role(RoleName=role_name)
            return response["Role"]["Arn"]
        except ClientError as exc:
            if exc.response["Error"].get("Code") != "NoSuchEntity":
                raise
        
        # Create the role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lakeformation.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        inline_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{config.bucket_name}",
                        f"arn:aws:s3:::{config.bucket_name}/*"
                    ]
                }
            ]
        }
        
        role_config = IamRoleConfig(
            name=role_name,
            assume_role_policy=trust_policy,
            inline_policies={"lakeformation-s3-access": inline_policy}
        )
        
        self._ensure_iam_role(role_config, config.tags)
        return f"arn:aws:iam::{self._get_account_id()}:role/{role_name}"

    def _update_database_for_lake_formation(self, config: DataLakeConfig) -> None:
        """Update Glue database to use Lake Formation permissions."""
        glue_client = self._sessions.client("glue")
        
        try:
            # Get current database
            response = glue_client.get_database(Name=config.glue_database)
            database = response["Database"]
            
            # Update to use Lake Formation permissions
            database_input = {
                "Name": database["Name"],
                "Description": database.get("Description", "Data lake analytics catalog"),
                "LocationUri": database.get("LocationUri", ""),
                "CreateTableDefaultPermissions": [],  # Disable default permissions
            }
            
            glue_client.update_database(
                Name=config.glue_database,
                DatabaseInput=database_input
            )
            self._logger.debug("Updated database to use Lake Formation permissions")
        except ClientError as exc:
            self._logger.warning("Failed to update database for Lake Formation: %s", exc)

    def _grant_lake_formation_permissions(
        self, lf_client, config: DataLakeConfig, permissions: List[LakeFormationPermission]
    ) -> int:
        """Grant Lake Formation permissions."""
        granted_count = 0
        
        for perm in permissions:
            try:
                # Build resource specification
                resource = self._build_lf_resource(perm, config)
                
                # Build principal
                principal = {"DataLakePrincipalIdentifier": perm.principal}
                
                # Grant permissions
                grant_args = {
                    "Principal": principal,
                    "Resource": resource,
                    "Permissions": perm.permissions,
                }
                
                if perm.permissions_with_grant_option:
                    grant_args["PermissionsWithGrantOption"] = perm.permissions_with_grant_option
                
                lf_client.grant_permissions(**grant_args)
                granted_count += 1
                self._logger.debug(
                    "Granted %s permissions to %s on %s",
                    perm.permissions,
                    perm.principal,
                    perm.resource_type
                )
            except ClientError as exc:
                error_code = exc.response["Error"].get("Code", "")
                if error_code == "AlreadyExistsException":
                    self._logger.debug("Permission already exists, skipping")
                    granted_count += 1
                else:
                    self._logger.warning("Failed to grant permission: %s", exc)
        
        return granted_count

    def _build_lf_resource(self, perm: LakeFormationPermission, config: DataLakeConfig) -> Dict[str, object]:
        """Build Lake Formation resource specification."""
        resource_type = perm.resource_type.upper()
        
        if resource_type == "DATABASE":
            return {
                "Database": {
                    "Name": perm.database_name or config.glue_database
                }
            }
        elif resource_type == "TABLE":
            table_resource = {
                "DatabaseName": perm.database_name or config.glue_database
            }
            if perm.table_wildcard:
                table_resource["TableWildcard"] = {}
            elif perm.table_name:
                table_resource["Name"] = perm.table_name
            else:
                raise ValueError("table_name or table_wildcard must be specified for TABLE resource")
            
            return {"Table": table_resource}
        elif resource_type == "DATA_LOCATION":
            return {
                "DataLocation": {
                    "ResourceArn": f"arn:aws:s3:::{config.bucket_name}"
                }
            }
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

    # --- Helper Methods ------------------------------------------------------------

    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        sts_client = self._sessions.client("sts")
        return sts_client.get_caller_identity()["Account"]

    def _tag_glue_resource(self, glue_client, resource_arn: str, tags: Dict[str, str]) -> None:
        """Tag a Glue resource."""
        try:
            glue_client.tag_resource(ResourceArn=resource_arn, TagsToAdd=tags)
        except ClientError as exc:
            self._logger.warning("Failed to tag Glue resource %s: %s", resource_arn, exc)

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
