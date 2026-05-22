import os
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Config"])


@router.get("/ice-servers")
def get_ice_servers():
    turn_ip = os.getenv("TURN_SERVER_IP", "")
    turn_user = os.getenv("TURN_USERNAME", "justadvisor")
    turn_cred = os.getenv("TURN_CREDENTIAL", "")

    servers = [
        {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]},
    ]

    if turn_ip:
        servers.append({
            "urls": [
                f"turn:{turn_ip}:3478?transport=udp",
                f"turn:{turn_ip}:3478?transport=tcp",
                f"turns:{turn_ip}:5349?transport=tcp",
            ],
            "username": turn_user,
            "credential": turn_cred,
        })

    return {"iceServers": servers}
