import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ment import create_identity, create_server
from core.cli import main


class CliTests(unittest.TestCase):
    def test_init_writes_encrypted_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.json"
            with patch("core.cli.getpass.getpass", side_effect=["secret", "secret"]):
                self.assertEqual(main(["init", "--identity", str(path)]), 0)
            bundle = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("encrypted_private_key", bundle)
            self.assertNotIn("secret", path.read_text(encoding="utf-8"))

    def test_login_check_unlocks_and_connects(self) -> None:
        identity = create_identity("secret")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.json"
            path.write_text(json.dumps(identity.bundle()), encoding="utf-8")
            server = create_server(port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            host, port = server.server_address
            try:
                with patch("core.cli.getpass.getpass", return_value="secret"):
                    result = main(
                        [
                            "login",
                            "--identity",
                            str(path),
                            "--url",
                            f"http://{host}:{port}",
                            "--check",
                        ]
                    )
                self.assertEqual(result, 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
