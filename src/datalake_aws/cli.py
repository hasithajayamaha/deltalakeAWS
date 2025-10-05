"""Command line entry point for deploying the data lake."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from .config import AwsCredentials, DataLakeConfig
from .deployer import DataLakeDeployer
from .sessions import SessionFactory
from .state import StateManager
from .cost import CostEstimator

_LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision AWS data lake resources")
    parser.add_argument(
        "--region",
        required=True,
        help="AWS region where the data lake will be deployed",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a TOML file containing the [datalake] configuration table",
    )
    parser.add_argument("--access-key", dest="access_key")
    parser.add_argument("--secret-key", dest="secret_key")
    parser.add_argument("--session-token", dest="session_token")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them to AWS",
    )
    parser.add_argument(
        "--estimate-cost",
        action="store_true",
        help="Estimate monthly costs for the data lake",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="Path to state file for tracking deployments (default: .datalake-state.json)",
    )
    parser.add_argument(
        "--show-drift",
        action="store_true",
        help="Show configuration drift from last deployment",
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Show deployment history",
    )
    return parser


def _resolve_credentials(args: argparse.Namespace) -> Optional[AwsCredentials]:
    if args.access_key and args.secret_key:
        return AwsCredentials(
            access_key_id=args.access_key,
            secret_access_key=args.secret_key,
            session_token=args.session_token,
        )
    return None


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    config = DataLakeConfig.from_toml(args.config)
    # Allow region to be overridden from the CLI so the same config can be reused.
    config.region = args.region
    # Set dry-run mode if specified
    config.dry_run = args.dry_run
    
    # Initialize state manager if state file is specified
    state_manager = None
    if args.state_file or not (args.estimate_cost or args.show_history):
        state_manager = StateManager(args.state_file)
    
    # Handle cost estimation
    if args.estimate_cost:
        _LOGGER.info("Estimating monthly costs...")
        estimator = CostEstimator()
        scenarios = estimator.estimate_with_scenarios(config)
        
        for scenario_name, estimate in scenarios.items():
            print(f"\n{'='*60}")
            print(f"SCENARIO: {scenario_name}")
            print(estimate.format_summary())
        
        return 0
    
    # Handle show history
    if args.show_history:
        if not state_manager:
            state_manager = StateManager(args.state_file)
        
        history = state_manager.get_deployment_history()
        if not history:
            _LOGGER.info("No deployment history found")
            return 0
        
        _LOGGER.info("Deployment History (last %d deployments):", len(history))
        for i, deployment in enumerate(history, 1):
            status = "✓ SUCCESS" if deployment.get("success") else "✗ FAILED"
            dry_run = " [DRY-RUN]" if deployment.get("dry_run") else ""
            _LOGGER.info(
                "%d. %s - %s%s - %s",
                i,
                deployment.get("timestamp"),
                status,
                dry_run,
                deployment.get("bucket_name"),
            )
        return 0
    
    # Handle show drift
    if args.show_drift:
        if not state_manager:
            state_manager = StateManager(args.state_file)
        
        drift = state_manager.detect_drift(config)
        if drift == ["No previous deployment found"]:
            _LOGGER.info("No previous deployment found - cannot detect drift")
        elif not drift:
            _LOGGER.info("No configuration drift detected")
        else:
            _LOGGER.warning("Configuration drift detected:")
            for change in drift:
                _LOGGER.warning("  - %s", change)
        return 0
    
    if config.dry_run:
        _LOGGER.info("Running in DRY-RUN mode - no changes will be made to AWS")

    credentials = _resolve_credentials(args)
    session_factory = SessionFactory(region=config.region, credentials=credentials)
    deployer = DataLakeDeployer(session_factory, state_manager=state_manager)

    summary = deployer.deploy(config)
    for resource, state in summary.items():
        _LOGGER.info("%s: %s", resource, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
