# halloween_skulls

Two 3D-printed Halloween skulls with NeoPixel eyes, each driven by a Raspberry Pi Pico W and controlled from openHAB.

## Parts list

Quantities are per skull, with the total for two skulls in the last column.

| Part | Per skull | Total | Notes |
|---|---|---|---|
| Raspberry Pi Pico W (with headers) | 1 | 2 | Wi-Fi for MQTT/openHAB control |
| 5 mm through-hole NeoPixel (WS2812D-F5 / PL9823-F5 type) | 2 | 4 | One per eye. The eye bores are sized for a 5.0 mm body with a 5.8 mm flange (`LED_D` / `LED_FLANGE_D` in `build_skull.py`). Diffused lenses look best |
| 0.1 µF ceramic capacitor | 2 | 4 | One across each LED's 5V/GND pins. Through-hole NeoPixels have no onboard decoupling |
| 74AHCT125 (or SN74AHCT1G125) level shifter | 1 | 2 | Shifts the Pico's 3.3 V data up to 5 V. 3.3 V is below the LEDs' 0.7 × VDD input threshold |
| 330–470 Ω resistor | 1 | 2 | In series with the data line, at the first LED |
| 10–100 µF electrolytic capacitor | 1 | 2 | Bulk capacitor across 5V/GND near the LEDs |
| Micro-USB cable + 5 V USB power supply (≥1 A) | 1 | 2 | Powers the Pico. The LEDs run from the Pico's VBUS pin: 2 LEDs × 60 mA max plus the Pico is well under 1 A |
| 4-conductor thin wire (e.g. 28–30 AWG ribbon or silicone) | ~30 cm | ~60 cm | 5V, GND, and data in/out between the two eyes and out the base wire slot (5 × 3 mm) |
| Small perfboard or protoboard | 1 | 2 | Holds the level shifter, resistor, and bulk cap next to the Pico |
| Heat-shrink tubing | — | — | For the LED leg joints inside the skull |
| PLA/PETG filament | ~1 print | 2 prints | `halloween-skull/skull.stl`. The skull is 50 mm wide |

The Pico W (51 × 21 mm) doesn't fit through the skull's 18 mm base opening. It sits outside, in a small box or under the display stand, and the LED wires run out through the slot in the back of the base.
