"""Public API for The Environment (ment)."""

from .agent_core import (
    DEFAULT_H,
    AgentIdentity,
    Message,
    PairingToken,
    UnlockedIdentity,
    create_identity,
    derive_id,
    verify_identity,
    verify_signature,
)
from .api import DEFAULT_ENVIRONMENT_URL, EnvironmentClient, connect, create_server, run, serve
from .environment import Environment, Presence

__all__ = [
    "DEFAULT_H",
    "AgentIdentity",
    "Message",
    "PairingToken",
    "UnlockedIdentity",
    "create_identity",
    "derive_id",
    "verify_identity",
    "verify_signature",
    "Environment",
    "Presence",
    "EnvironmentClient",
    "DEFAULT_ENVIRONMENT_URL",
    "connect",
    "create_server",
    "run",
    "serve",
]

__version__ = "0.1.3"
