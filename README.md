# rns-time

**Authenticated time distribution over [Reticulum](https://reticulum.network/).**
GPS-traceable time for off-grid mesh nodes, over TCP, I2P, or LoRa transports, with no internet anywhere in the chain.

```
GPS satellites ─> stratum-1 chrony (OpenTimeCard) ─> rns-time server (RNS node)
                                                          │  4-timestamp exchange over an RNS Link
                                                          v
                                     mesh clients (LoRa / TCP / I2P), no internet, no NTP
```

## Why

Off-grid nodes have terrible clocks and no way to set them: no NTP, no cell network,
maybe no GPS. But wrong time breaks TLS-style cert validity windows, log ordering,
scheduling, and any cryptographic protocol with timestamps. rns-time gives a mesh
node time that is:

- **GPS-traceable**, the reference implementation serves from a stratum-1 chrony host
- **Authenticated**, an RNS Link is end-to-end encrypted to the *server's identity*;
  if you know the server's destination hash, nobody can spoof its time answers
  (contrast: classic NTP is plaintext and trivially spoofed)
- **Latency-tolerant**, the NTP-style 4-timestamp exchange cancels *path delay*;
  residual error is path *asymmetry*, not latency. Multi-second LoRa RTTs are fine.

## Expected accuracy

| Transport | typical RTT | expected offset error |
|---|---|---|
| TCP / local | 10-100 ms | ~1-20 ms |
| I2P | 0.5-5 s | ~50-500 ms |
| LoRa (fast preset) | 1-6 s | ~0.2-2 s |

For a node that was days or weeks adrift, every row of that table is a win.

## Protocol (v1)

Client opens an RNS **Link** to the server destination (`rnstime`/`time`), then for
each round sends a msgpack map `{"v":1,"t1":<client send time>}`. The server replies
immediately with:

```
{"v":1, "t1":..., "t2":<server recv>, "t3":<server send>,
 "stratum":<local chrony stratum>, "root_disp_ms":<error bound>, "leap":"Normal"}
```

Client stamps `t4` on arrival and computes (RFC 5905 style):

```
offset = ((t2-t1)+(t3-t4))/2      delay = (t4-t1)-(t3-t2)
```

Several rounds are run; the sample with the **lowest delay** wins (least queuing,
least asymmetry). The server includes its chrony stratum + root dispersion so the
client knows the *quality* of what it's syncing to, a server in holdover says so.

## Usage

Server (on a host with chrony + an RNS instance, e.g. next to `rnsd`):
```
python3 -m rns_time.server            # prints its destination hash on startup
```

Client:
```
python3 -m rns_time.client <server_destination_hash>          # measure only
python3 -m rns_time.client <server_destination_hash> --set    # step the clock (root)
```

`--set` steps with `date`/`clock_settime` when the offset is large and leaves fine
discipline to whatever the node runs locally. Rule of thumb: mesh time is for getting
a node from "wrong by days" to "right within the table above", not for µs discipline.

## Files
- `rns_time/protocol.py`, wire format + offset math (shared)
- `rns_time/server.py`, serves time; refuses to claim health when local chrony is in holdover
- `rns_time/client.py`, N-round exchange, best-sample selection, optional `--set`
- `rnstime-server.service`, systemd unit
- `beacon/`, (experimental, stub) LXMF coarse time beacon for store-and-forward
  recovery of nodes that were completely dark. Not part of protocol v1.

## Security notes
- The Link is encrypted and authenticated **to the server identity**: distributing the
  server's destination hash out-of-band (QR, config bake-in) is the trust anchor.
- Time answers include quality metadata; clients SHOULD ignore answers with
  `stratum >= 10` (server in holdover/orphan) unless desperate.
- The server never trusts the client for anything; it only echoes timestamps.

## Status
Scaffold / v1 protocol. Reference deployment target: `.229` (rnsd shared instance,
syncs to the LAN stratum-1). Roadmap: LXMF beacon, client-side median-of-servers,
RNode GPS-mux (serve time straight from a GPS-equipped RNode).
