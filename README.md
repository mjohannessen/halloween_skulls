# halloween_skulls

Two 3D-printed Halloween skulls with NeoPixel eyes, controlled from openHAB.

The master skull sits on a control base that holds a single Raspberry Pi Pico W. The second skull sits on a matching stand. A 3-wire JST link cable (5V, GND, data) runs from the control base to the stand. All four eyes form one NeoPixel chain:

```
Pico W → level shifter → master left eye → master right eye → JST link → second skull left eye → right eye
```

### Power

The control base runs from either the Pico's micro-USB (wall supply) or the 5 V battery pack, which plugs into a DC5521 jack in the back wall. The LEDs and the level shifter are powered from the Pico's **VSYS** rail, not VBUS, so they run from whichever source is connected:

```
micro-USB ── VBUS ── (Pico's onboard diode) ──┐
                                              ├── VSYS ── level shifter VCC, 100 µF, all four LEDs' 5V
DC jack + ── 1N5817 Schottky ─────────────────┘
DC jack − ── GND
```

Each source reaches VSYS through a diode, so both can be connected at once, for example the battery in place and USB plugged in for reflashing, without either one back-feeding the other. VSYS sits at about 4.7 V, which the LEDs and the 74AHCT125 run on happily. VSYS is rated for 5.5 V max, which the regulated pack stays under.

## Parts list

| Part | Qty | Notes |
|---|---|---|
| Raspberry Pi Pico W | 1 | In the control base on 5 mm standoffs, under the perfboard. Solder wires directly to it, because upward headers would hit the perfboard |
| 5 mm through-hole NeoPixel (WS2812D-F5 / PL9823-F5 type) | 4 | Two per skull. The eye bores are sized for a 5.0 mm body with a 5.8 mm flange (`LED_D` / `LED_FLANGE_D` in `build_skull.py`). Diffused lenses look best |
| 0.1 µF ceramic capacitor | 4 | One across each LED's 5V/GND pins. Through-hole NeoPixels have no onboard decoupling |
| 74AHCT125 (or SN74AHCT1G125) level shifter | 1 | Shifts the Pico's 3.3 V data up to 5 V. 3.3 V is below the LEDs' 0.7 × VDD input threshold |
| 330–470 Ω resistor | 1 | In series with the data line, at the level shifter output |
| 100 µF electrolytic capacitor | 1 | Bulk capacitor across 5V/GND on the perfboard |
| Perfboard, 48.3 × 44.5 mm | 1 | Holds the level shifter, resistor and bulk cap. It sits in four corner brackets 16 mm above the floor, stacked over the Pico, with short wires running up from the Pico. A dab of hot glue keeps it in place. The box leaves room for 10 mm-tall components (`PERF_H`), so lay the 100 µF cap on its side if it's taller |
| Micro-USB cable + 5 V USB power supply (≥1 A) | 1 | Wall power, into the Pico's micro-USB. 4 LEDs × 60 mA max plus the Pico is well under 1 A |
| KBT 5 V 8 Ah lithium-ion battery pack (DC5521 lead) | 1 | Battery power, as an alternative to USB. It has a built-in boost converter, so it gives a regulated 5 V. Typical red-eye glow (~100–200 mA) runs for roughly 25–50 hours per charge. Charge it with its own charger |
| DC5521 (5.5 × 2.1 mm) panel-mount jack, M8 thread (DC-099 type) | 1 | In the control base's back wall, for the battery lead. For an 11 mm (DC-022) jack, set `JACK_D` to 11 |
| DC5521 extension lead, male–female, ≤2 m | 1 | From the battery box to the control base, if the pack's own lead is too short |
| 1N5817 (or SS14) Schottky diode | 1 | Jack + → diode → VSYS. Stops USB power from back-feeding the battery when both are plugged in. The Pico's own VBUS diode covers the other direction |
| JST-SM 3-pin pigtail pair (male + female) | 1 | The link between the bases. One pigtail comes out of each base's 6 mm link hole, with the connector outside the box. Add a 3-pin JST-SM extension lead if the skulls sit further apart than the two pigtails reach |
| 3-conductor thin wire (e.g. 28–30 AWG silicone) | ~60 cm | Eye wiring: 5V, GND and data in/out between the two eyes, down through the lid's locating tube |
| M3 heat-set inserts | 8 | Four per base, in the corner posts |
| M3 × 6 mm screws | 8 | Lid screws, four per base |
| M2 × 5 mm self-tapping screws | 4 | Pico W to its standoffs |
| Heat-shrink tubing | — | For the LED leg joints inside the skulls |
| PLA/PETG filament | — | 2 × skull, 1 × control base, 1 × stand, 2 × lid, 1 × battery box + lid |

## Enclosure (`cad/`)

`cad/skull_bases.FCStd` is a parametric FreeCAD document. Every dimension is a cell in its `Params` spreadsheet, so edit a cell and press Recompute. It contains:

- **Control_base_body**: a 67 × 67 × 31.5 mm box. Inside are the Pico W standoffs (micro-USB out the back wall, with the DC5521 battery jack beside it, below the perfboard), four tall corner brackets that hold the perfboard centred above the Pico, and four corner posts for M3 inserts. The link-cable hole is in the right wall.
- **Stand_body**: the same shell, empty inside, with the link-cable hole in the left wall. In the document it's drawn 100 mm to the right of the control base (`STAND_OFFSET`); that offset is for display only.
- **Lid**: print two. A hollow tube on top fits the skull's 18 mm base opening, so the skull sits centred on its base and the eye wires run down through the tube's 11 mm bore. The skull faces the front (−Y) of the box.
- **Battery_box_body / Battery_box_lid**: a plain tray for the battery pack, 2 mm clearance overall plus 3 mm at its lead end (`BATT_L` / `BATT_W` / `BATT_H`, `BB_CLEAR`). The lead leaves through a 6 mm full-height slot in the +X end wall (`BB_SLOT_W`), so the plug never has to fit through it. The lid is a friction fit with no screws (`BB_LIP_CLEAR`). It's drawn `BB_OFFSET` in front of the bases.
- **Components**: Pico W, perfboard and battery pack placeholders for checking fit. Not printed.

Ready-to-print STLs are in `cad/stl/` (`control_base_body.stl`, `stand_body.stl`, `lid_x2.stl`, `battery_box_body.stl`, `battery_box_lid.stl`). After editing the `.FCStd`, re-export them from FreeCAD (File → Export).

`cad/skull_bases.py` generated the document. Re-run it only to start over: `SKULL_OVERWRITE=1 freecadcmd skull_bases.py`. Without that variable it refuses to overwrite the existing `.FCStd`, so hand edits aren't lost.

## Planned: low-battery alert

The battery pack's boost converter holds its output at 5 V until the cells are nearly empty and then cuts off, so measuring the supply voltage gives no warning. The firmware will estimate the charge left instead:

- **Power source:** the Pico W reads VBUS through the WiFi chip (`machine.Pin("WL_GPIO2")` in MicroPython). If USB isn't present, it's running on the battery.
- **Charge estimate:** while on battery, the firmware adds up runtime weighted by LED brightness against the pack's ~30 Wh, and saves the total to flash every few minutes so it survives restarts. The counter resets when the pack is reconnected after charging.
- **MQTT:** it publishes something like `skulls/status {"power":"battery","batt_hours":18.5,"batt_pct":62}`. Its last will publishes `offline` on the same topic, following led_flowerpot's command/reply/status pattern.
- **openHAB:** at about 20% left, a rule pushes an ntfy alert. If the skulls go offline while on battery, it pushes "Skulls offline — battery probably dead".

If the estimate turns out to be unreliable, an INA219 current sensor on the perfboard can measure the mAh actually used.
