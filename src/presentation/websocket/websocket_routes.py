from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
from datetime import datetime, timezone
from .connection_manager import manager
from src.config.auth import get_optional_user
import json

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = Query(None)):
    """WebSocket endpoint for real-time job status updates"""
    
    # Simple token validation for WebSocket (in production, use proper validation)
    if not token or not token.startswith("clerk_"):
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connection",
            "message": "Connected to AI Backend WebSocket",
            "user_id": user_id
        }, user_id)
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                }, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {str(e)}")
        manager.disconnect(websocket, user_id)


async def notify_job_status_update(user_id: str, job_id: str, status: str, message: str = None, session_id: str | None = None):
    """Notify user about job status update via WebSocket"""
    await manager.send_personal_message({
        "type": "job_status_update",
        "job_id": job_id,
        "status": status,
        "session_id": session_id,
        "message": message,
        "timestamp": str(datetime.now(timezone.utc))
    }, user_id)
