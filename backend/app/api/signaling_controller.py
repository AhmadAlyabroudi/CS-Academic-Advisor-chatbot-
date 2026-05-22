from app.core.socket_manager import sio, room_participants


def _find_participant(room_key: str, sid: str) -> dict | None:
    for p in room_participants.get(room_key, []):
        if p["sid"] == sid:
            return p
    return None


def _find_rooms_for_sid(sid: str) -> list[str]:
    return [k for k, members in room_participants.items() if any(p["sid"] == sid for p in members)]


@sio.event
async def connect(sid, environ, auth=None):
    pass


@sio.event
async def disconnect(sid):
    for room_key in _find_rooms_for_sid(sid):
        participant = _find_participant(room_key, sid)
        if participant:
            room_participants[room_key] = [p for p in room_participants[room_key] if p["sid"] != sid]
            await sio.emit(
                "user-left",
                {"userId": participant["userId"], "name": participant["name"]},
                room=room_key,
                skip_sid=sid,
            )
            if not room_participants[room_key]:
                del room_participants[room_key]


@sio.event
async def join_room(sid, data):
    room_key = str(data.get("roomId", ""))
    user_id = str(data.get("userId", sid))
    name = str(data.get("name", "Student"))

    if not room_key:
        return

    sio.enter_room(sid, room_key)

    if room_key not in room_participants:
        room_participants[room_key] = []

    # Send current participants to the joiner before adding them
    existing = [
        {"userId": p["userId"], "name": p["name"], "sid": p["sid"]}
        for p in room_participants[room_key]
    ]
    await sio.emit("existing-users", {"users": existing}, to=sid)

    # Add the new participant
    room_participants[room_key].append({"sid": sid, "userId": user_id, "name": name})

    # Notify everyone else
    await sio.emit(
        "user-joined",
        {"userId": user_id, "name": name, "sid": sid},
        room=room_key,
        skip_sid=sid,
    )

    # Broadcast updated member count to the whole room
    count = len(room_participants[room_key])
    await sio.emit("member-count", {"count": count}, room=room_key)


@sio.event
async def leave_room(sid, data):
    room_key = str(data.get("roomId", ""))
    participant = _find_participant(room_key, sid)

    sio.leave_room(sid, room_key)

    if room_key in room_participants:
        room_participants[room_key] = [p for p in room_participants[room_key] if p["sid"] != sid]
        if participant:
            await sio.emit(
                "user-left",
                {"userId": participant["userId"], "name": participant["name"]},
                room=room_key,
                skip_sid=sid,
            )
        count = len(room_participants[room_key])
        await sio.emit("member-count", {"count": count}, room=room_key)
        if not room_participants[room_key]:
            del room_participants[room_key]


@sio.event
async def offer(sid, data):
    target_sid = data.get("target")
    if target_sid:
        await sio.emit("offer", {"from": sid, "sdp": data.get("sdp")}, to=target_sid)


@sio.event
async def answer(sid, data):
    target_sid = data.get("target")
    if target_sid:
        await sio.emit("answer", {"from": sid, "sdp": data.get("sdp")}, to=target_sid)


@sio.event
async def ice_candidate(sid, data):
    target_sid = data.get("target")
    if target_sid:
        await sio.emit(
            "ice-candidate",
            {"from": sid, "candidate": data.get("candidate")},
            to=target_sid,
        )


@sio.event
async def send_message(sid, data):
    room_key = str(data.get("roomId", ""))
    if room_key:
        await sio.emit(
            "receive-message",
            {
                "userId": data.get("userId"),
                "name": data.get("name"),
                "message": data.get("message"),
                "timestamp": data.get("timestamp"),
            },
            room=room_key,
        )


@sio.event
async def room_created(sid, data):
    """Broadcast to the lobby that a new room was created."""
    await sio.emit("room-list-updated", {}, room="lobby")


@sio.event
async def join_lobby(sid, data):
    sio.enter_room(sid, "lobby")


@sio.event
async def leave_lobby(sid, data):
    sio.leave_room(sid, "lobby")
