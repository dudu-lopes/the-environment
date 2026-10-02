"""Small terminal UX for local agent identities and Environment sessions."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path
import sys
import time
from typing import Sequence

from .agent_core import AgentIdentity, PairingToken, create_identity
from .api import connect


DEFAULT_IDENTITY_PATH = Path.home() / ".ment" / "identity.json"


def _path(value: str | None) -> Path:
    return Path(value).expanduser() if value else DEFAULT_IDENTITY_PATH


def _load_identity(path: Path) -> AgentIdentity:
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"identity not found: {path}. Run 'ment init' first") from None
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read identity: {path}") from error
    if not isinstance(bundle, dict):
        raise ValueError("identity file must contain a JSON object")
    return AgentIdentity.from_bundle(bundle)


def _save_identity(identity: AgentIdentity, path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise ValueError(f"identity already exists: {path} (use --force to replace it)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(identity.bundle(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _password_confirmation() -> str:
    password = getpass.getpass("Password: ")
    if not password:
        raise ValueError("password cannot be empty")
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("passwords do not match")
    return password


def _init(args: argparse.Namespace) -> int:
    path = _path(args.identity)
    identity = create_identity(_password_confirmation())
    _save_identity(identity, path, args.force)
    print("Identity created successfully.")
    print(f"Agent ID: {identity.id}")
    print(f"Saved to: {path}")
    return 0


def _login(args: argparse.Namespace) -> int:
    path = _path(args.identity)
    identity = _load_identity(path)
    unlocked = identity.unlock(getpass.getpass("Password: "))
    environment = connect(args.url)
    environment.join(identity.id, args.capability, public_key=identity.public_key)
    print("Identity unlocked.")
    print(f"Agent ID: {identity.id}")
    print(f"Connected to: {environment.url}")
    if args.check:
        environment.leave(identity.id)
        print("Connection verified.")
        return 0

    print("Agent is active. Press Ctrl+C to disconnect.")
    try:
        while True:
            for message in environment.receive(identity.id):
                print(json.dumps(message.to_dict(), ensure_ascii=False))
            environment.heartbeat(identity.id)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        environment.leave(identity.id)
    print("Disconnected.")
    return 0


def _status(args: argparse.Namespace) -> int:
    path = _path(args.identity)
    identity = _load_identity(path)
    environment = connect(args.url)
    active = any(item.get("id") == identity.id for item in environment.discover())
    print(f"Identity: valid")
    print(f"Agent ID: {identity.id}")
    print(f"Environment: {environment.url}")
    print(f"Presence: {'active' if active else 'offline'}")
    return 0


def _logout(args: argparse.Namespace) -> int:
    identity = _load_identity(_path(args.identity))
    environment = connect(args.url)
    try:
        environment.leave(identity.id)
    except (KeyError, ValueError):
        pass
    print(f"Agent {identity.id} disconnected.")
    return 0


def _token(args: argparse.Namespace) -> int:
    """Create a passwordless, single-use invitation for another agent."""
    name = args.name or args.token_name
    if not name:
        raise ValueError("token name is required (use --name NAME)")
    identity = _load_identity(_path(args.identity))
    unlocked = identity.unlock(getpass.getpass("Password: "))
    token = PairingToken.create(
        unlocked,
        name,
        ttl_seconds=args.expires,
    )
    print("Give this token to the agent once. It expires and cannot be reused:")
    print(token.encode())
    print(f"Name: {token.name}")
    print(f"Expires in: {args.expires}s")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ment", description="The Environment agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a local encrypted agent identity")
    init.add_argument("--identity", help="identity bundle path")
    init.add_argument("--force", action="store_true", help="replace an existing bundle")
    init.set_defaults(handler=_init)

    login = subparsers.add_parser("login", help="unlock and connect an agent")
    login.add_argument("--identity", help="identity bundle path")
    login.add_argument("--url", help="Environment URL override")
    login.add_argument("--capability", action="append", default=[], help="agent capability")
    login.add_argument("--check", action="store_true", help="check the connection and exit")
    login.set_defaults(handler=_login)

    status = subparsers.add_parser("status", help="show identity and presence status")
    status.add_argument("--identity", help="identity bundle path")
    status.add_argument("--url", help="Environment URL override")
    status.set_defaults(handler=_status)

    logout = subparsers.add_parser("logout", help="remove the agent from the Environment")
    logout.add_argument("--identity", help="identity bundle path")
    logout.add_argument("--url", help="Environment URL override")
    logout.set_defaults(handler=_logout)

    token = subparsers.add_parser(
        "token", help="create a passwordless one-time agent pairing token"
    )
    token.add_argument("token_name", nargs="?", help="token purpose/name")
    token.add_argument("--name", help="token purpose/name")
    token.add_argument("--identity", help="identity bundle path")
    token.add_argument(
        "--expires", type=int, default=300, help="validity in seconds (default: 300)"
    )
    token.set_defaults(handler=_token)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ConnectionError, KeyError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
