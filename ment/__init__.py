"""Public API for The Environment (ment)."""

from .agent_core import (
    DEFAULT_H,
    AgentIdentity,
    Message,
    UnlockedIdentity,
    create_identity,
    derive_id,
    verify_identity,
    verify_signature,
)
from .api import create_server, serve
from .environment import Environment, Presence

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
