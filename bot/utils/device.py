from db import db
import asyncio
import time

# ── Rate Limiting ──────────────────────────────────────────────
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 5  # seconds

_rate_limit_store: dict[int, list[float]] = {}
_device_rate_limit_store: dict[str, list[float]] = {}

DEVICE_RATE_LIMIT_MAX = 10
DEVICE_RATE_LIMIT_WINDOW = 10


class RateLimitExceeded(Exception):
    pass


def _check_rate_limit(user_id: int) -> None:
    """Check if user has exceeded rate limit. Raises RateLimitExceeded if so."""
    now = time.time()
    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    # Remove expired timestamps
    _rate_limit_store[user_id] = [
        ts for ts in _rate_limit_store[user_id]
        if now - ts < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        raise RateLimitExceeded(
            f"Rate limit exceeded: max {RATE_LIMIT_MAX} commands per {RATE_LIMIT_WINDOW}s"
        )

    _rate_limit_store[user_id].append(now)


def _check_device_rate_limit(device_id: str) -> None:
    """Check if device has exceeded rate limit. Raises RateLimitExceeded if so."""
    now = time.time()
    if device_id not in _device_rate_limit_store:
        _device_rate_limit_store[device_id] = []

    _device_rate_limit_store[device_id] = [
        ts for ts in _device_rate_limit_store[device_id]
        if now - ts < DEVICE_RATE_LIMIT_WINDOW
    ]

    if len(_device_rate_limit_store[device_id]) >= DEVICE_RATE_LIMIT_MAX:
        raise RateLimitExceeded(
            f"Device rate limit exceeded: max {DEVICE_RATE_LIMIT_MAX} commands per {DEVICE_RATE_LIMIT_WINDOW}s"
        )

    _device_rate_limit_store[device_id].append(now)


async def push_command(device_id: str, command: str, payload: dict = None, user_id: int = None):
    if payload is None:
        payload = {}

    if user_id is not None:
        _check_rate_limit(user_id)
        conn = await db.select("connections", "id", {"device_id": device_id, "user_id": user_id, "is_active": True})
        if not conn:
            raise PermissionError("User does not own this device")

    _check_device_rate_limit(device_id)

    row = await db.insert("device_commands", {
        "device_id": device_id,
        "command": command,
        "payload": payload,
        "status": "pending"
    })

    if row:
        return row["id"]
    return None


async def wait_for_result(command_id: str, timeout: int = 15):
    if not command_id:
        return "error_no_id"

    for _ in range(timeout):
        await asyncio.sleep(1)
        rows = await db.select("device_commands", "status, result", {"id": command_id})
        if rows:
            if rows[0]["status"] == "completed":
                return rows[0]["result"]
            elif rows[0]["status"] == "error":
                return f"Error: {rows[0].get('result', 'Unknown error')}"
    return "timeout"


async def log_action(device_id: str, user_id: int, username: str, action: str):
    if device_id:
        await db.insert("logs", {
            "device_id": device_id,
            "user_id": user_id,
            "username": username or "Unknown",
            "action": action
        })
