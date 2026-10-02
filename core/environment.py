"""Small, in-memory and temporary Environment for agents."""

from __future__ import annotations

from dataclasses import dataclass
import time
import threading
from typing import Any

from core.agent_core import Message, PairingToken, verify_identity
import secrets


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class Presence:
    """Temporary public presence information for an active agent."""

    agent_id: str
    capabilities: tuple[str, ...]
    metadata: dict[str, Any]
    last_seen: int
    expires_at: int
    public_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.agent_id,
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
            "last_seen": self.last_seen,
            "expires_at": self.expires_at,
            "public_key": self.public_key,
        }


class Environment:
    """Ephemeral agent space with presence, discovery, and message delivery.

    The environment keeps only active presence and undelivered messages. It
    does not provide a database or permanent event history.
    """

    def __init__(self, default_ttl_ms: int = 30_000) -> None:
        if default_ttl_ms <= 0:
            raise ValueError("default_ttl_ms must be positive")
        self.default_ttl_ms = default_ttl_ms
        self._agents: dict[str, Presence] = {}
        self._mailboxes: dict[str, list[Message]] = {}
        self._used_pairings: set[str] = set()
        self._pairing_lock = threading.Lock()

    def _prune(self, now: int) -> None:
        expired = [agent_id for agent_id, p in self._agents.items() if p.expires_at <= now]
        for agent_id in expired:
            self._agents.pop(agent_id, None)
            self._mailboxes.pop(agent_id, None)

    def join(
        self,
        agent_id: str,
        capabilities: list[str] | tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        ttl_ms: int | None = None,
        now: int | None = None,
        public_key: str | None = None,
    ) -> Presence:
        agent_id = _text(agent_id, "agent_id")
        if any(not isinstance(item, str) or not item for item in capabilities):
            raise ValueError("capabilities must contain non-empty strings")
        ttl = self.default_ttl_ms if ttl_ms is None else ttl_ms
        if ttl <= 0:
            raise ValueError("ttl_ms must be positive")
        if public_key is not None and not verify_identity(agent_id, public_key):
            raise ValueError("public_key does not match agent_id")
        current = _now_ms() if now is None else now
        self._prune(current)
        presence = Presence(
            agent_id=agent_id,
            capabilities=tuple(sorted(set(capabilities))),
            metadata=dict(metadata or {}),
            last_seen=current,
            expires_at=current + ttl,
            public_key=public_key,
        )
        self._agents[agent_id] = presence
        self._mailboxes.setdefault(agent_id, [])
        return presence

    def heartbeat(self, agent_id: str, now: int | None = None) -> Presence:
        current = _now_ms() if now is None else now
        self._prune(current)
        existing = self._agents.get(_text(agent_id, "agent_id"))
        if existing is None:
            raise KeyError("agent is not active")
        return self.join(
            existing.agent_id,
            existing.capabilities,
            existing.metadata,
            existing.expires_at - existing.last_seen,
            current,
            existing.public_key,
        )

    def leave(self, agent_id: str) -> None:
        agent_id = _text(agent_id, "agent_id")
        self._agents.pop(agent_id, None)
        self._mailboxes.pop(agent_id, None)

    def discover(self, capability: str | None = None, now: int | None = None) -> list[Presence]:
        current = _now_ms() if now is None else now
        self._prune(current)
        if capability is not None:
            _text(capability, "capability")
        result = [
            presence
            for presence in self._agents.values()
            if capability is None or capability in presence.capabilities
        ]
        return sorted(result, key=lambda presence: presence.agent_id)

    def send(
        self,
        source_id: str,
        content: Any,
        target_id: str | None = None,
        now: int | None = None,
        signature: str | None = None,
    ) -> Message:
        """Deliver a direct message or broadcast when target_id is omitted."""
        current = _now_ms() if now is None else now
        self._prune(current)
        source_id = _text(source_id, "source_id")
        if source_id not in self._agents:
            raise KeyError("source agent is not active")
        if target_id is not None:
            target_id = _text(target_id, "target_id")
            if target_id not in self._agents:
                raise KeyError("target agent is not active")
        message = Message(
            source_id=source_id,
            target_id=target_id,
            content=content,
            t=current,
            signature=signature,
        )
        return self.send_message(message, now=current)

    def send_message(self, message: Message, now: int | None = None) -> Message:
        """Verify a signed message, then deliver it to its recipients."""
        current = _now_ms() if now is None else now
        self._prune(current)
        source_id = _text(message.source_id, "source_id")
        source = self._agents.get(source_id)
        if source is None:
            raise KeyError("source agent is not active")
        if message.signature is not None:
            if source.public_key is None:
                raise ValueError("signed messages require the source public key")
            if not message.verify(source.public_key):
                raise ValueError("invalid message signature")
        target_id = message.target_id
        if target_id is not None:
            target_id = _text(target_id, "target_id")
            if target_id not in self._agents:
                raise KeyError("target agent is not active")
        recipients = [target_id] if target_id else list(self._agents)
        for recipient in recipients:
            if recipient != source_id and recipient in self._mailboxes:
                self._mailboxes[recipient].append(message)
        return message

    def receive(self, agent_id: str, now: int | None = None) -> list[Message]:
        current = _now_ms() if now is None else now
        self._prune(current)
        agent_id = _text(agent_id, "agent_id")
        if agent_id not in self._agents:
            raise KeyError("agent is not active")
        messages = self._mailboxes[agent_id]
        self._mailboxes[agent_id] = []
        return messages

    def pair(
        self,
        token: PairingToken,
        agent_id: str | None = None,
        capabilities: list[str] | tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        public_key: str | None = None,
        now: int | None = None,
    ) -> Presence:
        """Consume a one-time pairing token and join an agent.

        The recipient does not need the issuer's password. It may provide its
        own public key for signed messages; otherwise the server creates a
        temporary session ID for simple integrations.
        """
        current = _now_ms() if now is None else now
        if not token.verify(current // 1000):
            raise ValueError("pairing token is invalid or expired")
        if agent_id is None:
            agent_id = f"agent-{secrets.token_urlsafe(12)}"
        else:
            agent_id = _text(agent_id, "agent_id")
        if public_key is not None and not verify_identity(agent_id, public_key):
            raise ValueError("public_key does not match agent_id")
        pair_metadata = dict(metadata or {})
        pair_metadata.setdefault("paired_by", token.issuer_id)
        pair_metadata.setdefault("pairing_name", token.name)
        with self._pairing_lock:
            if token.nonce in self._used_pairings:
                raise ValueError("pairing token has already been used")
            presence = self.join(
                agent_id,
                capabilities,
                pair_metadata,
                public_key=public_key,
                now=current,
            )
            self._used_pairings.add(token.nonce)
            return presence
