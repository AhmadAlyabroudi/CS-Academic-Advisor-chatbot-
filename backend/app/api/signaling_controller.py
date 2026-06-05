from app.core.socket_manager import sio, room_participants

LOBBY_ROOM = "lobby"


def _room_key(data: dict) -> str:
    """Build a unique socket room key from type + id (e.g. 'Private:5')."""
    room_type = data.get("room_type") or data.get("roomType")
    room_id = data.get("room_id") or data.get("roomId")
    if room_type and room_id is not None and str(room_id):
        return f"{room_type}:{room_id}"
    return str(room_id or "")


def _find_participant(room_key: str, sid: str) -> dict | None:
    for p in room_participants.get(room_key, []):
        if p["sid"] == sid:
            return p
    return None


def _find_rooms_for_sid(sid: str) -> list[str]:
    return [k for k, members in room_participants.items() if any(p["sid"] == sid for p in members)]


@sio.event
async def join_lobby(sid, data):
    sio.enter_room(sid, LOBBY_ROOM)


@sio.event
async def leave_lobby(sid, data):
    sio.leave_room(sid, LOBBY_ROOM)


@sio.event
async def room_created(sid, data):
    await sio.emit("room-list-updated", {}, room=LOBBY_ROOM)


@sio.event
async def join_room(sid, data):
    room_key = _room_key(data)
    user_id = str(data.get("user_id") or data.get("userId") or sid)
    name = str(data.get("name", "Student"))

    if not room_key:
        return

    sio.enter_room(sid, room_key)

    if room_key not in room_participants:
        room_participants[room_key] = []

    # Re-join with updated name: remove stale entry for this socket first
    room_participants[room_key] = [
        p for p in room_participants[room_key] if p["sid"] != sid
    ]

    room_participants[room_key].append({"sid": sid, "user_id": user_id, "name": name})

    existing = [
        {"user_id": p["user_id"], "name": p["name"], "sid": p["sid"]}
        for p in room_participants[room_key]
        if p["sid"] != sid
    ]
    await sio.emit("existing-users", {"users": existing}, to=sid)

    await sio.emit(
        "user-joined",
        {"user_id": user_id, "name": name, "sid": sid},
        room=room_key,
        skip_sid=sid,
    )

    count = len(room_participants[room_key])
    await sio.emit("member-count", {"count": count}, room=room_key)


@sio.event
async def disconnect(sid):
    for room_key in _find_rooms_for_sid(sid):
        participant = _find_participant(room_key, sid)
        if participant:
            room_participants[room_key] = [
                p for p in room_participants[room_key] if p["sid"] != sid
            ]
            await sio.emit(
                "user-left",
                {"user_id": participant["user_id"], "name": participant["name"]},
                room=room_key,
                skip_sid=sid,
            )
            count = len(room_participants[room_key])
            await sio.emit("member-count", {"count": count}, room=room_key)
            if not room_participants[room_key]:
                del room_participants[room_key]


@sio.event
async def leave_room(sid, data):
    room_key = _room_key(data)
    participant = _find_participant(room_key, sid)

    sio.leave_room(sid, room_key)

    if room_key in room_participants:
        room_participants[room_key] = [
            p for p in room_participants[room_key] if p["sid"] != sid
        ]
        if participant:
            await sio.emit(
                "user-left",
                {"user_id": participant["user_id"], "name": participant["name"]},
                room=room_key,
                skip_sid=sid,
            )
        count = len(room_participants[room_key])
        await sio.emit("member-count", {"count": count}, room=room_key)
        if not room_participants[room_key]:
            del room_participants[room_key]


@sio.event
async def send_message(sid, data):
    room_key = _room_key(data)
    if not room_key:
        return
    user_id = data.get("user_id") or data.get("userId")
    await sio.emit(
        "receive-message",
        {
            "user_id": user_id,
            "userId": user_id,
            "name": data.get("name"),
            "message": data.get("message"),
            "timestamp": data.get("timestamp"),
        },
        room=room_key,
    )


# ── WebRTC signaling relay ────────────────────────────────────────────────────

@sio.event
async def offer(sid, data):
    target = data.get("target")
    if target:
        await sio.emit("offer", {"from": sid, "sdp": data.get("sdp")}, to=target)


@sio.event
async def answer(sid, data):
    target = data.get("target")
    if target:
        await sio.emit("answer", {"from": sid, "sdp": data.get("sdp")}, to=target)


@sio.event
async def ice_candidate(sid, data):
    target = data.get("target")
    if target:
        await sio.emit(
            "ice-candidate",
            {"from": sid, "candidate": data.get("candidate")},
            to=target,
        )
