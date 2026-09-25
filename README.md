pip install the-ment

# The Environment

pip install the-ment

Portable, pseudonymous agent identities with Ed25519 cryptographic signatures.

A minimal protocol for secure agent discovery, authentication, and communication. Perfect for multi-agent systems, AI agents, and decentralized applications.

## Why The Environment?

- **Secure** - Ed25519 signatures, AES-GCM encryption, Scrypt KDF
- **Simple** - Small core with one cryptography dependency
- **Portable** - Export/import identities as bundles
- **Flexible** - Support any serializable Python data
- **Fast** - In-memory environment for real-time discovery

## Quick Start

```bash
pip install the-ment
```

### Create an Identity

```python
from ment import create_identity

identity = create_identity("my-password")
print(f"Agent ID: {identity.id}")
unlocked = identity.unlock("my-password")
```

### Sign and Verify

```python
from ment import create_identity, verify_signature

identity = create_identity("my-password")
unlocked = identity.unlock("my-password")
signature = unlocked.sign({"action": "transfer"})

is_valid = verify_signature(identity.public_key, {"action": "transfer"}, signature)
print(f"Valid: {is_valid}")  # True
```

### Multi-Agent Communication

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
POST /join
GET  /discover
POST /send
GET  /receive
POST /heartbeat
POST /leave
```

The API has no database or graphical interface. It exposes the same temporary
Environment through JSON so agents in different processes can communicate.

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

20/20 tests passing

## License

MIT
