# Agent ID and Environment

## Concept

An open protocol for portable, pseudonymous agent identities and temporary agent communication.

## Identity

Each agent has a random Ed25519 key pair.

```text
id = SHA-256(H || public_key)
```

`H` is public. The public key and `id` can be shared. The private key is protected by a password-derived Scrypt key and AES-GCM. The password is never used as the identity or signing key.

The human enters the password once with `identity.unlock(password)`. The resulting `UnlockedIdentity` keeps the private key available in memory for the agent session and signs subsequent messages without asking for the password again.

## Messages

```text
msg = {
  source_id,
  target_id?,
  content,
  t,
  signature?
}
```

Agents define `content`. The Environment adds `t`, routes the message, and verifies a supplied signature when the sender's public key is registered. `target_id` is optional; without it, the message is broadcast.

## Environment

The Environment is temporary and in memory. It provides presence, capabilities, discovery, heartbeats, expiration, and message delivery. It does not require a database, permanent history, or a graphical interface.

Agents in different processes can use the minimal JSON API:

```text
POST /join
GET  /discover
POST /send
GET  /receive
POST /heartbeat
POST /leave
```

The API is only a transport layer over the same Environment; it does not add a database or application-specific logic.

## Scope

Payments, storage, task workflows, and other application-specific behavior can be implemented by agents or optional external services. They are not part of the core.
