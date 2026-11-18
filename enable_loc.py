import serial, time

# One-time configuration after flashing the location-enabled build.
# Stop anything that owns the serial port first (meshmonitor, exporters, etc.).
#
# TWO_BYTE_PATH: set True if your community enforces 2-byte path hashes
# (LusoFW-class forks, e.g. MeshCore Portugal) — their maps flag stock's
# 1-byte default as "older firmware". Stock pref, persists in flash; only
# affects this node's own flood adverts. Leave False elsewhere.
TWO_BYTE_PATH = False

s = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
s.reset_input_buffer()

def cmd(c, wait=1.5):
    s.write((c + '\r').encode())
    time.sleep(wait)
    out = s.read(8000).decode(errors='replace').strip()
    print(f'--- {c!r} ---')
    print(out if out else '(no output)')
    return out

time.sleep(1.5)
cmd('gps advert')             # policy query — MUST print "> none" (proves the feature compiled in)
cmd('gps advert prefs')       # -> "ok" : adverts now embed stored lat/lon
cmd(f'time {int(time.time())}')  # fresh clock (boot reset it to 15 May 2024)
cmd('get lat')
cmd('get lon')
if TWO_BYTE_PATH:
    cmd('set path.hash.mode 1')   # -> "ok"
    cmd('get path.hash.mode')     # -> "> 1"
cmd('advert', 3.0)            # flood advert with location
s.close()
print('done')
