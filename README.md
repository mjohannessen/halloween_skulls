# halloween_skulls

3D-printed Halloween ornaments lit by 5V NeoPixels, driven from one control box and controlled from openHAB.

The control box holds a Raspberry Pi Pico 2 W. It has a power input and one output connector, which carries 5V, GND and data out to a chain of **ornaments**. Each ornament has an input and an output connector and holds one or more 5V NeoPixels. Ornaments plug into each other in any order and any mix, and all their LEDs form one NeoPixel chain:

```
control box ─► ornament 1 ─► ornament 2 ─► … ─► ornament N (output unused)
```

The first set of ornaments is three skulls with one LED each:

```
control box ─► skull 1 (1 LED) ─► skull 2 (1 LED) ─► skull 3 (1 LED)
```

## Control box

### Power

The box runs from either a 5V wall brick or a 5V battery pack. Both have DC5521 (5.5 × 2.1 mm) plugs and share one panel jack, one at a time. The Pico's micro-USB stays reachable for flashing.

```
DC jack + ──┬── chain output 5V (1000 µF across 5V / GND)
            │
            ├── 1N5817 Schottky ─────────────────────┬── Pico VSYS ── 74AHCT125 VCC
            │                                        │
            │   micro-USB ── VBUS ── Pico's onboard diode ──┘
            │
            └── 4.7 kΩ ──┬── GP28 (supply sense)
                         └── 4.7 kΩ ── GND

DC jack − ── GND (common to the Pico, shifter and chain output)
```

- **The LEDs run straight from the DC jack**, not through the Pico, so the chain's current doesn't pass through the Pico or the diode.
- **The Pico runs from VSYS**, fed through diodes from the jack and from USB. Both can be connected at once without either back-feeding the other. VSYS sits at about 4.7V either way (5V less one diode drop).
- **USB alone doesn't power the chain.** USB is for flashing, so a laptop's USB port never has to supply the LEDs.
- **Supply sense:** a 4.7 kΩ / 4.7 kΩ divider puts about 2.5V on GP28 when the jack has power (measured 2.50V), and the lower resistor pulls it to 0V when it doesn't. Other pairs work too if the junction stays between about 2V and 3.2V, i.e. the GND-side resistor is 1–1.5× the jack-side one (10 kΩ / 15 kΩ gives 3.0V); the firmware treats above ~1.5V as "jack present". On USB alone the shifter is still powered from VSYS but the chain isn't, so a high on the data line would feed current into the first LED's data input. The firmware reads GP28 and holds GP22 low unless the jack has power.

### Data

```
Pico GP22 ── 74AHCT125 1A → 1Y ── 330–470 Ω ── chain output DATA
```

The 74AHCT125 shifts the Pico's 3.3V data up to VSYS, about 4.7V, because 3.3V is below the LEDs' 0.7 × 5V = 3.5V input threshold. Only channel 1 is used. The 330–470 Ω resistor (anything in that range works) sits at the shifter's output, limiting current into the first LED's data input and damping ringing on the line.

### Wiring list

Every connection in the box, grouped by net. Pico pin numbers are the physical pins (pin 1 is GP0, next to the USB connector; pins 21–40 run back up the other edge, so pin 40 is opposite pin 1). Do **not** connect anything to the Pico's VBUS (pin 40); the jack feeds VSYS only, through the diode.

| Net | Connects |
|---|---|
| **5V (jack)** | DC jack + (centre pin) · 1N5817 anode · 4.7 kΩ (top) · 1000 µF + leg · JST output red (5V) |
| **VSYS** | 1N5817 cathode (banded end) · Pico pin 39 (VSYS) · 74AHCT125 pin 14 (VCC) · pin 4 (2OE) · pin 10 (3OE) · pin 13 (4OE) · 0.1 µF |
| **GND** | DC jack − (sleeve) · Pico pin 38 (GND) · 74AHCT125 pin 7 (GND) · pin 1 (1OE) · pin 5 (2A) · pin 9 (3A) · pin 12 (4A) · 4.7 kΩ (bottom) · 1000 µF − leg (striped side) · 0.1 µF · JST output GND |
| **Sense** | 4.7 kΩ (top) · 4.7 kΩ (bottom) · Pico pin 34 (GP28 / ADC2) |
| **Data in** | Pico pin 29 (GP22) · 74AHCT125 pin 2 (1A) |
| **Data out** | 74AHCT125 pin 3 (1Y) · 330–470 Ω |
| **Chain DATA** | 330–470 Ω · JST output DATA |

74AHCT125 pins 6 (2Y), 8 (3Y) and 11 (4Y) are outputs and stay unconnected. Its enables are active-low, so 1OE to GND turns channel 1 on and 2OE–4OE to VCC turn the unused channels off. The unused inputs go to GND so they don't float.

Build notes:

- **Placement:** the 0.1 µF goes right at the shifter's pins 14 and 7. The 1000 µF goes where the jack and the JST output wires land on the perfboard, so the chain's current doesn't run through the shifter's ground.
- **Wire gauge:** the jack-to-output 5V and GND carry the whole chain's current (up to 2 A on the 2 A brick), so use 22 AWG there. The Pico and signal wires can be thinner.
- **Wires to the Pico:** with the Pico's USB end at the back wall and its pins facing up, every Pico pin used (29, 34, 38 and 39) is on the edge facing the perfboard. The data pin is GP22 (pin 29) rather than GP0 for that reason: GP0 (pin 1) is on the far edge, so its wire would cross the USB end of the board.
- **Checks before plugging in ornaments:** with only the jack connected, measure about 5V at the JST output's 5V/GND, about 4.7V at VSYS and at the shifter's pin 14, and about 2.5V at GP28. With only USB connected, the JST output's 5V should read 0V.

### Wiring procedure

Step by step, in an order that lets each part be checked before the next goes on. Tick a step when it's done. The board has **two separate positive rails**: **VSYS** (the diode's output, feeding the Pico and the shifter) and **5V (jack)** (feeding the chain). They differ by one diode drop and must never be joined. Ground is one common rail.

Pico pins used: **39** (VSYS), **38** (GND), **34** (GP28, supply sense) and **29** (GP22, data). Nothing goes to pin 40 (VBUS).

There are two separate 5v rails: one for the pico and 74AHCT125 and one for the LED power. All grounds are connected.

**Shifter**

- [x] 1. 74AHCT125 pins 4, 10, 13 and 14 to the VSYS rail.
- [x] 2. 74AHCT125 pins 1, 5, 7, 9 and 12 to the GND rail.
- [x] 3. 0.1 µF between 74AHCT125 pins 7 and 14, as close to the chip as it will go.
- [x] 4. 330–470 Ω from 74AHCT125 pin 3 (1Y) to a free row. Its other end takes the JST DATA wire in step 9.

Pins 2, 6, 8 and 11 are still open at this point: pin 2 gets the Pico in step 10, and 6, 8 and 11 stay unconnected.

**Power** (22 AWG for the jack and chain 5V/GND)

- [x] 5. DC jack + (centre pin) to the 5V (jack) rail, DC jack − (sleeve) to the GND rail.
- [x] 6. 1000 µF across the 5V (jack) rail and GND, where the jack wires land: + leg to 5V, striped − leg to GND.
- [x] 7. 1N5817: anode (plain end) on the 5V (jack) rail, cathode (banded end) on the VSYS rail.
- [x] 8. Supply sense: 4.7 kΩ from the 5V (jack) rail to a free row (the sense row), 4.7 kΩ from the sense row to GND.
- [x] 9. JST output pigtail: red (5V) to the 5V (jack) rail, GND to the GND rail, DATA to the free end of the data resistor.

**Pico** (jack unplugged)

- [x] 10. Pico pin 39 (VSYS) to the VSYS rail, pin 38 (GND) to the GND rail, pin 34 (GP28) to the sense row, pin 29 (GP22) to 74AHCT125 pin 2 (1A).

Wiring is then complete: run the test routine below before plugging in any ornament.

### Test routine

Each stage only adds one thing (power source, software, then LEDs), so a fault shows up at the stage that introduced it. Stop at the first reading that's off. **No ornaments are plugged in until stage 5.** The sense voltage is about **2.5V** with the 4.7 kΩ / 4.7 kΩ divider (3.0V with 10 kΩ / 15 kΩ), written "sense V" below.

**Stage 1: unpowered** (jack and USB both unplugged)

Continuity mode, meter leads on the points named:

| # | Between | Expect | If not |
|---|---|---|---|
| 1.1 | 5V (jack) rail and GND | No beep (a brief chirp is the 1000 µF charging) | Short on the chain supply |
| 1.2 | VSYS rail and GND | No beep | Short on the Pico/shifter supply |
| 1.3 | 5V (jack) rail and VSYS rail | No beep | The two rails are joined somewhere, or the diode is shorted |
| 1.4 | Pico pin 39 and VSYS rail · pin 38 and GND · pin 34 and the sense row · pin 29 and shifter pin 2 | Beep, each | That wire isn't connected |
| 1.5 | Shifter pin 1 and GND · pin 4 and VSYS | Beep, each | Enable pins swapped (pin 1 must be GND) |
| 1.6 | Shifter pin 3 and JST DATA (resistance mode) | 330–470 Ω | Data resistor missing or on the wrong row |
| 1.7 | JST red and the 5V (jack) rail · JST GND and GND | Beep, each | Pigtail miswired. Check its wire colours against the [chain connector](#chain-connector) table |

Diode mode, red lead on the 5V (jack) rail, black on VSYS:

| # | Expect | If not |
|---|---|---|
| 1.8 | About 0.15–0.35V. Swap the leads: OL (open) | Reads OL both ways: diode not in circuit. Low reading only with the leads swapped: diode is backwards |

**Stage 2: USB only** (Pico on the Pi 4's USB, jack unplugged)

| # | Measure | Expect | If not |
|---|---|---|---|
| 2.1 | Pi 4: `lsusb` | A Raspberry Pi device (`2e8a:`) | Pico not powered or bad cable |
| 2.2 | VSYS rail to GND | About 4.6–4.9V (USB through the Pico's own diode) | Pico's VSYS wire, or a short loading it down |
| 2.3 | Shifter pin 14 to pin 7 | Same as 2.2 | Shifter VCC/GND wiring |
| 2.4 | 5V (jack) rail and JST red to GND | 0V (a few tenths at most) | Near 4.5V: USB is feeding the chain, so the diode is backwards or the rails are joined |
| 2.5 | Sense row to GND | 0V | Divider fed from VSYS instead of the jack rail |

Then flash MicroPython (Pico 2 W build: `sudo picotool load -x ~/micropython-pico2-w.uf2` on the Pi 4, with the Pico in BOOTSEL mode) and, still on USB only:

| # | Test | Expect | If not |
|---|---|---|---|
| 2.6 | Read GP28 (ADC2) | Under 0.2V | Same as 2.5 |
| 2.7 | Drive GP22 high, measure JST DATA to GND | About 4.7V (same as VSYS) | 0V: no shifter output. Check pin 1 (1OE) on GND, pin 2 wired to pin 29 |
| 2.8 | Drive GP22 low | 0V | Stuck high: pin 2 not reaching GP22 |

**Stage 3: jack only** (brick or battery pack, USB unplugged)

| # | Measure | Expect | If not |
|---|---|---|---|
| 3.1 | 5V (jack) rail and JST red to GND | About 5.0V | Jack wiring, or centre/sleeve swapped (reads −5V) |
| 3.2 | VSYS rail to GND | About 4.7V (0.2–0.35V below 3.1) | Same as 3.1: jack is wired straight to VSYS. 0V: diode open or backwards |
| 3.3 | Sense row to GND | Sense V | Divider wiring |

**Stage 4: jack and USB together**

| # | Test | Expect | If not |
|---|---|---|---|
| 4.1 | VSYS rail | About 4.7–4.9V, whichever supply is higher | — |
| 4.2 | Read GP28 | Sense V (firmware treats above ~1.5V as "jack present") | Pin 34 wire |
| 4.3 | Unplug the jack, watch GP28 | Falls below 1.5V ("no jack") and keeps falling toward 0V. With no ornaments it takes 10–20 s: the only drain on the 1000 µF is the divider (9.4 kΩ × 1000 µF ≈ 9 s time constant). With ornaments plugged in it drops much faster | Stays at sense V: the GND-side divider resistor is missing |

**Stage 5: first light** (jack and USB connected)

| # | Test | Expect | If not |
|---|---|---|---|
| 5.1 | Plug in **one** skull. Light LED 0 red, then green, then blue, then white, at low brightness | Each colour as named | Wrong colours: the LED's colour order differs. WS2812D is GRB, PL9823 is RGB, so the firmware's order setting must match. Nothing: check the skull's DATA isn't on its output side, and the pigtail order |
| 5.2 | Add the other two skulls. Light each LED in turn (0, 1, 2), then all three | One skull at a time, in chain order, then all | A skull and every one after it dark: that skull's DIN/DOUT or its output pigtail |
| 5.3 | All three white at full brightness for a minute, measure JST red to GND | Still about 5V, nothing warm | Supply sagging under load, or a bad joint heating up |
| 5.4 | With LEDs lit, unplug the jack (USB still in) | LEDs go dark and stay dark | Power is reaching the chain from USB (recheck 2.4) |

**Results (2026-10-11, breadboard build):** every stage passed. USB only: VSYS 4.68V, jack rail 0.01V, GP28 0.004V, shifter pin 2 3.29V / pin 3 4.68V with GP22 high, 0V low. Jack + USB: GP28 2.50V, held at 2.50V through 90 s of all three skulls at full white (no sag). Unplugging the jack: GP28 under 1.5V in ~15 s with no ornaments, ~5 s with three skulls lit, and the skulls went dark on USB alone. The skull LEDs are **GRB** (WS2812D type, MicroPython's default `NeoPixel` order): red, green, blue and white all showed as sent, and the three skulls lit in chain order.

**Battery pack (2026-10-11):** on the KBT 5V pack alone (USB unplugged), three skulls glowing dim red (40,0,0) plus the Pico ran 17.5 minutes with the sense steady at 2.52V (5.04V out) and no auto-shutoff, so the pack is fine at this low a load. The test program logged uptime to the Pico's flash every 30 s; it's a temporary `main.py`, not the real firmware.

## Chain connector

Every connection in the chain is a **JST-SM 3-pin** pigtail pair, the standard WS2812 string connector:

| Wire | Signal |
|---|---|
| Red | 5V |
| Green (or white) | DATA |
| White (or black) | GND |

Wire colours vary between batches. Check the pairs you buy, then use the same pin order everywhere.

- The **box output** and every **ornament output** use the **female** (socket) half, so the live 5V pins are recessed and can't short against anything.
- Every **ornament input** uses the **male** (pin) half.

Any ornament can then plug into the box or into any other ornament. The last ornament's output is still live, so leave its cap on or tape it.

## Ornaments

An ornament is any housing with an input pigtail, one or more 5V NeoPixels in a chain, and an output pigtail:

```
input 5V ───────┬──────────┬──────────────── output 5V
input GND ──────┼────┬─────┼────┬─────────── output GND
input DATA ── DIN LED 1 DOUT ── DIN LED 2 DOUT ── … ── output DATA
            0.1 µF across each LED's 5V / GND
```

- Through-hole NeoPixels (5 mm or 8 mm, WS2812D / PL9823 type) need a 0.1 µF ceramic capacitor across each LED's 5V and GND pins. They have no onboard decoupling. NeoPixels on a PCB or strip already have it.
- 5V and GND run straight through the ornament to its output, so every ornament gets power from the same pair.

### Skull ornament

One 5 mm through-hole NeoPixel sits in the skull's cavity behind the eyes, and its glow comes out through both eye sockets. The input and output pigtails leave through the 18 mm opening in the skull's base.

The skull model (`halloween-skull/build_skull.py`) needs no changes for this. The LED goes in through the base opening, and its light reaches both eyes through the eye-socket bores that open into the cavity.

Each skull sits on a weathered cemetery-stone base (`halloween-skull/build_base.py`, which writes `base.stl`, `base.blend` and `renders/base_*.png` / `assembly_*.png`):

- **Pedestal:** round, 62 mm across and 28.5 mm tall. It has two stepped base courses cut into staggered blocks with mortar joints, a drum with a Gothic lancet niche on each of its four sides, and a projecting cap stone sloping up to the stem. Five crouching winged gargoyles (about 13 mm tall) sit on the cap stone ledge facing outward, one at the front; `GARGOYLES`, `GARGOYLE_R` and `GARGOYLE_SCALE` set their number, position and size. `renders/base_gargoyle.png` is a close-up of one.
- **Stem:** a 20 mm stout stone column on a chamfered base block, flaring at 45° into the seat.
- **Weathering:** the stone is voxel-remeshed and displaced with two scales of noise, and its upper edges are chipped. `SEED` sets the chip pattern, so each skull's base can be different. `WEATHER` sets how rough the surface is. The seat, spigot and wire path are added after weathering, so they stay exact.
- **Seat:** 23 mm across. The skull's underside isn't flat: around its opening it rises from 0.7 mm above the chin plane at the front to about 5 mm at the back. So the seat is cut from the skull model itself (with 0.2 mm clearance for glue) and supports the whole underside. A 16.6 mm spigot, 6 mm tall, fits up into the skull's ~17 mm opening and centres it.
- **Wires:** a 5 mm hole runs down the centre, sized for the LED's four 22 AWG wires (5V, GND, DIN, DOUT), which are glued in place to position the LED inside the skull. Underneath is a 45° cone-shaped cavity for splicing them to the input and output JST pigtails. The pigtails leave through a 12 × 6 mm notch at the back.
- **Printing:** print it as modelled, plinth on the bed, with no supports. Every overhang is 45° or steeper, and the niche tops are pointed arches.

The seat is cut from `skull.blend`, so run `build_skull.py` first if the skull changes, then `build_base.py`:

```sh
Blender -b -P build_skull.py -- <output_dir>
Blender -b -P build_base.py -- <output_dir>
```

Dimensions are mm parameters at the top of `build_base.py`.

## Firmware chain layout

The firmware needs to know which ornaments are in the chain, in order from the box, and how many LEDs each has. It keeps this as a list:

```python
CHAIN = [
    ("skull", 1),
    ("skull", 1),
    ("skull", 1),
]
```

The total LED count is the sum of the counts. Effects address ornaments by position in the list, so a mixed chain needs only this list changed, with no change to the effect code. The plan is to make the layout settable over MQTT, so rearranging ornaments doesn't need a reflash.

## Firmware

MicroPython (v1.28 on the Pico 2 W), in `firmware/`, following led_flowerpot's and lr_light's structure:

| File | What it is |
|---|---|
| `skulls_controller.py` | Deployed as `main.py`. `CHAIN`, command protocol (`HELP_TEXT`), patterns, jack-sense data hold-off, watchdog. |
| `net_mqtt.py` | Wi-Fi + MQTT client (the same as lr_light's, on `skulls/*`). Forwards each `skulls/command` message into `handle_command()`. |
| `wifi_secrets.py` | `WIFI_SSID` / `WIFI_PASSWORD`. Gitignored, never committed; the same file the flowerpot and lamp use, kept on the Pi 4. |

Commands, over MQTT or USB serial: `ON`, `OFF`, `COLOR <zone> r,g,b`, `PATTERN <zone> heartbeat|flicker|breathe|rainbow [args]`, `BRIGHTNESS 0-100`, `SET STARTUP <command>`, `STATUS`, `HELP`. A zone is `all` or an ornament number from `CHAIN` (1 = nearest the box). `HELP_TEXT` is the full reference. Notes:

- **Heartbeat** uses the same lub-dub curve as the flowers' scary stems. A pattern sent to `all` runs on one clock, so every skull beats together.
- **`ON` resumes** the last patterns. It boots **OFF** (`SET STARTUP` can change that), since openHAB's Halloween scene decides when the skulls run.
- **Jack sense:** every tick it reads GP28; without jack power it stops sending data and holds GP22 low. STATUS reports it as `jack=on|off`.
- **Status:** `power=… jack=… brightness=… ornaments=…`, then one `zone=… pattern=… color=… period=…` line per group of ornaments sharing a pattern.

### MQTT topics

Broker: the Mac Mini's Mosquitto, `192.168.1.220:1883`, anonymous.

| Topic | Direction | Payload |
|---|---|---|
| `skulls/command` | in | One command per message |
| `skulls/reply` | out, retained | `OK`, `ERR <type>: <message>`, the STATUS lines, or the HELP text |
| `skulls/status` | out, retained | LWT availability only: `online` / `offline` |
| `skulls/power` | out, retained | `ON` / `OFF`, republished whenever it changes. openHAB's switch uses it as its state topic |

### Deploying

From the Pi 4 (192.168.1.161), with the Pico on its USB:

```bash
# on Mac
scp firmware/skulls_controller.py firmware/net_mqtt.py pi@192.168.1.161:~/Documents/halloween_skulls/firmware/
# on the Pi
cd ~/Documents/halloween_skulls/firmware
cp ~/Documents/led_flowerpot/firmware/wifi_secrets.py .   # first time only
mpremote connect /dev/ttyACM0 mip install umqtt.simple    # first time only
mpremote connect /dev/ttyACM0 cp net_mqtt.py :net_mqtt.py + cp wifi_secrets.py :wifi_secrets.py + cp skulls_controller.py :main.py + reset
```

### Integration

- **openHAB** (house-brain): `things/halloween_skulls.things` (`mqtt:topic:skulls` on the broker bridge), `items/halloween_skulls.items` (`Skulls_Power`, `Skulls_Status`), a "Halloween skulls" sitemap switch, and the Halloween scene in `rules/scenes.rules`: a red heartbeat at the scene's shared BPM, dark with white flashes at the spooky hour's thunder strikes (like the flowers), OFF when the scene ends, and the heartbeat re-sent if they come back online mid-scene.
- **hauss-backend**: `skullsController.js` (on the shared `mqttDevice.js`), `GET /skulls/status` and `POST /skulls/command`, the control page `public/skulls.html`, and the skulls section of `public/api.html`. The pattern list there and `PATTERNS` in `skulls.html` are hand-maintained copies of `HELP_TEXT`.

## Current budget

Each NeoPixel draws up to about 60 mA at full white and about 20 mA for one colour at full brightness. The firmware should cap brightness so the whole chain stays inside the supply.

| Chain | Worst case (full white) |
|---|---|
| 3 skulls × 1 LED | 0.18 A |
| 20 LEDs | 1.2 A |
| 40 LEDs | 2.4 A |

JST-SM connectors and 22 AWG chain wire are good for about 3 A. Above roughly 30 LEDs, or for long cable runs, inject 5V and GND part way along the chain rather than through every connector.

## Parts list

### Control box

| Part | Qty | Notes |
|---|---|---|
| Raspberry Pi Pico 2 W | 1 | Solder wires directly to it rather than fitting headers |
| 74AHCT125 level shifter, DIP-14 | 1 | 3.3V → 5V data. The wiring list uses its DIP-14 pin numbers |
| 330–470 Ω resistor | 1 | In series with the data line, at the shifter output. Any value in that range |
| 1N5817 (or SS14) Schottky diode | 1 | DC jack + → VSYS |
| 4.7 kΩ resistors | 2 | Supply-sense divider to GP28. Other pairs work, see [Power](#power) |
| 1000 µF 10V electrolytic capacitor | 1 | Across 5V / GND at the chain output, absorbs inrush when ornaments are plugged in |
| 0.1 µF ceramic capacitor | 1 | Across the 74AHCT125's VCC / GND |
| Perfboard | 1 | Holds the shifter, resistors, diode and capacitors |
| DC5521 (5.5 × 2.1 mm) female panel-mount barrel jack | 1 | Power input. The same jack as lr_light: 10.75 mm thread in an 11.2 mm hole |
| JST-SM 3-pin female pigtail | 1 | Chain output, through the box wall |
| M3 heat-set inserts and M3 × 6 mm screws | 4 each | Lid to corner posts |
| M2 self-tapping screws, ~5 mm | 4 | Pico 2 W to its standoffs |
| Small zip tie | 1 | Anchors the output pigtail inside the box |

### Power

| Part | Qty | Notes |
|---|---|---|
| 5V wall brick, DC5521 plug, ≥2 A | 1 | 2 A covers about 30 LEDs at full white |
| KBT 5V 8 Ah lithium-ion battery pack (DC5521 lead) | 1 | Battery power, as an alternative to the brick. It has a built-in boost converter, so it gives a regulated 5V. Three skulls glowing red (~60 mA plus the Pico) run for days per charge. Charge it with its own charger |
| DC5521 extension lead, male–female | as needed | If the brick's or battery's lead doesn't reach |

### Per skull ornament

| Part | Qty | Notes |
|---|---|---|
| 5 mm through-hole NeoPixel (WS2812D-F5 / PL9823-F5 type) | 1 | Diffused lens looks best |
| 0.1 µF ceramic capacitor | 1 | Across the LED's 5V / GND pins |
| JST-SM 3-pin pigtail pair | 1 | The male half is the input, the female half the output |
| Heat-shrink tubing | — | For the LED leg joints |

### Chain

| Part | Qty | Notes |
|---|---|---|
| JST-SM 3-pin extension lead | as needed | Between ornaments that sit further apart than their pigtails reach |

## Enclosure (`cad/`)

### Control box

`cad/control_box.FCStd` is the control box and its lid. The box is 88.8 × 77 mm outside and 29 mm tall with the lid on. Every dimension is a cell in the document's `Params` spreadsheet, so edit a cell and press Recompute.

- **Inside:** the Pico 2 W sits on four 5 mm standoffs along the left side, with M2 self-tapping screws. The perfboard sits beside it in a floor cradle, 4 mm up for solder-joint clearance, with no screws.
- **Back wall:** everything plugs in here: the micro-USB slot at the Pico's USB end, the DC jack (11.2 mm hole) and a 5 mm hole for the JST-SM output pigtail's wires. A zip-tie anchor on the floor behind the pigtail hole takes the pull off the solder joints.
- **Lid:** a flat plate whose lip drops 3 mm inside the walls to locate it. Four M3 screws hold it on, through counterbored holes into heat-set inserts in the corner posts.
- **Printing:** print the body open side up and the lid flat face down, both without supports.

| File | What it is |
|---|---|
| `control_box.FCStd` | **The model, edit this.** `Control_box_body` and `Control_box_lid` are the printed parts. The `Components` group holds placeholders (Pico, perfboard, jack, pigtail) for checking fit and isn't printed |
| `stl/control_box_body.stl`, `stl/control_box_lid.stl` | Ready-to-print exports. After editing, re-export with File → Export on each part |
| `control_box.py` | Generates the `.FCStd` from scratch. It only overwrites with `SKULL_OVERWRITE=1 freecadcmd control_box.py`, so hand edits aren't lost |

The perfboard size (48.3 × 44.5 mm), the jack's thread (10.75 mm), its body length inside the box (10 mm) and its nut (14 mm) are measured. The perfboard's components are taken as 12 mm tall (`PERF_H`, with the 1000 µF capacitor lying on its side), which leaves about 6 mm under the lid for wiring. Check them against the built board before printing.

### Earlier two-skull design

`cad/skull_bases.FCStd` and `cad/skull_bases.py` are the earlier design: a control base under the master skull, a stand for the second skull and a JST link between them. The control box and the cemetery-stone skull bases replace them. Only the battery box (`Battery_box_body` / `Battery_box_lid`) is still useful.

## Planned: low-battery alert

The battery pack's boost converter holds its output at 5V until the cells are nearly empty and then cuts off. Measuring the supply voltage gives no warning, and the Pico can't tell the battery from the wall brick, since both supply a regulated 5V through the same jack. So:

- **Power source:** openHAB holds a switch (e.g. `Skulls_On_Battery`) that you turn on when the battery is plugged in, and the firmware reads it over MQTT.
- **Charge estimate:** while on battery, the firmware adds up runtime weighted by LED count and brightness against the pack's ~30 Wh. It saves the total to flash every few minutes so it survives restarts. Turning `Skulls_On_Battery` back on after a recharge resets the counter.
- **MQTT:** it reports the estimate (e.g. `batt_hours=18.5 batt_pct=62`) in its STATUS reply on `skulls/reply`, or on a topic of its own. Not on `skulls/status`, which stays LWT-only (`online`/`offline`) because openHAB treats every message there as availability.
- **openHAB:** at about 20% left, a rule pushes an ntfy alert. If the skulls go offline while on battery, it pushes "Skulls offline — battery probably dead".

If the estimate turns out to be unreliable, an INA219 current sensor in the control box can measure the mAh actually used.
