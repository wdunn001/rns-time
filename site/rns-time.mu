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
