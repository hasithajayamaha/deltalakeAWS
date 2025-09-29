"""Helpers for building boto3 sessions and clients."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from .config import AwsCredentials


@dataclass
class SessionFactory:
    """Factory responsible for creating boto3 sessions and service clients."""

    region: str
    credentials: Optional[AwsCredentials] = None
    boto_config: Optional[BotoConfig] = None

    def __post_init__(self) -> None:
        self._session: Optional[boto3.Session] = None

    def create_session(self) -> boto3.Session:
        """Return a cached boto3 Session using the provided credentials."""
        if self._session is None:
            kwargs = {"region_name": self.region}
            if self.credentials:
                kwargs.update(self.credentials.as_dict())
            self._session = boto3.Session(**kwargs)
        return self._session

    def client(self, service_name: str):
        """Return a boto3 client for the given service using the shared session."""
        session = self.create_session()
        extra = {}
        if self.boto_config is not None:
            extra["config"] = self.boto_config
        return session.client(service_name, **extra)

    def resource(self, service_name: str):
        """Return a boto3 resource interface for the given service."""
        session = self.create_session()
        return session.resource(service_name)


__all__ = ["SessionFactory"]
