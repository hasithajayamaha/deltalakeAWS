"""Discovery API routes for AWS resources."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging

from app.services.aws_service import AWSService
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/discover")
async def discover_resources(
    region: Optional[str] = Query(None, description="AWS region to discover resources in")
) -> Dict[str, Any]:
    """
    Discover all deployed AWS data lake resources.
    
    Returns a complete snapshot of the current architecture including:
    - S3 buckets
    - Glue databases and tables
    - Athena workgroups
    - Firehose streams
    - IAM roles
    - VPC endpoints
    """
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        logger.info(f"Discovering resources in region: {aws_region}")
        
        # Discover all resources
        resources = {
            "timestamp": aws_service.get_current_timestamp(),
            "region": aws_region,
            "resources": {
                "s3_buckets": await aws_service.list_s3_buckets(),
                "glue_databases": await aws_service.list_glue_databases(),
                "athena_workgroups": await aws_service.list_athena_workgroups(),
                "firehose_streams": await aws_service.list_firehose_streams(),
                "iam_roles": await aws_service.list_iam_roles(),
                "vpc_endpoints": await aws_service.list_vpc_endpoints(),
            }
        }
        
        # Calculate summary statistics
        resources["summary"] = {
            "total_resources": sum(
                len(v) if isinstance(v, list) else 0
                for v in resources["resources"].values()
            ),
            "s3_buckets_count": len(resources["resources"]["s3_buckets"]),
            "glue_databases_count": len(resources["resources"]["glue_databases"]),
            "athena_workgroups_count": len(resources["resources"]["athena_workgroups"]),
        }
        
        return resources
        
    except Exception as e:
        logger.error(f"Error discovering resources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/s3")
async def list_s3_buckets(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all S3 buckets with detailed information."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        buckets = await aws_service.list_s3_buckets()
        
        return {
            "region": aws_region,
            "count": len(buckets),
            "buckets": buckets
        }
        
    except Exception as e:
        logger.error(f"Error listing S3 buckets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/s3/{bucket_name}")
async def get_s3_bucket_details(
    bucket_name: str,
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """Get detailed information about a specific S3 bucket."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        details = await aws_service.get_s3_bucket_details(bucket_name)
        
        return details
        
    except Exception as e:
        logger.error(f"Error getting S3 bucket details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/glue/databases")
async def list_glue_databases(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all Glue databases."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        databases = await aws_service.list_glue_databases()
        
        return {
            "region": aws_region,
            "count": len(databases),
            "databases": databases
        }
        
    except Exception as e:
        logger.error(f"Error listing Glue databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/glue/tables")
async def list_glue_tables(
    database: str = Query(..., description="Database name"),
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all tables in a Glue database."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        tables = await aws_service.list_glue_tables(database)
        
        return {
            "region": aws_region,
            "database": database,
            "count": len(tables),
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Error listing Glue tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/athena/workgroups")
async def list_athena_workgroups(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all Athena workgroups."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        workgroups = await aws_service.list_athena_workgroups()
        
        return {
            "region": aws_region,
            "count": len(workgroups),
            "workgroups": workgroups
        }
        
    except Exception as e:
        logger.error(f"Error listing Athena workgroups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/firehose/streams")
async def list_firehose_streams(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all Kinesis Firehose delivery streams."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        streams = await aws_service.list_firehose_streams()
        
        return {
            "region": aws_region,
            "count": len(streams),
            "streams": streams
        }
        
    except Exception as e:
        logger.error(f"Error listing Firehose streams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/iam/roles")
async def list_iam_roles(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List IAM roles created by deltalake-aws."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        roles = await aws_service.list_iam_roles()
        
        return {
            "region": aws_region,
            "count": len(roles),
            "roles": roles
        }
        
    except Exception as e:
        logger.error(f"Error listing IAM roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/vpc/endpoints")
async def list_vpc_endpoints(
    region: Optional[str] = Query(None, description="AWS region")
) -> Dict[str, Any]:
    """List all VPC endpoints."""
    try:
        aws_region = region or settings.AWS_REGION
        aws_service = AWSService(region=aws_region)
        
        endpoints = await aws_service.list_vpc_endpoints()
        
        return {
            "region": aws_region,
            "count": len(endpoints),
            "endpoints": endpoints
        }
        
    except Exception as e:
        logger.error(f"Error listing VPC endpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
