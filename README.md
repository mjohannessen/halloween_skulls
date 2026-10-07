# halloween_skulls

Two 3D-printed Halloween skulls with NeoPixel eyes, controlled from openHAB.

The master skull sits on a control base that holds a single Raspberry Pi Pico W. The second skull sits on a matching stand. A 3-wire JST link cable (5V, GND, data) runs from the control base to the stand. All four eyes form one NeoPixel chain:

```
Pico W → level shifter → master left eye → master right eye → JST link → second skull left eye → right eye
```

## Parts list

| Part | Qty | Notes |
|---|---|---|
| Raspberry Pi Pico W | 1 | In the control base. Solder wires directly, or fit headers pointing up: it sits on 5 mm standoffs |
| 5 mm through-hole NeoPixel (WS2812D-F5 / PL9823-F5 type) | 4 | Two per skull. The eye bores are sized for a 5.0 mm body with a 5.8 mm flange (`LED_D` / `LED_FLANGE_D` in `build_skull.py`). Diffused lenses look best |
| 0.1 µF ceramic capacitor | 4 | One across each LED's 5V/GND pins. Through-hole NeoPixels have no onboard decoupling |
| 74AHCT125 (or SN74AHCT1G125) level shifter | 1 | Shifts the Pico's 3.3 V data up to 5 V. 3.3 V is below the LEDs' 0.7 × VDD input threshold |
| 330–470 Ω resistor | 1 | In series with the data line, at the level shifter output |
| 100 µF electrolytic capacitor | 1 | Bulk capacitor across 5V/GND on the perfboard |
| Small perfboard or protoboard | 1 | Holds the level shifter, resistor and bulk cap. The cradle in the control base is sized for 40 × 22 mm; change `PERF_L` / `PERF_W` to match the real board |
| Micro-USB cable + 5 V USB power supply (≥1 A) | 1 | Powers everything. The LEDs run from the Pico's VBUS pin: 4 LEDs × 60 mA max plus the Pico is well under 1 A |
| JST-SM 3-pin pigtail pair (male + female) | 1 | The link between the bases. One pigtail comes out of each base's 6 mm link hole, with the connector outside the box. Add a 3-pin JST-SM extension lead if the skulls sit further apart than the two pigtails reach |
| 3-conductor thin wire (e.g. 28–30 AWG silicone) | ~60 cm | Eye wiring: 5V, GND and data in/out between the two eyes, down through the lid's locating tube |
| M3 heat-set inserts | 8 | Four per base, in the corner posts |
| M3 × 6 mm screws | 8 | Lid screws, four per base |
| M2 × 5 mm self-tapping screws | 4 | Pico W to its standoffs |
| Heat-shrink tubing | — | For the LED leg joints inside the skulls |
| PLA/PETG filament | — | 2 × skull, 1 × control base, 1 × stand, 2 × lid |

## Enclosure (`cad/`)

`cad/skull_bases.FCStd` is a parametric FreeCAD document. Every dimension is a cell in its `Params` spreadsheet, so edit a cell and press Recompute. It contains:

- **Control_base_body**: a 67 × 67 × 26.5 mm box. Inside are the Pico W standoffs (micro-USB out the back wall), the perfboard cradle and four corner posts for M3 inserts. The link-cable hole is in the right wall.
- **Stand_body**: the same shell, empty inside, with the link-cable hole in the left wall. In the document it's drawn 100 mm to the right of the control base (`STAND_OFFSET`); that offset is for display only.
- **Lid**: print two. A hollow tube on top fits the skull's 18 mm base opening, so the skull sits centred on its base and the eye wires run down through the tube's 11 mm bore. The skull faces the front (−Y) of the box.
- **Components**: Pico W and perfboard placeholders for checking fit. Not printed.

Ready-to-print STLs are in `cad/stl/` (`control_base_body.stl`, `stand_body.stl`, `lid_x2.stl`). After editing the `.FCStd`, re-export them from FreeCAD (File → Export).

`cad/skull_bases.py` generated the document. Re-run it only to start over: `SKULL_OVERWRITE=1 freecadcmd skull_bases.py`. Without that variable it refuses to overwrite the existing `.FCStd`, so hand edits aren't lost.
