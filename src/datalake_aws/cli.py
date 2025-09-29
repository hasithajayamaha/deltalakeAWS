"""Command line entry point for deploying the data lake."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from .config import AwsCredentials, DataLakeConfig
from .deployer import DataLakeDeployer
from .sessions import SessionFactory

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

    credentials = _resolve_credentials(args)
    session_factory = SessionFactory(region=config.region, credentials=credentials)
    deployer = DataLakeDeployer(session_factory)

    summary = deployer.deploy(config)
    for resource, state in summary.items():
        _LOGGER.info("%s: %s", resource, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
