import serial, time

# run AFTER flashing the location-enabled build:
#   systemctl --user stop meshmonitor.service
#   /home/rbc/Documents/LoRa/.venv/bin/python /tmp/enable_loc.py
#   systemctl --user start meshmonitor.service

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
cmd('advert', 3.0)            # flood advert with location
s.close()
print('done')
