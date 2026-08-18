>rns-time — authenticated time service

`F4ade80GPS-traceable time for mesh nodes, over Reticulum itself.`f
No internet, no NTP, no cell required — works over TCP, I2P, and LoRa.

-

>>Server destination

`=
e210fb416af335bd68a9ed4b86919895
app: rnstime   aspect: time
`=

Source: stratum-1 GPS (u-blox MAX-M10S / OpenTimeCard Mini) -> chrony -> this service.
Answers are `!authenticated`! — the RNS Link is encrypted to the server identity above,
so with the right hash nobody can spoof your time. The server refuses to announce
when its own clock is in holdover.

-

>>Expected accuracy

`=
transport     typical RTT    offset error
TCP / LAN     10-100 ms      ~1-20 ms
I2P           0.5-5 s        ~50-500 ms
LoRa          1-6 s          ~0.2-2 s
`=

The 4-timestamp exchange cancels path delay; the residual is path asymmetry.
Multi-second LoRa RTTs are fine — that is the point.

-

>>Get the time

`=
pip install rns
git clone https://github.com/wdunn001/rns-time.git
cd rns-time
python3 -m rns_time.client e210fb416af335bd68a9ed4b86919895
`=

Add --set (as root) to step your clock. Add --timeout 120 on slow LoRa paths.

-

>>Stock NTP client? (over meshtunnel)

rns-time above speaks its own protocol. To point an `!unmodified`! chrony / ntpd /
Windows Time at this same GPS clock, a MeshTunnel egress fronts it on plain UDP 123
over Reticulum:

`=
ntp egress   874db2e2afd043320b38de431c15c173
app: ntp   aspect: tunnel   port: 123
`=

Download the launcher and run the ready-made profile:

`=
pip install rns
pip install git+https://github.com/wdunn001/meshtunnel
pip install git+https://github.com/wdunn001/meshtunnel-launcher
git clone https://github.com/wdunn001/meshtunnel-launcher
meshtunnel-launch meshtunnel-launcher/examples/quasarke-ntp.toml
`=

Then set 127.0.0.1 as your time source (chrony: `!server 127.0.0.1 iburst`!).
Add `!--install`! to hold the tunnel up at every startup (Windows or Linux).
Stop your OS time daemon first if it already holds UDP 123.

`F4ade80meshtunnel`f https://github.com/wdunn001/meshtunnel
`F4ade80launcher`f  https://github.com/wdunn001/meshtunnel-launcher

>>Protocol v1 (for implementers)

Open an RNS Link to app `!rnstime`! aspect `!time`!. Per round send msgpack
{"v":1,"t1":<send time>}; server replies with t1,t2,t3 + stratum/root_disp_ms/leap.
Stamp t4 on arrival:

`=
offset = ((t2-t1)+(t3-t4))/2      delay = (t4-t1)-(t3-t2)
`=

Run several rounds, keep the lowest-delay sample. Ignore answers with stratum >= 10.
Only step FORWARD from store-and-forward time; live Links may step either way.

-

web: https://ntp.quasarke.net/rns   ·   source: https://github.com/wdunn001/rns-time
meshtunnel: https://github.com/wdunn001/meshtunnel   ·   launcher: https://github.com/wdunn001/meshtunnel-launcher
