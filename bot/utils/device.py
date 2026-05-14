from db import db
import asyncio


async def push_command(device_id: str, command: str, payload: dict = None):
    if payload is None:
        payload = {}

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
