"""AWS service layer for interacting with AWS resources."""
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSService:
    """Service for interacting with AWS resources."""
    
    def __init__(self, region: str = None):
        """Initialize AWS service with boto3 clients."""
        self.region = region or settings.AWS_REGION
        
        # Initialize boto3 session
        session_kwargs = {"region_name": self.region}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        
        self.session = boto3.Session(**session_kwargs)
        
        # Initialize clients
        self.s3_client = self.session.client("s3")
        self.glue_client = self.session.client("glue")
        self.athena_client = self.session.client("athena")
        self.firehose_client = self.session.client("firehose")
        self.iam_client = self.session.client("iam")
        self.ec2_client = self.session.client("ec2")
        self.cloudwatch_client = self.session.client("cloudwatch")
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + "Z"
    
    async def list_s3_buckets(self) -> List[Dict[str, Any]]:
        """List all S3 buckets with details."""
        try:
            response = self.s3_client.list_buckets()
            buckets = []
            
            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]
                bucket_info = {
                    "name": bucket_name,
                    "creation_date": bucket["CreationDate"].isoformat(),
                }
                
                # Get bucket location
                try:
                    location = self.s3_client.get_bucket_location(Bucket=bucket_name)
                    bucket_info["region"] = location.get("LocationConstraint") or "us-east-1"
                except ClientError:
                    bucket_info["region"] = "unknown"
                
                # Get versioning status
                try:
                    versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
                    bucket_info["versioning"] = versioning.get("Status", "Disabled")
                except ClientError:
                    bucket_info["versioning"] = "unknown"
                
                # Get encryption
                try:
                    encryption = self.s3_client.get_bucket_encryption(Bucket=bucket_name)
                    rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                    if rules:
                        bucket_info["encryption"] = rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
                    else:
                        bucket_info["encryption"] = "None"
                except ClientError:
                    bucket_info["encryption"] = "None"
                
                # Get tags
                try:
                    tags_response = self.s3_client.get_bucket_tagging(Bucket=bucket_name)
                    bucket_info["tags"] = {
                        tag["Key"]: tag["Value"]
                        for tag in tags_response.get("TagSet", [])
                    }
                except ClientError:
                    bucket_info["tags"] = {}
                
                buckets.append(bucket_info)
            
            return buckets
            
        except ClientError as e:
            logger.error(f"Error listing S3 buckets: {e}")
            raise
    
    async def get_s3_bucket_details(self, bucket_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific S3 bucket."""
        try:
            details = {"name": bucket_name}
            
            # Get bucket size (approximate)
            try:
                cloudwatch = self.session.client("cloudwatch")
                response = cloudwatch.get_metric_statistics(
                    Namespace="AWS/S3",
                    MetricName="BucketSizeBytes",
                    Dimensions=[
                        {"Name": "BucketName", "Value": bucket_name},
                        {"Name": "StorageType", "Value": "StandardStorage"}
                    ],
                    StartTime=datetime.utcnow().replace(hour=0, minute=0, second=0),
                    EndTime=datetime.utcnow(),
                    Period=86400,
                    Statistics=["Average"]
                )
                if response["Datapoints"]:
                    size_bytes = response["Datapoints"][0]["Average"]
                    details["size_gb"] = round(size_bytes / (1024**3), 2)
                else:
                    details["size_gb"] = 0
            except ClientError:
                details["size_gb"] = "unknown"
            
            # List prefixes
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Delimiter="/",
                    MaxKeys=100
                )
                details["prefixes"] = [
                    prefix["Prefix"]
                    for prefix in response.get("CommonPrefixes", [])
                ]
            except ClientError:
                details["prefixes"] = []
            
            return details
            
        except ClientError as e:
            logger.error(f"Error getting S3 bucket details: {e}")
            raise
    
    async def list_glue_databases(self) -> List[Dict[str, Any]]:
        """List all Glue databases."""
        try:
            response = self.glue_client.get_databases()
            databases = []
            
            for db in response.get("DatabaseList", []):
                db_info = {
                    "name": db["Name"],
                    "description": db.get("Description", ""),
                    "location": db.get("LocationUri", ""),
                    "create_time": db.get("CreateTime", "").isoformat() if db.get("CreateTime") else None,
                }
                
                # Get table count
                try:
                    tables_response = self.glue_client.get_tables(DatabaseName=db["Name"])
                    db_info["tables_count"] = len(tables_response.get("TableList", []))
                except ClientError:
                    db_info["tables_count"] = 0
                
                databases.append(db_info)
            
            return databases
            
        except ClientError as e:
            logger.error(f"Error listing Glue databases: {e}")
            raise
    
    async def list_glue_tables(self, database: str) -> List[Dict[str, Any]]:
        """List all tables in a Glue database."""
        try:
            response = self.glue_client.get_tables(DatabaseName=database)
            tables = []
            
            for table in response.get("TableList", []):
                table_info = {
                    "name": table["Name"],
                    "database": database,
                    "type": table.get("TableType", ""),
                    "location": table.get("StorageDescriptor", {}).get("Location", ""),
                    "create_time": table.get("CreateTime", "").isoformat() if table.get("CreateTime") else None,
                    "update_time": table.get("UpdateTime", "").isoformat() if table.get("UpdateTime") else None,
                    "parameters": table.get("Parameters", {}),
                }
                tables.append(table_info)
            
            return tables
            
        except ClientError as e:
            logger.error(f"Error listing Glue tables: {e}")
            raise
    
    async def list_athena_workgroups(self) -> List[Dict[str, Any]]:
        """List all Athena workgroups."""
        try:
            response = self.athena_client.list_work_groups()
            workgroups = []
            
            for wg in response.get("WorkGroups", []):
                wg_name = wg["Name"]
                
                # Get workgroup details
                try:
                    details = self.athena_client.get_work_group(WorkGroup=wg_name)
                    wg_config = details["WorkGroup"]
                    
                    wg_info = {
                        "name": wg_name,
                        "state": wg_config.get("State", ""),
                        "description": wg_config.get("Description", ""),
                        "creation_time": wg_config.get("CreationTime", "").isoformat() if wg_config.get("CreationTime") else None,
                        "output_location": wg_config.get("Configuration", {}).get("ResultConfiguration", {}).get("OutputLocation", ""),
                    }
                    workgroups.append(wg_info)
                except ClientError:
                    pass
            
            return workgroups
            
        except ClientError as e:
            logger.error(f"Error listing Athena workgroups: {e}")
            raise
    
    async def list_firehose_streams(self) -> List[Dict[str, Any]]:
        """List all Kinesis Firehose delivery streams."""
        try:
            response = self.firehose_client.list_delivery_streams()
            streams = []
            
            for stream_name in response.get("DeliveryStreamNames", []):
                try:
                    details = self.firehose_client.describe_delivery_stream(
                        DeliveryStreamName=stream_name
                    )
                    stream_desc = details["DeliveryStreamDescription"]
                    
                    stream_info = {
                        "name": stream_name,
                        "status": stream_desc.get("DeliveryStreamStatus", ""),
                        "type": stream_desc.get("DeliveryStreamType", ""),
                        "create_time": stream_desc.get("CreateTimestamp", "").isoformat() if stream_desc.get("CreateTimestamp") else None,
                    }
                    streams.append(stream_info)
                except ClientError:
                    pass
            
            return streams
            
        except ClientError as e:
            logger.error(f"Error listing Firehose streams: {e}")
            raise
    
    async def list_iam_roles(self) -> List[Dict[str, Any]]:
        """List IAM roles (filtered for data lake related roles)."""
        try:
            response = self.iam_client.list_roles()
            roles = []
            
            # Filter for roles that might be related to data lake
            keywords = ["datalake", "glue", "firehose", "athena", "crawler"]
            
            for role in response.get("Roles", []):
                role_name = role["RoleName"].lower()
                if any(keyword in role_name for keyword in keywords):
                    role_info = {
                        "name": role["RoleName"],
                        "arn": role["Arn"],
                        "create_date": role["CreateDate"].isoformat(),
                        "description": role.get("Description", ""),
                    }
                    roles.append(role_info)
            
            return roles
            
        except ClientError as e:
            logger.error(f"Error listing IAM roles: {e}")
            raise
    
    async def list_vpc_endpoints(self) -> List[Dict[str, Any]]:
        """List all VPC endpoints."""
        try:
            response = self.ec2_client.describe_vpc_endpoints()
            endpoints = []
            
            for endpoint in response.get("VpcEndpoints", []):
                endpoint_info = {
                    "id": endpoint["VpcEndpointId"],
                    "type": endpoint["VpcEndpointType"],
                    "service_name": endpoint["ServiceName"],
                    "state": endpoint["State"],
                    "vpc_id": endpoint["VpcId"],
                    "creation_time": endpoint.get("CreationTimestamp", "").isoformat() if endpoint.get("CreationTimestamp") else None,
                }
                endpoints.append(endpoint_info)
            
            return endpoints
            
        except ClientError as e:
            logger.error(f"Error listing VPC endpoints: {e}")
            raise
