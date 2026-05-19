from db import db
import asyncio
import time
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ── Rate Limiting ──────────────────────────────────────────────
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 5  # seconds
HEARTBEAT_TIMEOUT = timedelta(seconds=60)

_rate_limit_store: dict[int, list[float]] = {}


class RateLimitExceeded(Exception):
    pass


class DeviceOffline(Exception):
    pass


def _check_rate_limit(user_id: int) -> None:
    now = time.time()
    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    _rate_limit_store[user_id] = [
        ts for ts in _rate_limit_store[user_id]
        if now - ts < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        raise RateLimitExceeded(
            f"Rate limit exceeded: max {RATE_LIMIT_MAX} commands per {RATE_LIMIT_WINDOW}s"
        )

    _rate_limit_store[user_id].append(now)


async def is_device_online(device_id: str, mark_offline: bool = True) -> bool:
    dev = await db.select_one("devices", "is_online, last_seen_at", {"id": device_id})
    if not dev or not dev.get("is_online"):
        return False

    last_seen_at = dev.get("last_seen_at")
    if not last_seen_at:
        return False

    if isinstance(last_seen_at, str):
        last_seen_at = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)

    online = (datetime.now(timezone.utc) - last_seen_at) < HEARTBEAT_TIMEOUT

    if not online and mark_offline:
        await db.update("devices", {"is_online": False}, {"id": device_id})

    return online


async def push_command(device_id: str, command: str, payload: dict = None, user_id: int = None):
    if payload is None:
        payload = {}

    if user_id is not None:
        _check_rate_limit(user_id)

    if not await is_device_online(device_id):
        raise DeviceOffline("Device is offline")

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
