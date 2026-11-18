# Xiao nRF52840 — Location Adverts for MeshCore Repeaters

A **two-file, 13-line patch** against official [MeshCore](https://github.com/meshcore-dev/MeshCore)
`v1.18.0` that makes a Seeed XIAO nRF52840 (Wio SX1262) repeater **visible on the network maps** —
no GPS hardware, no protocol changes, stock code paths only.

Built and verified live on the [MeshCore Portugal](https://www.meshcore.pt) network
(node `SE.SXL GGEZUS R8`, Seixal).

## The symptom

A freshly-flashed Xiao repeater with `lat`/`lon` correctly set (and even saved in the community's
repeater registry) simply **does not appear on the map** — neither on meshcore.pt nor
meshcore.io/map. The node detail page shows `Location: —`, and the node feed API reports
`lat: 0, long: 0`. On the PT network, 43 of 709 listed nodes are coordinate-less this way.

## The root cause chain

Every MeshCore map derives node position **only from coordinates embedded in the node's advert
packets**. For this board that chain is broken at compile time:

```
map dot            ← advert-embedded coords
advert coords      ← advert_loc_policy (default NONE, only settable via `gps advert prefs`)
`gps advert *` CLI ← compiled in only when ENV_INCLUDE_GPS == 1
ENV_INCLUDE_GPS    ← explicitly UNdefined (-UENV_INCLUDE_GPS) in variants/xiao_nrf52
```

The strip exists in the official tree (whole Xiao family plus ~11 other small-flash boards;
78 of 92 variants ship with it on) and is inherited verbatim by community forks.

**The key insight:** `ENV_INCLUDE_GPS` is a misleading *flag name*. The `prefs` location policy
just broadcasts the stored `lat`/`lon` from node prefs — **no GPS hardware is involved**.
The flag being stripped doesn't remove a GPS feature, it removes *static coordinates from adverts*.

## The fix

Flag-on builds need board plumbing the Xiao variant never had. Pattern taken from
`heltec_t114` — an nRF52840 board that ships with the flag on and **no GPS hardware**:

- `variants/xiao_nrf52/platformio.ini`
  - drop `-UENV_INCLUDE_GPS`
  - `-D PIN_GPS_TX=31 -D PIN_GPS_RX=30` — the unpopulated **NFC pads**. Every exposed pin is
    taken (D0 button, D1–D5 radio, D6/D7 RTC I²C, D8–D10 radio SPI), so the unused GPS UART
    parks on electrically dead pads
  - `-D ENV_SKIP_GPS_DETECT` — skip the 5 s "is a GPS plugged in?" boot probe
- `variants/xiao_nrf52/target.cpp`
  - construct `EnvironmentSensorManager` with a `MicroNMEALocationProvider(Serial1, &rtc_clock)`
    under `#if ENV_INCLUDE_GPS`. The provider idles forever (nothing is wired to pads 30/31)

See [`0001-enable-location-adverts-xiao-nrf52.patch`](0001-enable-location-adverts-xiao-nrf52.patch)
for the full diff.

## Build

```sh
git clone --depth 1 --branch repeater-v1.18.0 https://github.com/meshcore-dev/MeshCore.git
cd MeshCore
git am /path/to/0001-enable-location-adverts-xiao-nrf52.patch
pio run -e Xiao_nrf52_repeater -t create_uf2     # NOTE: UF2 needs the explicit create_uf2 target
# → .pio/build/Xiao_nrf52_repeater/firmware.uf2
```

(First build downloads ~300 MB of toolchain into `~/.platformio`.)

## Flash

Double-tap RST (fast, <0.5 s apart) → board enumerates as the `XIAO-SENSE` mass-storage drive
(~17 s window) → copy the UF2 onto it. **Node prefs survive the reflash** (name, keys,
coordinates, regions, duty cycle). Reverting = reflash any stock/community UF2.

## Configure (one-time, over USB serial at 115200)

```
gps advert           # → "> none"   proves the feature compiled in
gps advert prefs     # → "ok"       adverts now embed stored lat/lon
time <epoch>         # fresh clock (boot resets it to a 2024 firmware epoch)
set path.hash.mode 1 # optional — community-dependent, see below
advert               # flood advert with coordinates
```

[`enable_loc.py`](enable_loc.py) automates the sequence (pyserial).

### Path hash width (community-dependent, one-time)

Flood packets carry a *path* of short hashes of the repeaters they traversed. Stock defaults
to **1-byte** hashes (`path.hash.mode 0` — still the upstream default). Communities running
LusoFW-class forks standardize on **2-byte**, and their maps flag 1-byte-only nodes as
"older firmware" — a freshly flashed stock build triggers exactly that warning even on
current firmware. It's a stock runtime pref (no rebuild), persists in flash, and only
affects the node's **own** flood adverts — repeated traffic keeps the originator's width:

```
get path.hash.mode   # → "> 0" (stock default)
set path.hash.mode 1 # → "ok"
```

## Verification — before/after

PT node detail API (`meshcore.pt/api/nodes/detail?id=…`) for the same node, same day:

```json
// before (stock/community Xiao firmware):
{ "lat": 0,          "long": 0,          "lastAdvertAt": … }
// after this patch + `gps advert prefs`:
{ "lat": 38.616276,  "long": -9.097648,  "lastAdvertAt": … }
```

Result: dot on **meshcore.pt** (geo-resolved Lisboa e Vale do Tejo → Setúbal → Seixal → `SE.SXL`)
and on **meshcore.io/map** (picked up by a LetsMesh-class observer within 9 minutes of the
first coordinates-carrying advert).

## Caveats

- The clock still resets to a 2024 epoch on every power cycle — unrelated stock behavior;
  re-run `time <epoch>` after powerbank stints. Map coordinates are unaffected.
- Community panels may label the node with their own (cached) firmware string — cosmetic.

## Credits / basis

- Base: meshcore-dev/MeshCore (formerly ripplebiz), tag `repeater-v1.18.0` (commit `81dbae5`)
- Board-plumbing pattern: `variants/heltec_t114` from the same tree

## License

MIT — same as MeshCore upstream. See [LICENSE](LICENSE) (upstream copyright
notice preserved, as MIT requires for derivatives).
