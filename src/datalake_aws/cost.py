"""Cost estimation for AWS data lake resources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .config import DataLakeConfig


@dataclass
class CostEstimate:
    """Cost estimate for data lake resources."""

    monthly_cost: float
    breakdown: Dict[str, float]
    assumptions: Dict[str, str]
    currency: str = "USD"

    def format_summary(self) -> str:
        """Format cost estimate as human-readable summary."""
        lines = [
            f"\n{'='*60}",
            "ESTIMATED MONTHLY COST",
            f"{'='*60}",
            f"\nTotal: ${self.monthly_cost:.2f} {self.currency}/month\n",
            "Breakdown:",
        ]

        for service, cost in sorted(self.breakdown.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {service:.<40} ${cost:>8.2f}")

        lines.extend([
            f"\n{'='*60}",
            "ASSUMPTIONS:",
        ])

        for key, value in self.assumptions.items():
            lines.append(f"  • {key}: {value}")

        lines.extend([
            f"\n{'='*60}",
            "NOTE: These are estimates based on AWS pricing as of 2024.",
            "Actual costs may vary based on usage patterns and AWS pricing changes.",
            "This does not include data transfer costs or optional services.",
            f"{'='*60}\n",
        ])

        return "\n".join(lines)


class CostEstimator:
    """
    Estimate monthly costs for data lake resources.
    
    Pricing is based on AWS US East (N. Virginia) region as of 2024.
    Actual costs may vary by region and over time.
    """

    # AWS Pricing (USD, us-east-1, as of 2024)
    PRICING = {
        # S3 Standard Storage (per GB/month)
        "s3_storage_gb": 0.023,
        
        # S3 Requests (per 1000 requests)
        "s3_put_requests_per_1k": 0.005,
        "s3_get_requests_per_1k": 0.0004,
        
        # Glue Crawler (per DPU-hour)
        "glue_crawler_dpu_hour": 0.44,
        
        # Glue Data Catalog (per 100k objects stored per month)
        "glue_catalog_per_100k": 1.00,
        
        # Athena (per TB scanned)
        "athena_tb_scanned": 5.00,
        
        # Kinesis Data Firehose (per GB ingested)
        "firehose_gb": 0.029,
        
        # KMS (per 10k requests)
        "kms_requests_per_10k": 0.03,
        
        # VPC Endpoint (per hour)
        "vpc_endpoint_hour": 0.01,
        
        # VPC Endpoint (per GB processed)
        "vpc_endpoint_gb": 0.01,
    }

    def estimate(
        self,
        config: DataLakeConfig,
        storage_gb: int = 100,
        monthly_queries: int = 100,
        avg_query_scan_gb: float = 10.0,
        firehose_gb_per_day: float = 1.0,
    ) -> CostEstimate:
        """
        Estimate monthly costs for the data lake.
        
        Args:
            config: Data lake configuration
            storage_gb: Estimated S3 storage in GB
            monthly_queries: Number of Athena queries per month
            avg_query_scan_gb: Average data scanned per query in GB
            firehose_gb_per_day: Daily data ingestion via Firehose in GB
            
        Returns:
            CostEstimate with breakdown and assumptions
        """
        breakdown: Dict[str, float] = {}
        assumptions: Dict[str, str] = {}

        # S3 Storage
        s3_cost = storage_gb * self.PRICING["s3_storage_gb"]
        breakdown["S3 Storage"] = s3_cost
        assumptions["S3 Storage"] = f"{storage_gb} GB stored"

        # S3 Requests (estimate based on typical usage)
        # Assume 10 PUT requests per GB stored per month
        put_requests = storage_gb * 10
        s3_put_cost = (put_requests / 1000) * self.PRICING["s3_put_requests_per_1k"]
        
        # Assume 100 GET requests per GB stored per month
        get_requests = storage_gb * 100
        s3_get_cost = (get_requests / 1000) * self.PRICING["s3_get_requests_per_1k"]
        
        breakdown["S3 Requests"] = s3_put_cost + s3_get_cost
        assumptions["S3 Requests"] = f"{put_requests:,.0f} PUT, {get_requests:,.0f} GET per month"

        # Glue Data Catalog
        # Estimate 1000 objects (tables/partitions) per 100 GB
        catalog_objects = max(1000, (storage_gb / 100) * 1000)
        catalog_cost = (catalog_objects / 100000) * self.PRICING["glue_catalog_per_100k"]
        breakdown["Glue Data Catalog"] = catalog_cost
        assumptions["Glue Catalog"] = f"{catalog_objects:,.0f} objects stored"

        # Glue Crawler (if configured)
        if config.crawler_name:
            # Assume daily runs, 10 minutes each, 2 DPUs
            crawler_hours_per_month = (10 / 60) * 30 * 2  # 10 hours/month
            crawler_cost = crawler_hours_per_month * self.PRICING["glue_crawler_dpu_hour"]
            breakdown["Glue Crawler"] = crawler_cost
            assumptions["Glue Crawler"] = "Daily runs, 10 min each, 2 DPUs"

        # Athena
        if config.athena_workgroup:
            total_scan_tb = (monthly_queries * avg_query_scan_gb) / 1000
            athena_cost = total_scan_tb * self.PRICING["athena_tb_scanned"]
            breakdown["Athena Queries"] = athena_cost
            assumptions["Athena"] = f"{monthly_queries} queries, {avg_query_scan_gb} GB avg scan"

        # Kinesis Data Firehose (if configured)
        if config.firehose:
            monthly_firehose_gb = firehose_gb_per_day * 30
            firehose_cost = monthly_firehose_gb * self.PRICING["firehose_gb"]
            breakdown["Kinesis Firehose"] = firehose_cost
            assumptions["Firehose"] = f"{firehose_gb_per_day} GB/day ingestion"

        # KMS (if configured)
        if config.kms_key_id:
            # Estimate 10k encryption/decryption requests per GB stored
            kms_requests = storage_gb * 10000
            kms_cost = (kms_requests / 10000) * self.PRICING["kms_requests_per_10k"]
            breakdown["KMS Encryption"] = kms_cost
            assumptions["KMS"] = f"{kms_requests:,.0f} requests per month"

        # VPC Endpoints (if configured)
        if config.vpc_endpoints:
            endpoint_count = 0
            if config.vpc_endpoints.enable_s3:
                endpoint_count += 1
            if config.vpc_endpoints.enable_glue:
                endpoint_count += 1
            if config.vpc_endpoints.enable_athena:
                endpoint_count += 1

            # Interface endpoints cost per hour
            hours_per_month = 730  # Average hours in a month
            vpc_endpoint_cost = endpoint_count * hours_per_month * self.PRICING["vpc_endpoint_hour"]
            
            # Data processing cost (estimate 10% of storage accessed via VPC)
            vpc_data_gb = storage_gb * 0.1
            vpc_data_cost = vpc_data_gb * self.PRICING["vpc_endpoint_gb"]
            
            breakdown["VPC Endpoints"] = vpc_endpoint_cost + vpc_data_cost
            assumptions["VPC Endpoints"] = f"{endpoint_count} endpoints, {vpc_data_gb:.0f} GB processed"

        # Calculate total
        total_cost = sum(breakdown.values())

        return CostEstimate(
            monthly_cost=total_cost,
            breakdown=breakdown,
            assumptions=assumptions,
        )

    def estimate_with_scenarios(self, config: DataLakeConfig) -> Dict[str, CostEstimate]:
        """
        Estimate costs for different usage scenarios.
        
        Args:
            config: Data lake configuration
            
        Returns:
            Dictionary of scenario names to cost estimates
        """
        scenarios = {
            "Light Usage (Dev/Test)": self.estimate(
                config,
                storage_gb=50,
                monthly_queries=50,
                avg_query_scan_gb=5.0,
                firehose_gb_per_day=0.5,
            ),
            "Medium Usage (Small Production)": self.estimate(
                config,
                storage_gb=500,
                monthly_queries=500,
                avg_query_scan_gb=20.0,
                firehose_gb_per_day=5.0,
            ),
            "Heavy Usage (Large Production)": self.estimate(
                config,
                storage_gb=5000,
                monthly_queries=2000,
                avg_query_scan_gb=50.0,
                firehose_gb_per_day=50.0,
            ),
        }
        return scenarios


__all__ = ["CostEstimator", "CostEstimate"]
