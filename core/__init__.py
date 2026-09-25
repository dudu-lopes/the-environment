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
from core.api import create_server, serve

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
    "create_server",
    "serve",
]

__version__ = "0.1.0"
