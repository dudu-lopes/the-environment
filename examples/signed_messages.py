"""
Signed messages example demonstrating authentication.

This example demonstrates:
- Creating signed messages
- Verifying message authenticity
- Detecting tampered messages
- Using messages with the Environment
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ment import create_identity, verify_signature, Message, AgentIdentity

# Create two agents
alice = create_identity("alice-password")
bob = create_identity("bob-password")
alice_unlocked = alice.unlock("alice-password")

print("=== Creating Signed Message ===")
# Create a message from Alice
message = Message(
    source_id=alice.id,
    content={"action": "transfer", "amount": 100, "to": "bob"},
    target_id=bob.id
)

# Sign the message with Alice's identity
signed_message = message.sign(alice_unlocked)
print(f"Message: {signed_message.content}")
print(f"Signature: {signed_message.signature[:32]}...")
print()

print("=== Verifying Signature ===")
# Bob verifies the message came from Alice
is_authentic = signed_message.verify(alice.public_key)
print(f"Message is authentic: {is_authentic}")
print()

print("=== Detecting Tampering ===")
# Someone tries to tamper with the message
tampered_data = {"action": "transfer", "amount": 1000, "to": "bob"}  # Changed amount!
is_tampered_valid = verify_signature(alice.public_key, tampered_data, signed_message.signature)
print(f"Tampered message valid: {is_tampered_valid}")
print()

print("=== Wrong Source ID ===")
# Try to sign a message with wrong source_id
wrong_message = Message(
    source_id=bob.id,  # Wrong source
    content={"action": "transfer", "amount": 100, "to": "bob"},
)
try:
    wrong_message.sign(alice_unlocked)
    print("ERROR: Should have raised ValueError")
except ValueError as e:
    print(f"Correctly rejected: {e}")
print()

print("=== Portable Identity Bundles ===")
# Export and import identities
bundle = alice.bundle()
print(f"Bundle keys: {list(bundle.keys())}")

# Later, on another machine or process:
restored_alice = AgentIdentity.from_bundle(bundle)
restored_alice_unlocked = restored_alice.unlock("alice-password")
new_signature = restored_alice_unlocked.sign({"data": "from restored"})
is_restored_valid = verify_signature(restored_alice.public_key, {"data": "from restored"}, new_signature)
print(f"Restored identity signature valid: {is_restored_valid}")
