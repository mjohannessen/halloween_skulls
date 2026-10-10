# halloween_skulls

3D-printed Halloween ornaments lit by 5V NeoPixels, driven from one control box and controlled from openHAB.

The control box holds a Raspberry Pi Pico W. It has a power input and one output connector, which carries 5V, GND and data out to a chain of **ornaments**. Each ornament has an input and an output connector and holds one or more 5V NeoPixels. Ornaments plug into each other in any order and any mix, and all their LEDs form one NeoPixel chain:

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
            └── 10 kΩ ──┬── GP28 (supply sense)
                        └── 15 kΩ ── GND

DC jack − ── GND (common to the Pico, shifter and chain output)
```

- **The LEDs run straight from the DC jack**, not through the Pico, so the chain's current doesn't pass through the Pico or the diode.
- **The Pico runs from VSYS**, fed through diodes from the jack and from USB. Both can be connected at once without either back-feeding the other.
- **USB alone doesn't power the chain.** USB is for flashing, so a laptop's USB port never has to supply the LEDs.
- **Supply sense:** a 10 kΩ / 15 kΩ divider puts about 3.0V on GP28 when the jack has power. The firmware reads it and doesn't drive the chain on USB power alone, because the unpowered LEDs would draw current from the data line.

### Data

```
Pico GP0 ── 74AHCT125 ── 330 Ω ── chain output DATA
```

The 74AHCT125 shifts the Pico's 3.3V data up to about 4.7V, because 3.3V is below the LEDs' 0.7 × VDD input threshold. Tie its unused inputs to GND and its unused enables (1OE…4OE) to VCC. Tie its used enable (1OE) to GND. The 330 Ω resistor sits at the shifter's output and protects the first LED's data input.

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
| Raspberry Pi Pico W | 1 | Solder wires directly to it rather than fitting headers |
| 74AHCT125 (or SN74AHCT1G125) level shifter | 1 | 3.3V → 5V data |
| 330 Ω resistor | 1 | In series with the data line, at the shifter output |
| 1N5817 (or SS14) Schottky diode | 1 | DC jack + → VSYS |
| 10 kΩ and 15 kΩ resistors | 1 each | Supply-sense divider to GP28 |
| 1000 µF 10V electrolytic capacitor | 1 | Across 5V / GND at the chain output, absorbs inrush when ornaments are plugged in |
| 0.1 µF ceramic capacitor | 1 | Across the 74AHCT125's VCC / GND |
| Perfboard | 1 | Holds the shifter, resistors, diode and capacitors |
| DC5521 (5.5 × 2.1 mm) panel-mount jack, M8 thread (DC-099 type) | 1 | Power input |
| JST-SM 3-pin female pigtail | 1 | Chain output, through the box wall |

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

`cad/skull_bases.FCStd` and `cad/skull_bases.py` are the **earlier two-skull design**: a control base under the master skull, a stand for the second skull and a JST link between them. They still need redoing for this design: a standalone control box (Pico W, perfboard, DC jack, micro-USB access, JST output) and a base for each skull with its input and output pigtails.

The parametric approach stays the same. Every dimension is a cell in the document's `Params` spreadsheet, so edit a cell and press Recompute. `skull_bases.py` regenerates the document from scratch, and only runs with `SKULL_OVERWRITE=1 freecadcmd skull_bases.py`, so hand edits aren't lost.

## Planned: low-battery alert

The battery pack's boost converter holds its output at 5V until the cells are nearly empty and then cuts off. Measuring the supply voltage gives no warning, and the Pico can't tell the battery from the wall brick, since both supply a regulated 5V through the same jack. So:

- **Power source:** openHAB holds a switch (e.g. `Skulls_On_Battery`) that you turn on when the battery is plugged in, and the firmware reads it over MQTT.
- **Charge estimate:** while on battery, the firmware adds up runtime weighted by LED count and brightness against the pack's ~30 Wh. It saves the total to flash every few minutes so it survives restarts. Turning `Skulls_On_Battery` back on after a recharge resets the counter.
- **MQTT:** it publishes something like `skulls/status {"power":"battery","batt_hours":18.5,"batt_pct":62}`. Its last will publishes `offline` on the same topic, following led_flowerpot's command/reply/status pattern.
- **openHAB:** at about 20% left, a rule pushes an ntfy alert. If the skulls go offline while on battery, it pushes "Skulls offline — battery probably dead".

If the estimate turns out to be unreliable, an INA219 current sensor in the control box can measure the mAh actually used.
