from supabase_client import sb
import asyncio

def push_command(device_id: str, command: str, payload: dict = None):
    if payload is None:
        payload = {}
    
    resp = sb.table("device_commands").insert({
        "device_id": device_id,
        "command": command,
        "payload": payload,
        "status": "pending"
    }).execute()
    
    if resp.data:
        return resp.data[0]["id"]
    return None

async def wait_for_result(command_id: str, timeout: int = 15):
    if not command_id:
        return "error_no_id"
        
    for _ in range(timeout):
        await asyncio.sleep(1)
        resp = sb.table("device_commands").select("status, result").eq("id", command_id).execute()
        if resp.data:
            if resp.data[0]["status"] == "completed":
                return resp.data[0]["result"]
            elif resp.data[0]["status"] == "error":
                return f"Помилка: {resp.data[0].get('result', 'Невідома помилка')}"
    return "timeout"

def log_action(device_id: str, user_id: int, username: str, action: str):
    if device_id:
        sb.table("logs").insert({
            "device_id": device_id,
            "user_id": user_id,
            "username": username or "Unknown",
            "action": action
        }).execute()
