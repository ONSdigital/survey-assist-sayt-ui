#!/usr/bin/env python3
"""Inspect a local Redis-backed Flask session without changing it."""

from __future__ import annotations

import argparse
import getpass
import os
from pprint import pprint
import re
import sys

import msgspec
from redis import Redis
from redis.exceptions import RedisError

SESSION_KEY_PREFIX = "sayt-ui:session:"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Inspect a local Redis-backed Survey Assist UI session."
    )
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Print session values, including potentially sensitive survey answers.",
    )
    return parser.parse_args()


def _redis_port(raw_port: str) -> int:
    """Validate the Redis port from the environment.

    Args:
        raw_port: Value of REDIS_PORT.

    Returns:
        int: Validated TCP port.

    Raises:
        ValueError: If the port is not an integer between 1 and 65535.
    """
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("REDIS_PORT must be an integer") from exc

    if not 1 <= port <= 65535:
        raise ValueError("REDIS_PORT must be between 1 and 65535")

    return port


def read_session(
    redis_client: Redis,
    session_id: str,
) -> tuple[int, dict[str, object]]:
    """Read and decode one Redis-backed session.

    Args:
        redis_client: Redis client connected to the local session store.
        session_id: Opaque session ID, without the Redis key prefix.

    Returns:
        tuple[int, dict[str, object]]: Remaining TTL and decoded session data.

    Raises:
        ValueError: If the ID is invalid, the session is missing, or its
            decoded value is not a session dictionary.
        msgspec.DecodeError: If the stored bytes are not valid msgpack.
        RedisError: If reading Redis fails.
    """
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("Enter a session ID without the Redis key prefix")

    key = f"{SESSION_KEY_PREFIX}{session_id}"
    raw_value = redis_client.get(key)

    if raw_value is None:
        raise ValueError("Session not found; check the ID or whether it has expired")

    data = msgspec.msgpack.decode(raw_value)

    if not isinstance(data, dict) or any(not isinstance(field_name, str) for field_name in data):
        raise ValueError("Stored session is not a dictionary with string keys")

    ttl = redis_client.ttl(key)

    if ttl == -2:
        raise ValueError("Session expired while it was being inspected")

    return ttl, data


def main() -> int:
    """Inspect a session identified interactively by the operator in
    a locally running Redis instance.

    Returns:
        int: Zero on success, or one if configuration, Redis, or session
        inspection fails.
    """
    args = parse_args()
    host = os.getenv("REDIS_HOST", "").strip()

    if not host:
        print("Error: REDIS_HOST must be configured", file=sys.stderr)
        return 1

    password = os.getenv("REDIS_PASSWORD", "").strip()
    if not password:
        print("Error: REDIS_PASSWORD must be configured", file=sys.stderr)
        return 1

    try:
        port = _redis_port(os.getenv("REDIS_PORT", "6379"))
        session_id = getpass.getpass("Session ID (without sayt-ui:session:): ").strip()
        redis_client = Redis(
            host=host,
            port=port,
            password=password,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        ttl, data = read_session(redis_client, session_id)
    except (ValueError, msgspec.DecodeError, RedisError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Redis TTL: {ttl} seconds")
    print("Session fields:")
    for field_name in sorted(data):
        print(f"  {field_name}")

    if args.show_values:
        print(
            "Warning: session values may contain personal data and survey answers.",
            file=sys.stderr,
        )
        pprint(data, sort_dicts=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
