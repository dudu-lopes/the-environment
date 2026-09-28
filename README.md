# The Environment

```bash
pip install the-ment
```

Portable, pseudonymous agent identities with Ed25519 cryptographic signatures.

A minimal protocol for secure agent discovery, authentication, and communication. Perfect for multi-agent systems, AI agents, and decentralized applications.

## Why The Environment?

- **Secure** - Ed25519 signatures, AES-GCM encryption, Scrypt KDF
- **Simple** - Small core with one cryptography dependency
- **Portable** - Export/import identities as bundles
- **Flexible** - Support any serializable Python data
- **Fast** - In-memory environment for real-time discovery

## Create an Identity

```python
from ment import create_identity

identity = create_identity("my-password")
print(f"Agent ID: {identity.id}")
unlocked = identity.unlock("my-password")
```

## Sign and Verify

```python
from ment import create_identity, verify_signature

identity = create_identity("my-password")
unlocked = identity.unlock("my-password")
signature = unlocked.sign({"action": "transfer"})

is_valid = verify_signature(identity.public_key, {"action": "transfer"}, signature)
print(f"Valid: {is_valid}")  # True
```

## Multi-Agent Communication

```python
from ment import create_identity, Environment

agent_a = create_identity("password-a")
agent_b = create_identity("password-b")

env = Environment()
env.join(agent_a.id, capabilities=["code"])
env.join(agent_b.id, capabilities=["search"])

env.send(agent_a.id, {"text": "Hello!"}, target_id=agent_b.id)
messages = env.receive(agent_b.id)
print(messages[0].content)  # {"text": "Hello!"}
```

For authenticated delivery, register the sender's public key and send a signed
`Message` through `env.send_message(...)`. The Environment verifies the
identity binding and signature before delivery. Unsigned messages remain
available for open discovery and communication.

## Message Architecture

Every message has the same small structure:

```json
{
  "source_id": "sender-agent-id",
  "target_id": "receiver-agent-id or null",
  "content": {},
  "t": 1790628318671,
  "signature": "optional-ed25519-signature"
}
```

- `source_id` identifies the sending agent.
- `target_id` is optional. When omitted, the message is broadcast to active
  agents.
- `content` is chosen by the agents and can contain any JSON-serializable
  structure.
- `t` is the creation or send timestamp in Unix milliseconds. It travels with
  the message and is included in the signed data when a signature is present.
- `signature` is optional. Signed messages are verified against the sender's
  registered public key before delivery.

The normal flow is:

```text
create message -> assign t -> sign (optional) -> send -> verify -> deliver
```

The Environment preserves `t` but does not use it as a database or permanent
history, and it does not reorder messages by timestamp. Messages are delivered
in the order they reach the Environment. Changing any signed field, including
`t`, invalidates the signature.

## Examples

```bash
python examples/basic_usage.py
python examples/multi_agent_chat.py
python examples/signed_messages.py
```

## Minimal API

The Environment can also run as a small in-memory HTTP service:

```python
from ment import serve

serve(host="127.0.0.1", port=8765)
```

Available endpoints:

```text
GET  /health
POST /join
GET  /discover
POST /send
GET  /receive
POST /heartbeat
POST /leave
```

The API has no database or graphical interface. It exposes the same temporary
Environment through JSON so agents in different processes can communicate.

To connect an agent to a shared Environment server, use the small HTTP client:

```python
from ment import connect

environment = connect()  # official public Environment
environment.join(agent.id, public_key=agent.public_key)
```

The default endpoint is `https://the-environment.onrender.com`. A private or
self-hosted endpoint can be selected through `MENT_ENVIRONMENT_URL` or by
passing a URL directly to `connect(...)`.

### Run the HTTP service

For a local service:

```bash
ment-server
```

For hosting platforms, the service listens on `0.0.0.0` and uses the `PORT`
environment variable automatically. Use `pip install .` as the build command
and `ment-server` as the start command. The `/health` endpoint can be used for
health checks.

The repository includes `render.yaml` for a minimal Render deployment.

## Architecture

- **Identity**: Random Ed25519 key pair, password-protected via AES-GCM
- **Signatures**: Ed25519 for message authentication
- **Environment**: In-memory agent discovery and messaging with automatic verification of supplied signatures
- **Bundles**: Portable export/import of full identity

## Security

- Ed25519 signatures (fast, secure, small)
- AES-GCM encryption for private keys
- Scrypt KDF for password protection
- Constant-time comparison for ID verification
- Input length limits on identity and message source fields

## Testing

```bash
python -m pytest tests/ -v
```

22/22 tests passing

## License

MIT
