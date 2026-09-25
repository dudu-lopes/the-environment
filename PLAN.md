# The Environment (`the-ment`) - Plan

## Current status

The PyPI distribution is `the-ment`. The Python import package remains `ment`, so developers can install it and import the complete MVP from one namespace:

```bash
pip install the-ment
```

## Implemented

- Portable Ed25519 identities.
- Password-protected private keys.
- `UnlockedIdentity` for one password entry per agent session.
- Signed and verified messages.
- Temporary in-memory Environment.
- Presence, capabilities, discovery, heartbeat, and expiration.
- Direct and broadcast messages with optional `target_id`.
- Minimal JSON HTTP API.
- Public `ment` package namespace.
- Runnable examples and automated tests.

## Public API

```python
from ment import Environment, create_identity, Message, serve
```

## Files

- `ment/` - public package namespace.
- `core/` - implementation modules.
- `tests/` - automated tests.
- `examples/` - runnable examples.
- `README.md` - usage documentation.
- `the agent ID.md` - product specification.
- `pyproject.toml` - package metadata.

## Design decisions

- Keep the public API small and stable.
- Keep the Environment temporary and in memory.
- Keep agents responsible for message content and workflows.
- Use standard-library HTTP transport without a web framework.
- Do not add a database, UI, or application-specific marketplace logic to the core.

## Next steps

The MVP is complete. Only add these for a larger public deployment:

1. Rate limits and spam protection.
2. Key rotation and identity revocation.
3. Production key-storage policy.
4. Hosting and operational monitoring.

## Change log

### 2026-09-24

- Added the `ment` public package namespace.
- Updated examples and tests to use `ment` imports.
- Named the PyPI distribution `the-ment`; the Python import remains `ment`.
