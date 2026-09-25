"""
Basic usage example for Agent ID.

This example demonstrates:
- Creating a new agent identity
- Signing a message
- Verifying a signature
- Exporting and importing an identity bundle
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ment import create_identity, verify_signature, Message

# Create a new agent identity with a password
identity = create_identity("my-secure-password")
unlocked = identity.unlock("my-secure-password")

print(f"Agent ID: {identity.id}")
print(f"Public Key: {identity.public_key[:32]}...")
print()

# Sign a message
message_data = {"action": "greet", "target": "world"}
signature = unlocked.sign(message_data)

print(f"Message: {message_data}")
print(f"Signature: {signature[:32]}...")
print()

# Verify the signature
is_valid = verify_signature(identity.public_key, message_data, signature)
print(f"Signature valid: {is_valid}")
print()

# Export identity bundle
bundle = identity.bundle()
print(f"Identity bundle contains: {list(bundle.keys())}")
print()

# Import identity from bundle
from ment import AgentIdentity
restored_identity = AgentIdentity.from_bundle(bundle)

# Verify restored identity works
restored_unlocked = restored_identity.unlock("my-secure-password")
restored_signature = restored_unlocked.sign(message_data)
is_valid_restored = verify_signature(restored_identity.public_key, message_data, restored_signature)
print(f"Restored identity signature valid: {is_valid_restored}")
