import unittest

from ment import Environment, Message, create_identity


class EnvironmentTests(unittest.TestCase):
    def test_presence_and_capability_discovery(self) -> None:
        environment = Environment(default_ttl_ms=100)
        environment.join("agent-b", ["search"], now=1000)
        environment.join("agent-a", ["code", "search"], now=1000)

        found = environment.discover("search", now=1050)
        self.assertEqual([presence.agent_id for presence in found], ["agent-a", "agent-b"])
        self.assertEqual(environment.discover("missing", now=1050), [])

    def test_presence_expires_without_heartbeat(self) -> None:
        environment = Environment(default_ttl_ms=100)
        environment.join("agent-a", now=1000)
        self.assertEqual(len(environment.discover(now=1099)), 1)
        self.assertEqual(len(environment.discover(now=1100)), 0)

    def test_heartbeat_extends_presence(self) -> None:
        environment = Environment(default_ttl_ms=100)
        environment.join("agent-a", now=1000)
        environment.heartbeat("agent-a", now=1050)
        self.assertEqual(len(environment.discover(now=1149)), 1)
        self.assertEqual(len(environment.discover(now=1150)), 0)

    def test_messages_are_delivered_and_not_stored_as_history(self) -> None:
        environment = Environment()
        environment.join("agent-a", now=1000)
        environment.join("agent-b", now=1000)
        message = environment.send("agent-a", {"text": "hello"}, "agent-b", now=1001)

        received = environment.receive("agent-b", now=1002)
        self.assertEqual([item.content for item in received], [{"text": "hello"}])
        self.assertEqual(received[0].t, 1001)
        self.assertEqual(environment.receive("agent-b", now=1003), [])

    def test_broadcast_does_not_return_to_sender(self) -> None:
        environment = Environment()
        environment.join("agent-a", now=1000)
        environment.join("agent-b", now=1000)
        environment.join("agent-c", now=1000)
        environment.send("agent-a", "announcement", now=1001)

        self.assertEqual(len(environment.receive("agent-a", now=1002)), 0)
        self.assertEqual(len(environment.receive("agent-b", now=1002)), 1)
        self.assertEqual(len(environment.receive("agent-c", now=1002)), 1)

    def test_environment_verifies_signed_messages(self) -> None:
        sender = create_identity("sender password")
        receiver = create_identity("receiver password")
        environment = Environment()
        environment.join(sender.id, public_key=sender.public_key, now=1000)
        environment.join(receiver.id, public_key=receiver.public_key, now=1000)
        message = Message(sender.id, {"text": "signed"}, receiver.id, t=1001)
        signed = message.sign(sender, "sender password")

        environment.send_message(signed, now=1001)
        received = environment.receive(receiver.id, now=1002)
        self.assertEqual(received, [signed])

    def test_environment_rejects_invalid_signed_messages(self) -> None:
        sender = create_identity("sender password")
        receiver = create_identity("receiver password")
        environment = Environment()
        environment.join(sender.id, public_key=sender.public_key, now=1000)
        environment.join(receiver.id, public_key=receiver.public_key, now=1000)
        message = Message(sender.id, {"text": "signed"}, receiver.id, t=1001)
        signed = message.sign(sender, "sender password")
        tampered = Message(
            signed.source_id,
            {"text": "tampered"},
            signed.target_id,
            signed.t,
            signed.signature,
        )

        with self.assertRaises(ValueError):
            environment.send_message(tampered, now=1001)

    def test_join_rejects_a_mismatched_public_key(self) -> None:
        identity = create_identity("password")
        other = create_identity("other password")
        environment = Environment()
        with self.assertRaises(ValueError):
            environment.join(identity.id, public_key=other.public_key, now=1000)


if __name__ == "__main__":
    unittest.main()
