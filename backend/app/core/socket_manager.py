import os
import socketio

_origins = os.getenv("ALLOWED_ORIGINS", "*")
cors_origins = [o.strip() for o in _origins.split(",")] if _origins != "*" else "*"

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=cors_origins,
    logger=False,
    engineio_logger=False,
)

# room_key (str) → list of {"sid": str, "userId": str, "name": str}
room_participants: dict[str, list[dict]] = {}
