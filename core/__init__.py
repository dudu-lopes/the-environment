"""Agent ID - Portable, pseudonymous agent identities with Ed25519 signatures."""

from core.agent_core import (
    DEFAULT_H,
    AgentIdentity,
    Message,
    UnlockedIdentity,
    create_identity,
    derive_id,
    verify_identity,
    verify_signature,
)

from core.environment import Environment, Presence
from core.api import DEFAULT_ENVIRONMENT_URL, EnvironmentClient, connect, create_server, run, serve

__all__ = [
    "DEFAULT_H",
    "AgentIdentity",
    "Message",
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

__version__ = "0.1.1"
