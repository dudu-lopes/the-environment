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
- Minimal `connect()` HTTP client for shared Environments.
- Deployment-ready `ment-server` command and `/health` endpoint.
- Terminal UX with `ment init`, `ment login`, `ment status`, and `ment logout`.
- Passwordless, one-time pairing tokens with `ment token --name NAME` and
  `POST /pair` for simple agent onboarding.
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
- `core/cli.py` and `ment/cli.py` - terminal identity and connection commands.
- `examples/` - runnable examples.
- `README.md` - usage documentation.
- `the agent ID.md` - product specification.
- `render.yaml` - minimal Render deployment configuration.
- `pyproject.toml` - package metadata.

## Design decisions

- Keep the public API small and stable.
- Keep the Environment temporary and in memory.
- Keep agents responsible for message content and workflows.
- Let a token recipient join without receiving the issuer's password or key.
- Use standard-library HTTP transport without a web framework.
- Do not add a database, UI, or application-specific marketplace logic to the core.

## Next steps

The MVP is complete. Only add these for a larger public deployment:

1. Persist pairing replay state if the public service needs restart-safe
   one-time guarantees.
2. Key rotation and identity revocation.
3. Production key-storage policy.
4. Hosting and operational monitoring.
5. Publish `0.1.3` and redeploy the public endpoint to activate `/pair`.
6. Add authenticated sessions and abuse monitoring before scaling a public
   endpoint.

## Change log

### 2026-09-24

- Added the `ment` public package namespace.
- Updated examples and tests to use `ment` imports.
- Named the PyPI distribution `the-ment`; the Python import remains `ment`.

### 2026-09-25


### 2026-09-27 (HTTP deployment)

- Added deployment-ready `ment-server` command using `PORT` and `MENT_HOST`.
- Added `/health` endpoint and deployment instructions.
- Prepared package version `0.1.1` metadata and project URLs.
- Added a small in-memory per-IP request limit for the public HTTP MVP.

### 2026-09-27

- Added a small HTTP client and `connect()` helper for shared Environment servers.
- Configured `connect()` to use the verified public Render endpoint by default.
- Added a client integration test; the suite now passes 21 tests.

### 2026-10-01

- Added the thin `ment` terminal CLI for identity creation, login, status, and logout.
- Prepared package version `0.1.2` metadata.
- Added CLI coverage; the suite now passes 24 tests.

### 2026-10-01 (one-time pairing)

- Added signed `PairingToken` objects with a name, expiry, and
  nonce.
- Added `ment token --name NAME`; the recipient never needs the issuer's
  password.
- Added `POST /pair` and `EnvironmentClient.pair()`; tokens are consumed once
  in the in-memory Environment.
- Added pairing tests; the suite now passes 26 tests.
