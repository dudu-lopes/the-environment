import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ment import Message, create_identity, create_server


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


if __name__ == "__main__":
    unittest.main()
