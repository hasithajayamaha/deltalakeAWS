"""State management for tracking deployed resources and detecting drift."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import DataLakeConfig
from .exceptions import DataLakeError

_LOGGER = logging.getLogger(__name__)


class StateManager:
    """
    Manages deployment state for tracking resources and detecting drift.
    
    Stores information about deployed resources to enable:
    - Drift detection (manual changes to resources)
    - Rollback capabilities
    - Deployment history
    - Resource tracking
    """

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to state file. Defaults to .datalake-state.json
        """
        self.state_file = state_file or Path(".datalake-state.json")
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or return empty state."""
        if self.state_file.exists():
            try:
                content = self.state_file.read_text(encoding="utf-8")
                return json.loads(content)
            except (json.JSONDecodeError, IOError) as exc:
                _LOGGER.warning("Failed to load state file: %s", exc)
                return self._empty_state()
        return self._empty_state()

    def _empty_state(self) -> Dict[str, Any]:
        """Return empty state structure."""
        return {
            "version": "1.0",
            "deployments": [],
            "current_config": {},
            "resources": {},
        }

    def save_deployment(
        self,
        config: DataLakeConfig,
        resources: Dict[str, str],
        success: bool = True,
    ) -> None:
        """
        Save deployment information to state.
        
        Args:
            config: Configuration used for deployment
            resources: Dictionary of resource names to their status
            success: Whether deployment was successful
        """
        deployment = {
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "region": config.region,
            "bucket_name": config.bucket_name,
            "glue_database": config.glue_database,
            "resources": resources,
            "dry_run": config.dry_run,
        }

        # Add to deployment history
        self.state["deployments"].append(deployment)

        # Keep only last 10 deployments
        if len(self.state["deployments"]) > 10:
            self.state["deployments"] = self.state["deployments"][-10:]

        # Update current config if successful and not dry-run
        if success and not config.dry_run:
            self.state["current_config"] = {
                "region": config.region,
                "bucket_name": config.bucket_name,
                "glue_database": config.glue_database,
                "raw_prefix": config.raw_prefix,
                "processed_prefix": config.processed_prefix,
                "analytics_prefix": config.analytics_prefix,
                "table_format": config.table_format,
                "kms_key_id": config.kms_key_id,
                "crawler_name": config.crawler_name,
                "athena_workgroup": config.athena_workgroup,
                "tags": config.tags,
            }
            self.state["resources"] = resources

        self._save_state()

    def _save_state(self) -> None:
        """Save state to file."""
        try:
            self.state_file.write_text(
                json.dumps(self.state, indent=2),
                encoding="utf-8"
            )
            _LOGGER.debug("State saved to %s", self.state_file)
        except IOError as exc:
            _LOGGER.error("Failed to save state file: %s", exc)

    def detect_drift(self, config: DataLakeConfig) -> List[str]:
        """
        Detect configuration drift from last successful deployment.
        
        Args:
            config: Current configuration to compare
            
        Returns:
            List of drift descriptions
        """
        if not self.state.get("current_config"):
            return ["No previous deployment found"]

        drift = []
        current = self.state["current_config"]

        # Check for configuration changes
        if current.get("region") != config.region:
            drift.append(f"Region changed: {current.get('region')} → {config.region}")

        if current.get("bucket_name") != config.bucket_name:
            drift.append(
                f"Bucket name changed: {current.get('bucket_name')} → {config.bucket_name}"
            )

        if current.get("glue_database") != config.glue_database:
            drift.append(
                f"Database changed: {current.get('glue_database')} → {config.glue_database}"
            )

        if current.get("table_format") != config.table_format:
            drift.append(
                f"Table format changed: {current.get('table_format')} → {config.table_format}"
            )

        if current.get("kms_key_id") != config.kms_key_id:
            drift.append(
                f"KMS key changed: {current.get('kms_key_id')} → {config.kms_key_id}"
            )

        # Check prefix changes
        for prefix_name in ["raw_prefix", "processed_prefix", "analytics_prefix"]:
            old_val = current.get(prefix_name)
            new_val = getattr(config, prefix_name)
            if old_val != new_val:
                drift.append(f"{prefix_name} changed: {old_val} → {new_val}")

        # Check tag changes
        old_tags = current.get("tags", {})
        new_tags = config.tags
        if old_tags != new_tags:
            added = set(new_tags.keys()) - set(old_tags.keys())
            removed = set(old_tags.keys()) - set(new_tags.keys())
            changed = {
                k for k in set(old_tags.keys()) & set(new_tags.keys())
                if old_tags[k] != new_tags[k]
            }

            if added:
                drift.append(f"Tags added: {', '.join(added)}")
            if removed:
                drift.append(f"Tags removed: {', '.join(removed)}")
            if changed:
                drift.append(f"Tags changed: {', '.join(changed)}")

        return drift

    def get_deployment_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get deployment history.
        
        Args:
            limit: Maximum number of deployments to return
            
        Returns:
            List of deployment records
        """
        deployments = self.state.get("deployments", [])
        return deployments[-limit:]

    def get_last_successful_deployment(self) -> Optional[Dict[str, Any]]:
        """Get the last successful deployment."""
        for deployment in reversed(self.state.get("deployments", [])):
            if deployment.get("success") and not deployment.get("dry_run"):
                return deployment
        return None

    def clear_state(self) -> None:
        """Clear all state (use with caution)."""
        self.state = self._empty_state()
        self._save_state()
        _LOGGER.info("State cleared")


__all__ = ["StateManager"]
