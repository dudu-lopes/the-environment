import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ment import Message, PairingToken, connect, create_identity, create_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    @classmethod
    def request(cls, method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(
            cls.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read())

    def test_join_discover_and_leave(self) -> None:
        agent_id = "api-agent"
        self.request("POST", "/join", {"agent_id": agent_id, "capabilities": ["search"]})
        discovered = self.request("GET", "/discover?capability=search")
        self.assertEqual(discovered["agents"][0]["id"], agent_id)
        self.request("POST", "/leave", {"agent_id": agent_id})
        self.assertEqual(self.request("GET", "/discover?capability=search")["agents"], [])

    def test_health(self) -> None:
        self.assertEqual(self.request("GET", "/health"), {"status": "ok"})

    def test_signed_message_is_verified_and_delivered(self) -> None:
        sender = create_identity("api sender")
        receiver = create_identity("api receiver")
        self.request("POST", "/join", {"agent_id": sender.id, "public_key": sender.public_key})
        self.request("POST", "/join", {"agent_id": receiver.id, "public_key": receiver.public_key})
        signed = Message(sender.id, {"hello": "receiver"}, receiver.id, t=100).sign(
            sender.unlock("api sender")
        )
        self.request("POST", "/send", signed.to_dict())
        received = self.request("GET", f"/receive?agent_id={receiver.id}")
        self.assertEqual(received["messages"][0]["content"], {"hello": "receiver"})

    def test_invalid_signed_message_is_rejected(self) -> None:
        sender = create_identity("api sender invalid")
        receiver = create_identity("api receiver invalid")
        self.request("POST", "/join", {"agent_id": sender.id, "public_key": sender.public_key})
        self.request("POST", "/join", {"agent_id": receiver.id, "public_key": receiver.public_key})
        signed = Message(sender.id, {"value": 1}, receiver.id, t=100).sign(
            sender.unlock("api sender invalid")
        )
        payload = signed.to_dict()
        payload["content"] = {"value": 2}
        with self.assertRaises(HTTPError) as error:
            self.request("POST", "/send", payload)
        self.assertEqual(error.exception.code, 400)

    def test_client_connects_to_shared_environment(self) -> None:
        sender = create_identity("client sender")
        receiver = create_identity("client receiver")
        client = connect(self.base_url)
        client.join(sender.id, public_key=sender.public_key)
        client.join(receiver.id, public_key=receiver.public_key)
        message = Message(
            sender.id,
            {"hello": "client"},
            receiver.id,
            t=100,
        ).sign(sender.unlock("client sender"))
        client.send_message(message)
        received = client.receive(receiver.id)
        self.assertEqual(received[0].content, {"hello": "client"})
        self.assertTrue(received[0].verify(sender.public_key))

    def test_one_time_pairing_token_joins_without_password(self) -> None:
        issuer = create_identity("issuer password")
        token = PairingToken.create(issuer.unlock("issuer password"), "chatgpt")
        paired = connect(self.base_url).pair(token.encode(), capabilities=["chat"])
        self.assertTrue(paired["paired"])
        self.assertEqual(paired["pairing_name"], "chatgpt")
        with self.assertRaises(ValueError):
            connect(self.base_url).pair(token.encode())


if __name__ == "__main__":
    unittest.main()
