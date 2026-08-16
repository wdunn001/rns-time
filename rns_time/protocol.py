"""rns-time protocol v1: wire format + offset math (shared by server and client)."""
import time

import umsgpack  # bundled with RNS

VERSION = 1
APP_NAME = "rnstime"
ASPECTS = ("time",)

# Server-side health: refuse to advertise healthy time above this chrony stratum.
MAX_HEALTHY_STRATUM = 9


def pack_request():
    """Client -> server. Returns (payload_bytes, t1)."""
    t1 = time.time()
    return umsgpack.packb({"v": VERSION, "t1": t1}), t1


def pack_response(req: dict, stratum, root_disp_ms, leap):
    """Server -> client. t2 = receive time (stamp as early as possible, pass in),
    t3 = stamped here at send time."""
    return umsgpack.packb({
        "v": VERSION,
        "t1": req.get("t1"),
        "t2": req.get("_t2"),
        "t3": time.time(),
        "stratum": stratum,
        "root_disp_ms": root_disp_ms,
        "leap": leap,
    })


def unpack(data: bytes) -> dict:
    return umsgpack.unpackb(data)


def compute(t1, t2, t3, t4):
    """RFC 5905 offset/delay. Positive offset = local clock is BEHIND server."""
    offset = ((t2 - t1) + (t3 - t4)) / 2.0
    delay = (t4 - t1) - (t3 - t2)
    return offset, delay


def best_sample(samples):
    """samples: list of (offset, delay, meta). Lowest-delay sample has the least
    queuing and asymmetry — classic NTP filter for high-jitter paths."""
    return min(samples, key=lambda s: s[1]) if samples else None
