"""MeshAPI 0.1 manifest for rns-time. Served over RNS via the __manifest__
discovery op on the MeshAPI request path. Plain dict (conforms to MeshAPI 0.1).
See github.com/wdunn001/meshapi.

Note: the precise, GPS-traceable clock sync is the packet-based NTP 4-timestamp
exchange (see protocol.py / the client); MeshAPI here exposes the simple
request/response `now` op for programmatic clients and the interactive explorer.
"""
MANIFEST = {
    "meshapi": "0.1",
    "service": {
        "name": "rns-time",
        "summary": "Authenticated time over Reticulum",
        "app": "rnstime",
        "aspect": "time",
        "path": "t",
        "dest": "e210fb416af335bd68a9ed4b86919895",
        "encoding": "umsgpack",
        "source": "https://github.com/wdunn001/rns-time",
    },
    "ops": [
        {"op": "now", "summary": "Current GPS/chrony-disciplined server time", "auth": "none",
         "request": {},
         "response": {"utc": "str", "epoch": "float", "stratum": "int",
                      "root_disp_ms": "float", "leap": "str"}},
    ],
}
