"""Halloween skulls controller: Pico 2 W driving a chain of NeoPixel ornaments.

The chain is described by CHAIN (ornaments in order from the box, with their
LED counts — see README "Firmware chain layout"). Effects address ornaments,
not LEDs, so a different mix of ornaments only needs CHAIN changed.
Commands arrive over USB serial and MQTT (net_mqtt.py) and both go through
handle_command().

See HELP_TEXT for the command protocol. Kept as a constant rather than the
module docstring, because this MicroPython build doesn't populate __doc__.
"""

HELP_TEXT = """Command protocol, one command per line, case-insensitive:

    ON                              resume the last colours/patterns
    OFF                             all ornaments dark
    COLOR <zone> <r>,<g>,<b>        solid colour on a zone
    PATTERN <zone> <name> [args]    run a pattern on a zone
    BRIGHTNESS <0-100>              overall brightness, keeps patterns
    SET STARTUP <command>           run <command> now and save it as the
                                     boot-time default (persists across
                                     reboots; default OFF, so openHAB's
                                     Halloween scene decides)
    STATUS                          state: power, jack, then one line per
                                     pattern group
    HELP                            print this command list

Any command except OFF, STATUS and HELP also turns the skulls on.

Zones: all | 1-N (ornament number, 1 = nearest the box). A pattern sent to
"all" runs on one clock, so every ornament stays in step.

Patterns:
    heartbeat [<r>,<g>,<b>] [period_s]  lub-dub, like the flowers' scary
                                         stems (default red, 1.5s = 40 bpm)
    flicker [<r>,<g>,<b>]               uneasy candle flicker, each ornament
                                         on its own phase (default orange)
    breathe <r>,<g>,<b> [period_s]      smooth fade in/out (default 4s)
    rainbow [period_s]                  cycle through every hue (default 10s)

Examples:
    PATTERN all heartbeat 255,0,0 1.304
    PATTERN all flicker
    PATTERN 2 breathe 0,255,0 3
    COLOR all 255,255,255
    BRIGHTNESS 50
    SET STARTUP PATTERN all flicker
    OFF
"""

from machine import ADC, Pin, WDT
from neopixel import NeoPixel
import sys
import select
import time
import math

from net_mqtt import SkullsMQTT

CHAIN = [
    ("skull", 1),
    ("skull", 1),
    ("skull", 1),
]

DATA_PIN = 22         # pin 29; see README "Wiring list"
SENSE_ADC = 28        # pin 34: 4.7k/4.7k divider off the jack rail
SENSE_ON_V = 1.5      # ~2.5V with the jack powered, 0V without
TICK_MS = 20
WDT_TIMEOUT_MS = 8000

HEARTBEAT_COLOR = (255, 0, 0)
HEARTBEAT_PERIOD = 1.5
HEARTBEAT_FLOOR = 0.06  # never fully dark between beats
FLICKER_COLOR = (255, 70, 0)

STARTUP_COMMAND = "OFF"
STARTUP_FILE = "/startup.txt"

# ornament number (1-based) -> list of LED indices
ORNAMENT_LEDS = []
_i = 0
for _name, _count in CHAIN:
    ORNAMENT_LEDS.append(list(range(_i, _i + _count)))
    _i += _count
NUM_LEDS = _i

np = NeoPixel(Pin(DATA_PIN), NUM_LEDS)
data_pin = Pin(DATA_PIN)
sense = ADC(SENSE_ADC)


def sense_v():
    return sum(sense.read_u16() for _ in range(4)) / 4 * 3.3 / 65535


def parse_zone(token):
    token = token.lower()
    if token == "all":
        return list(range(1, len(CHAIN) + 1))
    if token.isdigit() and 1 <= int(token) <= len(CHAIN):
        return [int(token)]
    raise ValueError("unknown zone: %s (all or 1-%d)" % (token, len(CHAIN)))


def parse_color(token):
    parts = token.split(",")
    if len(parts) != 3:
        raise ValueError("color must be r,g,b")
    c = tuple(int(p) for p in parts)
    for v in c:
        if not 0 <= v <= 255:
            raise ValueError("color channel out of range 0-255")
    return c


def wheel(pos):
    """0.0-1.0 -> RGB, evenly spaced hues."""
    pos = int((pos % 1.0) * 255)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def heartbeat_level(elapsed, period):
    """0.0-1.0 lub-dub, the same curve as led_flowerpot's scary stems: a fast
    rise then exponential fall for each beat, the softer dub 0.25s after."""
    t = elapsed % period
    level = 0.0
    for onset, amp in ((0.0, 1.0), (0.25, 0.6)):
        x = t - onset
        if x < 0:
            continue
        if x < 0.06:
            beat = amp * x / 0.06
        else:
            beat = amp * math.exp(-(x - 0.06) / 0.12)
        level = max(level, beat)
    return HEARTBEAT_FLOOR + (1 - HEARTBEAT_FLOOR) * level


def flicker_level(elapsed, seed):
    """0.0-1.0 uneasy flicker: incommensurate sines, phase-shifted per
    ornament so they don't flicker together."""
    wave = (
        math.sin(2 * math.pi * (elapsed * 1.9 + seed * 0.37))
        + math.sin(2 * math.pi * (elapsed * 4.7 + seed * 0.61))
        + math.sin(2 * math.pi * (elapsed * 11.3 + seed * 0.89))
    ) / 3
    return 0.6 + 0.4 * wave


def scale(c, k):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


class Pattern:
    def __init__(self, name, ornaments, color=(0, 0, 0), period=1.0):
        self.name = name
        self.ornaments = ornaments
        self.color = color
        self.period = period
        self.start = time.ticks_ms()

    def color_at(self, now_ms, ornament):
        elapsed = time.ticks_diff(now_ms, self.start) / 1000
        if self.name == "solid":
            return self.color
        if self.name == "heartbeat":
            return scale(self.color, heartbeat_level(elapsed, self.period))
        if self.name == "flicker":
            return scale(self.color, flicker_level(elapsed, ornament))
        if self.name == "breathe":
            phase = (elapsed % self.period) / self.period
            return scale(self.color, (1 - math.cos(2 * math.pi * phase)) / 2)
        if self.name == "rainbow":
            return wheel(elapsed / self.period + ornament / len(CHAIN))
        return (0, 0, 0)


class Skulls:
    def __init__(self):
        self.power = False
        self.brightness = 100
        self.jack = False
        # ornament number -> Pattern; ornaments sent the same command share
        # one Pattern instance, and so one clock
        self.active = {n: Pattern("solid", [n]) for n in range(1, len(CHAIN) + 1)}

    def set_pattern(self, ornaments, name, color=(0, 0, 0), period=1.0):
        p = Pattern(name, ornaments, color, period)
        for n in ornaments:
            self.active[n] = p
        self.power = True

    def render(self, now_ms):
        self.jack = sense_v() > SENSE_ON_V
        if not self.jack:
            # chain unpowered (USB only, or the pack cut out): keep the data
            # line low rather than driving current into the first LED's input
            data_pin.init(Pin.OUT, value=0)
            return
        k = self.brightness / 100 if self.power else 0
        for n, p in self.active.items():
            c = scale(p.color_at(now_ms, n), k) if k else (0, 0, 0)
            for i in ORNAMENT_LEDS[n - 1]:
                np[i] = c
        np.write()

    def status_lines(self):
        lines = ["power=%s jack=%s brightness=%d ornaments=%d" % (
            "on" if self.power else "off", "on" if self.jack else "off",
            self.brightness, len(CHAIN))]
        seen = []
        for n in range(1, len(CHAIN) + 1):
            p = self.active[n]
            if p in seen:
                continue
            seen.append(p)
            group = [m for m in range(1, len(CHAIN) + 1) if self.active[m] is p]
            lines.append("zone=%s pattern=%s color=%d,%d,%d period=%s" % (
                ",".join(str(m) for m in group), p.name,
                p.color[0], p.color[1], p.color[2], p.period))
        return lines


skulls = Skulls()


def handle_command(line, out=print):
    line = line.strip()
    if not line:
        return
    line = line.replace(", ", ",")  # tolerate "r, g, b"
    parts = line.split()
    cmd = parts[0].upper()
    try:
        if cmd == "ON":
            skulls.power = True
        elif cmd == "OFF":
            skulls.power = False
        elif cmd == "COLOR":
            skulls.set_pattern(parse_zone(parts[1]), "solid", parse_color(parts[2]))
        elif cmd == "PATTERN":
            zone = parse_zone(parts[1])
            name = parts[2].lower()
            args = parts[3:]
            # optional leading colour, then optional period
            color = None
            if args and "," in args[0]:
                color = parse_color(args.pop(0))
            period = float(args[0]) if args else None
            if period is not None and period <= 0:
                raise ValueError("period must be > 0")
            if name == "heartbeat":
                skulls.set_pattern(zone, name, color or HEARTBEAT_COLOR, period or HEARTBEAT_PERIOD)
            elif name == "flicker":
                skulls.set_pattern(zone, name, color or FLICKER_COLOR)
            elif name == "breathe":
                if color is None:
                    raise ValueError("breathe needs a colour")
                skulls.set_pattern(zone, name, color, period or 4.0)
            elif name == "rainbow":
                skulls.set_pattern(zone, name, period=period or 10.0)
            else:
                raise ValueError("unknown pattern: %s" % name)
        elif cmd == "BRIGHTNESS":
            pct = int(float(parts[1]))
            if not 0 <= pct <= 100:
                raise ValueError("brightness out of range 0-100")
            skulls.brightness = pct
            skulls.power = True
        elif cmd == "SET" and len(parts) > 1 and parts[1].upper() == "STARTUP":
            sub_cmd = " ".join(parts[2:])
            if not sub_cmd:
                raise ValueError("SET STARTUP requires a command, e.g. PATTERN all flicker")
            result = []
            handle_command(sub_cmd, out=result.append)
            if result and result[0].startswith("ERR"):
                out(result[0])
                return
            with open(STARTUP_FILE, "w") as f:
                f.write(sub_cmd)
        elif cmd == "STATUS":
            out("\n".join(skulls.status_lines()))
            return
        elif cmd == "HELP":
            out(HELP_TEXT)
            return
        else:
            out("ERR unknown command: %s" % cmd)
            return
        out("OK")
    except Exception as e:
        # broad by design: an uncaught exception would kill main()'s loop
        out("ERR %s: %s" % (type(e).__name__, e))


def load_startup_command():
    try:
        with open(STARTUP_FILE) as f:
            return f.read().strip() or STARTUP_COMMAND
    except OSError:
        return STARTUP_COMMAND


def main():
    handle_command(load_startup_command())
    print("Halloween skulls ready (%d ornaments, %d LEDs). Send HELP for commands." % (len(CHAIN), NUM_LEDS))

    wdt = WDT(timeout=WDT_TIMEOUT_MS)
    mqtt = SkullsMQTT(handle_command, get_power=lambda: skulls.power, feed=wdt.feed)

    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    last_tick = time.ticks_ms()
    buf = ""

    while True:
        now = time.ticks_ms()
        wdt.feed()

        if poll.poll(0):
            ch = sys.stdin.read(1)
            if ch in ("\n", "\r"):
                if buf:
                    handle_command(buf)
                    buf = ""
            elif ch:
                buf += ch

        mqtt.poll()

        if time.ticks_diff(now, last_tick) >= TICK_MS:
            last_tick = now
            skulls.render(now)


if __name__ == "__main__":
    main()
