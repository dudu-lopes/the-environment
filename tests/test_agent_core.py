import unittest

from ment import (
    DEFAULT_H,
    Message,
    create_identity,
    derive_id,
    verify_identity,
    verify_signature,
)


class IdentityTests(unittest.TestCase):
    def test_identity_uses_a_random_public_key(self) -> None:
        first = create_identity("same password")
        second = create_identity("same password")
        self.assertNotEqual(first.id, second.id)
        self.assertTrue(verify_identity(first.id, first.public_key))
        self.assertTrue(verify_identity(second.id, second.public_key))

    def test_identity_can_be_restored_from_bundle(self) -> None:
        identity = create_identity("private password")
        restored = type(identity).from_bundle(identity.bundle())
        self.assertEqual(restored.public, identity.public)
        signature = restored.sign({"action": "test"}, "private password")
        self.assertTrue(verify_signature(identity.public_key, {"action": "test"}, signature))

    def test_wrong_password_cannot_sign(self) -> None:
        identity = create_identity("private password")
        with self.assertRaises(ValueError):
            identity.sign("data", "wrong password")

    def test_unlocked_identity_signs_without_repeating_password(self) -> None:
        identity = create_identity("private password")
        unlocked = identity.unlock("private password")
        first = unlocked.sign({"sequence": 1})
        second = unlocked.sign({"sequence": 2})
        self.assertTrue(verify_signature(identity.public_key, {"sequence": 1}, first))
        self.assertTrue(verify_signature(identity.public_key, {"sequence": 2}, second))

    def test_signature_rejects_changed_data(self) -> None:
        identity = create_identity("private password")
        signature = identity.sign({"amount": 10}, "private password")
        self.assertTrue(verify_signature(identity.public_key, {"amount": 10}, signature))
        self.assertFalse(verify_signature(identity.public_key, {"amount": 11}, signature))

    def test_protocol_base_changes_identity(self) -> None:
        identity = create_identity("same secret")
        self.assertNotEqual(derive_id(identity.public_key, DEFAULT_H), derive_id(identity.public_key, "another-public-base"))


class MessageTests(unittest.TestCase):
    def test_message_keeps_agent_defined_content_and_time(self) -> None:
        message = Message("agent-a", {"action": "anything"}, t=100)
        self.assertEqual(message.to_dict(), {
            "source_id": "agent-a",
            "target_id": None,
            "content": {"action": "anything"},
            "t": 100,
            "signature": None,
        })

    def test_message_can_be_signed_and_verified(self) -> None:
        identity = create_identity("message password")
        unlocked = identity.unlock("message password")
        message = Message(identity.id, {"action": "anything"}, t=100)
        signed = message.sign(unlocked)
        self.assertTrue(signed.verify(identity.public_key))

    def test_target_is_optional(self) -> None:
        self.assertIsNone(Message("agent-a", "broadcast").target_id)


if __name__ == "__main__":
    unittest.main()
