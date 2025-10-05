"""Cost estimation API routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging
import sys
import os

# Add parent directory to path to import deltalake_aws
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from datalake_aws import CostEstimator, DataLakeConfig
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/cost/estimate")
async def estimate_cost(
    config_path: Optional[str] = Query(None, description="Path to TOML config file"),
    scenario: Optional[str] = Query("medium", description="Scenario: light, medium, or heavy"),
    storage_gb: Optional[int] = Query(None, description="Storage in GB"),
    monthly_queries: Optional[int] = Query(None, description="Monthly Athena queries"),
) -> Dict[str, Any]:
    """
    Estimate monthly costs for the data lake.
    
    Returns cost breakdown by service and usage assumptions.
    """
    try:
        # Load configuration
        if config_path:
            config = DataLakeConfig.from_toml(config_path)
        else:
            # Create minimal config for estimation
            config = DataLakeConfig(
                region=settings.AWS_REGION,
                bucket_name="example-bucket",
                glue_database="example_db"
            )
        
        estimator = CostEstimator()
        
        # Get estimate based on scenario or custom parameters
        if storage_gb and monthly_queries:
            estimate = estimator.estimate(
                config,
                storage_gb=storage_gb,
                monthly_queries=monthly_queries
            )
        else:
            # Use predefined scenarios
            scenarios = estimator.estimate_with_scenarios(config)
            scenario_key = f"{scenario.capitalize()} Usage"
            
            # Find matching scenario
            estimate = None
            for key, est in scenarios.items():
                if scenario.lower() in key.lower():
                    estimate = est
                    break
            
            if not estimate:
                estimate = scenarios.get("Medium Usage (Small Production)")
        
        return {
            "monthly_cost": estimate.monthly_cost,
            "currency": estimate.currency,
            "breakdown": estimate.breakdown,
            "assumptions": estimate.assumptions,
        }
        
    except Exception as e:
        logger.error(f"Error estimating cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/scenarios")
async def get_cost_scenarios(
    config_path: Optional[str] = Query(None, description="Path to TOML config file")
) -> Dict[str, Any]:
    """
    Get cost estimates for all scenarios (light, medium, heavy).
    """
    try:
        # Load configuration
        if config_path:
            config = DataLakeConfig.from_toml(config_path)
        else:
            config = DataLakeConfig(
                region=settings.AWS_REGION,
                bucket_name="example-bucket",
                glue_database="example_db"
            )
        
        estimator = CostEstimator()
        scenarios = estimator.estimate_with_scenarios(config)
        
        result = {}
        for scenario_name, estimate in scenarios.items():
            result[scenario_name] = {
                "monthly_cost": estimate.monthly_cost,
                "currency": estimate.currency,
                "breakdown": estimate.breakdown,
                "assumptions": estimate.assumptions,
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting cost scenarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/breakdown")
async def get_cost_breakdown(
    config_path: Optional[str] = Query(None, description="Path to TOML config file"),
    storage_gb: int = Query(100, description="Storage in GB"),
    monthly_queries: int = Query(100, description="Monthly Athena queries"),
) -> Dict[str, Any]:
    """
    Get detailed cost breakdown by service.
    """
    try:
        # Load configuration
        if config_path:
            config = DataLakeConfig.from_toml(config_path)
        else:
            config = DataLakeConfig(
                region=settings.AWS_REGION,
                bucket_name="example-bucket",
                glue_database="example_db"
            )
        
        estimator = CostEstimator()
        estimate = estimator.estimate(
            config,
            storage_gb=storage_gb,
            monthly_queries=monthly_queries
        )
        
        # Sort breakdown by cost (highest first)
        sorted_breakdown = dict(
            sorted(estimate.breakdown.items(), key=lambda x: x[1], reverse=True)
        )
        
        return {
            "total_monthly_cost": estimate.monthly_cost,
            "currency": estimate.currency,
            "breakdown": sorted_breakdown,
            "breakdown_percentage": {
                service: round((cost / estimate.monthly_cost) * 100, 1)
                for service, cost in sorted_breakdown.items()
            },
            "assumptions": estimate.assumptions,
        }
        
    except Exception as e:
        logger.error(f"Error getting cost breakdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
