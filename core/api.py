"""Minimal HTTP access to an in-memory Environment."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from urllib.parse import parse_qs, urlparse
from typing import Any

from .agent_core import Message
from .environment import Environment


MAX_BODY_BYTES = 1_000_000


class EnvironmentHTTPServer(ThreadingHTTPServer):
    """HTTP server that exposes one in-memory Environment instance."""

    def __init__(self, address: tuple[str, int], environment: Environment) -> None:
        super().__init__(address, EnvironmentRequestHandler)
        self.environment = environment


class EnvironmentRequestHandler(BaseHTTPRequestHandler):
    server: EnvironmentHTTPServer

    def _write(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._write(status, {"error": message})

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("invalid Content-Length") from None
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("request body is empty or too large")
        try:
            value = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("request body must be valid JSON") from None
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/discover":
                capability = query.get("capability", [None])[0]
                result = [presence.to_dict() for presence in self.server.environment.discover(capability)]
                self._write(200, {"agents": result})
                return
            if parsed.path == "/receive":
                agent_id = query.get("agent_id", [None])[0]
                if agent_id is None:
                    raise ValueError("agent_id is required")
                messages = self.server.environment.receive(agent_id)
                self._write(200, {"messages": [message.to_dict() for message in messages]})
                return
            self._error(404, "unknown endpoint")
        except (KeyError, ValueError) as error:
            self._error(400, str(error))

    def do_POST(self) -> None:  # noqa: N802
        try:
            data = self._read_json()
            environment = self.server.environment
            if self.path == "/join":
                presence = environment.join(
                    data["agent_id"],
                    data.get("capabilities", []),
                    data.get("metadata"),
                    data.get("ttl_ms"),
                    public_key=data.get("public_key"),
                )
                self._write(200, presence.to_dict())
                return
            if self.path == "/heartbeat":
                presence = environment.heartbeat(data["agent_id"])
                self._write(200, presence.to_dict())
                return
            if self.path == "/leave":
                environment.leave(data["agent_id"])
                self._write(200, {"left": data["agent_id"]})
                return
            if self.path == "/send":
                message = Message(
                    source_id=data["source_id"],
                    target_id=data.get("target_id"),
                    content=data.get("content"),
                    t=data.get("t", time.time_ns() // 1_000_000),
                    signature=data.get("signature"),
                )
                environment.send_message(message)
                self._write(200, message.to_dict())
                return
            self._error(404, "unknown endpoint")
        except KeyError as error:
            self._error(400, f"missing field: {error.args[0]}")
        except (TypeError, ValueError) as error:
            self._error(400, str(error))

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(
    environment: Environment | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> EnvironmentHTTPServer:
    """Create a server; call ``serve_forever`` to start it."""
    return EnvironmentHTTPServer((host, port), environment or Environment())


def serve(
    environment: Environment | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """Run the Environment API until interrupted."""
    server = create_server(environment, host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
