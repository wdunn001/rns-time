"""rns-time client: fetch authenticated time from a rns-time server over Reticulum.

    python3 -m rns_time.client <server_destination_hash> [--rounds 5] [--set]
                               [--config RNS_CONFIG_DIR] [--timeout 90]

Exit codes: 0 ok, 1 no path/link, 2 no samples, 3 server unhealthy.
"""
import argparse
import subprocess
import sys
import threading
import time

import RNS

from . import protocol


class Exchange:
    def __init__(self):
        self.event = threading.Event()
        self.response = None
        self.t4 = None

    def on_packet(self, data, packet):
        self.t4 = time.time()  # stamp arrival first
        self.response = data
        self.event.set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("server", help="server destination hash (hex)")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--set", action="store_true", help="step the local clock (needs root)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--timeout", type=float, default=90, help="per-step timeout (LoRa needs patience)")
    args = ap.parse_args()

    RNS.Reticulum(args.config)
    dest_hash = bytes.fromhex(args.server)

    if not RNS.Transport.has_path(dest_hash):
        print("requesting path...")
        RNS.Transport.request_path(dest_hash)
        deadline = time.time() + args.timeout
        while not RNS.Transport.has_path(dest_hash):
            if time.time() > deadline:
                print("no path to server"); sys.exit(1)
            time.sleep(0.25)

    identity = RNS.Identity.recall(dest_hash)
    dest = RNS.Destination(identity, RNS.Destination.OUT, RNS.Destination.SINGLE,
                           protocol.APP_NAME, *protocol.ASPECTS)

    up = threading.Event()
    link = RNS.Link(dest, established_callback=lambda l: up.set())
    if not up.wait(args.timeout):
        print("link establishment timed out"); sys.exit(1)

    samples = []
    for i in range(args.rounds):
        ex = Exchange()
        link.set_packet_callback(ex.on_packet)
        payload, t1 = protocol.pack_request()
        RNS.Packet(link, payload).send()
        if not ex.event.wait(args.timeout):
            print(f"round {i+1}: timeout"); continue
        try:
            r = protocol.unpack(ex.response)
            offset, delay = protocol.compute(r["t1"], r["t2"], r["t3"], ex.t4)
            samples.append((offset, delay, r))
            print(f"round {i+1}: offset {offset:+.4f}s  delay {delay:.4f}s  "
                  f"(server stratum {r.get('stratum')}, root_disp {r.get('root_disp_ms')}ms)")
        except Exception as e:
            print(f"round {i+1}: bad response ({e})")
        time.sleep(0.5)

    link.teardown()
    if not samples:
        print("no valid samples"); sys.exit(2)

    offset, delay, meta = protocol.best_sample(samples)
    stratum = meta.get("stratum", 16)
    print(f"\nBEST: offset {offset:+.4f}s (local clock is "
          f"{'behind' if offset > 0 else 'ahead of'} server)  delay {delay:.4f}s")
    print(f"      server stratum {stratum}, root_disp {meta.get('root_disp_ms')}ms, "
          f"leap {meta.get('leap')}")

    if stratum > protocol.MAX_HEALTHY_STRATUM:
        print("server is UNHEALTHY (holdover) - not applying"); sys.exit(3)

    if args.set:
        target = time.time() + offset
        try:
            import ctypes  # clock_settime via librt-less path: use date as portable fallback
            subprocess.run(["date", "-u", "-s",
                            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(target))
                            + f".{int((target % 1)*1e6):06d}"],
                           check=True, capture_output=True)
            print("clock stepped.")
        except Exception as e:
            print(f"failed to set clock ({e}) - run as root?"); sys.exit(1)


if __name__ == "__main__":
    main()
