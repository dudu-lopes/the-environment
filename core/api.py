"""Minimal HTTP access to an in-memory Environment."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
from typing import Any

from .agent_core import Message
from .environment import Environment


MAX_BODY_BYTES = 1_000_000
DEFAULT_TIMEOUT = 10.0
DEFAULT_ENVIRONMENT_URL = "https://the-environment.onrender.com"
RATE_WINDOW_SECONDS = 60.0
RATE_LIMIT_REQUESTS = 120


class EnvironmentHTTPServer(ThreadingHTTPServer):
    """HTTP server that exposes one in-memory Environment instance."""

    def __init__(self, address: tuple[str, int], environment: Environment) -> None:
        super().__init__(address, EnvironmentRequestHandler)
        self.environment = environment


class EnvironmentRequestHandler(BaseHTTPRequestHandler):
    server: EnvironmentHTTPServer
    _rate_lock = threading.Lock()
    _rate_state: dict[str, tuple[float, int]] = {}

    def _rate_limited(self) -> bool:
        address = self.client_address[0]
        current = time.monotonic()
        with self._rate_lock:
            started, count = self._rate_state.get(address, (current, 0))
            if current - started >= RATE_WINDOW_SECONDS:
                started, count = current, 0
            count += 1
            self._rate_state[address] = (started, count)
            limited = count > RATE_LIMIT_REQUESTS
        if limited:
            self._error(429, "rate limit exceeded")
        return limited

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
        if self._rate_limited():
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/health":
                self._write(200, {"status": "ok"})
                return
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
        if self._rate_limited():
            return
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


def run() -> None:
    """Run the HTTP service using deployment-friendly environment variables."""
    host = os.getenv("MENT_HOST", "0.0.0.0")
    raw_port = os.getenv("PORT", os.getenv("MENT_PORT", "8765"))
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("PORT must be an integer") from error
    serve(host=host, port=port)


class EnvironmentClient:
    """Small HTTP client for a shared Environment server."""

    def __init__(self, url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        parsed = urlparse(url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute http or https URL")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"} if body is not None else {}
        request = Request(self.url + path, data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                value = json.loads(response.read())
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("error", str(error))
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = str(error)
            raise ValueError(detail) from error
        except URLError as error:
            raise ConnectionError(f"could not reach Environment at {self.url}") from error
        if not isinstance(value, dict):
            raise ValueError("Environment returned an invalid response")
        return value

    def join(
        self,
        agent_id: str,
        capabilities: list[str] | tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        ttl_ms: int | None = None,
        public_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "capabilities": list(capabilities),
        }
        if metadata is not None:
            payload["metadata"] = metadata
        if ttl_ms is not None:
            payload["ttl_ms"] = ttl_ms
        if public_key is not None:
            payload["public_key"] = public_key
        return self._request("POST", "/join", payload)

    def discover(self, capability: str | None = None) -> list[dict[str, Any]]:
        path = "/discover"
        if capability is not None:
            path += f"?capability={quote(capability)}"
        return self._request("GET", path).get("agents", [])

    def send_message(self, message: Message) -> Message:
        data = self._request("POST", "/send", message.to_dict())
        return Message(
            source_id=data["source_id"],
            target_id=data.get("target_id"),
            content=data.get("content"),
            t=data["t"],
            signature=data.get("signature"),
        )

    def receive(self, agent_id: str) -> list[Message]:
        data = self._request("GET", f"/receive?agent_id={quote(agent_id)}")
        return [
            Message(
                source_id=item["source_id"],
                target_id=item.get("target_id"),
                content=item.get("content"),
                t=item["t"],
                signature=item.get("signature"),
            )
            for item in data.get("messages", [])
        ]

    def heartbeat(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", "/heartbeat", {"agent_id": agent_id})

    def leave(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", "/leave", {"agent_id": agent_id})


def connect(url: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> EnvironmentClient:
    """Connect to a shared Environment URL.

    If ``url`` is omitted, ``MENT_ENVIRONMENT_URL`` overrides the public
    default. The default is the official The Environment endpoint.
    """
    endpoint = url or os.getenv("MENT_ENVIRONMENT_URL", DEFAULT_ENVIRONMENT_URL)
    return EnvironmentClient(endpoint, timeout)
