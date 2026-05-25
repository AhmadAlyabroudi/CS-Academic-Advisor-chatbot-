from app.core.socket_manager import sio, room_participants


def _find_participant(room_key: str, sid: str) -> dict | None:
    for p in room_participants.get(room_key, []):
        if p["sid"] == sid:
            return p
    return None


def _find_rooms_for_sid(sid: str) -> list[str]:
    return [k for k, members in room_participants.items() if any(p["sid"] == sid for p in members)]


@sio.event
async def join_room(sid, data):
    # التصحيح هون: الباكيند لازم يقرأ room_id و user_id بالأندرسكور
    room_key = str(data.get("room_id", ""))
    user_id = str(data.get("user_id", sid))
    name = str(data.get("name", "Student"))

    if not room_key:
        return

    sio.enter_room(sid, room_key)

    if room_key not in room_participants:
        room_participants[room_key] = []

    # إرسال المستخدمين بصيغة user_id للأندرسكور لتطابق الفرونتيند
    existing = [
        {"user_id": p["user_id"], "name": p["name"], "sid": p["sid"]}
        for p in room_participants[room_key]
    ]
    await sio.emit("existing-users", {"users": existing}, to=sid)

    # إضافة المستخدم الجديد بالـ Snake Case
    room_participants[room_key].append({"sid": sid, "user_id": user_id, "name": name})

    # إطلاق الحدث المتوافق
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
            room_participants[room_key] = [p for p in room_participants[room_key] if p["sid"] != sid]
            await sio.emit(
                "user-left",
                {"user_id": participant["user_id"], "name": participant["name"]},
                room=room_key,
                skip_sid=sid,
            )
            if not room_participants[room_key]:
                del room_participants[room_key]


@sio.event
async def leave_room(sid, data):
    room_key = str(data.get("room_id", ""))
    participant = _find_participant(room_key, sid)

    sio.leave_room(sid, room_key)

    if room_key in room_participants:
        room_participants[room_key] = [p for p in room_participants[room_key] if p["sid"] != sid]
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
    room_key = str(data.get("room_id", ""))
    if room_key:
        await sio.emit(
            "receive-message",
            {
                "user_id": data.get("user_id"),
                "name": data.get("name"),
                "message": data.get("message"),
                "timestamp": data.get("timestamp"),
            },
            room=room_key,
        )