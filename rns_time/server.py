"""rns-time server: authenticated GPS-traceable time over Reticulum.

Runs next to an RNS instance (shared rnsd is fine) on a chrony-synced host.
Prints its destination hash on startup — that hash is what clients need.

    python3 -m rns_time.server [--identity PATH] [--config RNS_CONFIG_DIR]
"""
import argparse
import datetime
import os
import subprocess
import time

import RNS

from . import manifest, protocol

IDENTITY_PATH_DEFAULT = os.path.expanduser("~/.rns_time/identity")
ANNOUNCE_INTERVAL = 1800  # seconds


def chrony_quality():
    """Read local chrony tracking: (stratum, root_dispersion_ms, leap).
    Falls back to (16, None, 'unknown') if chrony is unreadable."""
    try:
        f = subprocess.run(["chronyc", "-c", "tracking"], capture_output=True,
                           text=True, timeout=5).stdout.strip().split(",")
        stratum = int(f[2])
        root_disp_ms = (float(f[10]) + float(f[11])) * 1000.0  # delay + dispersion
        leap = f[13] if len(f) > 13 else "unknown"
        return stratum, round(root_disp_ms, 3), leap
    except Exception:
        return 16, None, "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity", default=IDENTITY_PATH_DEFAULT)
    ap.add_argument("--config", default=None, help="RNS config dir (default: shared instance)")
    args = ap.parse_args()

    RNS.Reticulum(args.config)

    os.makedirs(os.path.dirname(args.identity), exist_ok=True)
    if os.path.isfile(args.identity):
        identity = RNS.Identity.from_file(args.identity)
    else:
        identity = RNS.Identity()
        identity.to_file(args.identity)

    dest = RNS.Destination(identity, RNS.Destination.IN, RNS.Destination.SINGLE,
                           protocol.APP_NAME, *protocol.ASPECTS)
    dest.set_link_established_callback(on_link)
    # MeshAPI request-handler (discovery + the simple "now" op) alongside the
    # packet-based NTP exchange. Same destination, different access path.
    dest.register_request_handler(protocol.MESHAPI_PATH,
                                  response_generator=on_meshapi_request,
                                  allow=RNS.Destination.ALLOW_ALL)

    RNS.log(f"[rns-time] serving as {RNS.prettyhexrep(dest.hash)}")
    print(f"rns-time destination: {RNS.hexrep(dest.hash, delimit=False)}")

    while True:
        stratum, disp, leap = chrony_quality()
        if stratum <= protocol.MAX_HEALTHY_STRATUM:
            dest.announce()
            RNS.log(f"[rns-time] announced (stratum {stratum}, root_disp {disp}ms)")
        else:
            RNS.log(f"[rns-time] NOT announcing — local chrony unhealthy (stratum {stratum})")
        time.sleep(ANNOUNCE_INTERVAL)


def on_link(link):
    link.set_packet_callback(on_packet)


def on_meshapi_request(path, data, request_id, link_id, remote_identity, requested_at):
    """MeshAPI request-handler: __manifest__ discovery + the 'now' op."""
    try:
        req = protocol.unpack(data)
    except Exception:
        return protocol.pack({"v": protocol.VERSION, "ok": False, "err": "bad_encoding"})
    if not isinstance(req, dict):
        return protocol.pack({"v": protocol.VERSION, "ok": False, "err": "bad_encoding"})
    if req.get("op") == protocol.MANIFEST_OP:
        return protocol.pack({"v": protocol.VERSION, "ok": True, "manifest": manifest.MANIFEST})
    if req.get("op") == "now":
        stratum, disp, leap = chrony_quality()
        utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = {"v": protocol.VERSION, "ok": True,
                "res": {"utc": utc, "epoch": time.time(), "stratum": stratum,
                        "root_disp_ms": disp, "leap": leap}}
        if stratum > protocol.MAX_HEALTHY_STRATUM:
            resp["degraded"] = True
        return protocol.pack(resp)
    return protocol.pack({"v": protocol.VERSION, "ok": False, "err": "bad_op"})


def on_packet(data, packet):
    t2 = time.time()  # stamp receive as early as possible
    try:
        req = protocol.unpack(data)
        if req.get("v") != protocol.VERSION or "t1" not in req:
            return
        req["_t2"] = t2
        stratum, disp, leap = chrony_quality()
        RNS.Packet(packet.link, protocol.pack_response(req, stratum, disp, leap)).send()
    except Exception as e:
        RNS.log(f"[rns-time] bad request: {e}", RNS.LOG_DEBUG)


if __name__ == "__main__":
    main()
