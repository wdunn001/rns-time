# LXMF time beacon (experimental, not protocol v1)

Store-and-forward coarse time for nodes that were completely dark.

Idea: broadcast a signed LXMF message every N hours containing the send timestamp
and the server's quality metadata. A node that has been off for a week and merely
*receives* the beacon (even hours late, via propagation nodes) can bound its clock
error to roughly the propagation delay, enough to get certificates and schedules
working again, after which it can do a live rns-time Link exchange for real accuracy.

Open questions before building:
- propagation-node delivery delay is unbounded -> the beacon must carry "sent at"
  and clients must treat age as unknown-but-positive (clock can only be stepped
  FORWARD safely from a beacon; never backward)
- rate: LoRa airtime is precious; hourly is probably too chatty for slow presets
- dedup across multiple beacon servers

Nothing here yet, `rns_time.client` + a live Link is the real mechanism.
