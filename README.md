# NeoAmbi

A Python-based screen ambient lighting system for Raspberry Pi. Captures the average color of screen regions in real time and drives a NeoPixel (WS2812B) RGB LED strip to produce immersive ambient backlight that mirrors your display.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Requirements](#requirements)
3. [Wiring Diagram](#wiring-diagram)
4. [File Overview](#file-overview)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Troubleshooting](#troubleshooting)
9. [Version History](#version-history)

---

## How It Works

Once running, NeoAmbi enters a continuous capture-and-render loop that:

- **Captures the screen** at a configurable interval using a screenshot library, dividing the display into zones that correspond to sections of the LED strip.
- **Samples the dominant color** of each zone by averaging pixel values, optionally with brightness and saturation scaling applied.
- **Writes color data to the NeoPixel strip** via the `rpi_ws281x` library over GPIO, updating each LED to match its corresponding screen zone.
- **Applies smoothing** between frames to prevent harsh flickering when the on-screen content changes abruptly.
- **Respects a configurable brightness cap** so the strip does not draw excessive current from the Raspberry Pi power supply.

---

## Requirements

### Hardware

- Raspberry Pi (3B, 4, or 5 recommended)
- WS2812B (NeoPixel) LED strip
- 5 V / 3 A or greater power supply (separate from the Pi — do not power the strip from the Pi's 5 V rail)
- 300–470 Ω resistor on the data line
- 1000 µF capacitor across the strip's power input (recommended)
- Jumper wires

### Software

- Python 3.7 or later
- The following packages (install via pip):

```
rpi_ws281x
Pillow
numpy
```

> **Note:** `rpi_ws281x` requires root privileges to access hardware PWM. Run the script with `sudo`.

---

## Wiring Diagram

```
Raspberry Pi                   WS2812B LED Strip
─────────────                  ─────────────────
GPIO 18 (PWM) ──[300Ω]──────►  DIN  (Data In)
GND           ───────────────►  GND
                               +5V  ◄─── External 5V PSU (+)
                               GND  ◄─── External 5V PSU (–)
                                              │
                                      [1000µF cap]
                                              │
                                             GND
```

### Pin Reference

| Component           | Pi Pin | GPIO  | Notes                          |
|---------------------|--------|-------|--------------------------------|
| LED Strip Data Line | Pin 12 | GPIO 18 | Hardware PWM — do not change without updating config |
| LED Strip Ground    | GND    | —     | Shared ground with external PSU |
| External PSU +5V    | —      | —     | Connect directly to strip VCC  |
| External PSU GND    | GND    | —     | Tie Pi GND to PSU GND          |

> **Warning:** Never power more than a few LEDs directly from the Pi's 5 V rail. Use a dedicated PSU rated for your strip length (60 LEDs × 60 mA max = 3.6 A peak).

---

## File Overview

| File           | Purpose |
|----------------|---------|
| `NeoAmbi.py`   | Main script — capture loop, color sampling, and LED output |
| `.gitignore`   | Git ignore rules |
| `README.md`    | This file |

---

## Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/maserowik/NeoAmbi.git
cd NeoAmbi
```

### Step 2 — Install system dependencies

```bash
sudo apt update
sudo apt install python3-pip python3-dev libopenjp2-7 libtiff5 -y
```

### Step 3 — Install Python packages

```bash
sudo pip3 install rpi_ws281x Pillow numpy
```

### Step 4 — Configure the script

Edit the configuration constants at the top of `NeoAmbi.py` to match your hardware. See [Configuration](#configuration) for details.

### Step 5 — Run

```bash
sudo python3 NeoAmbi.py
```

> `sudo` is required for hardware PWM access via `rpi_ws281x`.

---

### Running at Startup (Optional)

To launch NeoAmbi automatically on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/neoambi.service
```

Paste the following:

```ini
[Unit]
Description=NeoAmbi Ambient Lighting
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/NeoAmbi/NeoAmbi.py
WorkingDirectory=/home/pi/NeoAmbi
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable neoambi
sudo systemctl start neoambi
```

---

## Configuration

All configuration is handled by constants near the top of `NeoAmbi.py`. Edit these before running.

```python
# ── LED Strip ──────────────────────────────────────────────────
LED_COUNT      = 60        # Total number of LEDs on the strip
LED_PIN        = 18        # GPIO pin (must support PWM — GPIO 18 recommended)
LED_FREQ_HZ    = 800000    # LED signal frequency in Hz (800 kHz for WS2812B)
LED_DMA        = 10        # DMA channel for signal generation
LED_BRIGHTNESS = 150       # Global brightness (0–255); keep below 200 to limit current draw
LED_INVERT     = False     # True if using an inverting level shifter

# ── Screen Capture ─────────────────────────────────────────────
CAPTURE_INTERVAL_MS = 50   # Milliseconds between screen captures (lower = more responsive)
SCREEN_WIDTH        = 1920 # Your display resolution width
SCREEN_HEIGHT       = 1080 # Your display resolution height

# ── Color Processing ───────────────────────────────────────────
SMOOTHING_FACTOR    = 0.3  # Blend factor between frames (0.0 = instant, 1.0 = no change)
SATURATION_BOOST    = 1.2  # Multiply color saturation (1.0 = no boost)
BLACK_THRESHOLD     = 10   # Pixel brightness below this value is treated as off
```

### Configuration Reference

| Constant | Default | Description |
|----------|---------|-------------|
| `LED_COUNT` | `60` | Number of LEDs on your strip |
| `LED_PIN` | `18` | GPIO data pin — GPIO 18 is required for hardware PWM |
| `LED_BRIGHTNESS` | `150` | Master brightness cap (0–255) |
| `CAPTURE_INTERVAL_MS` | `50` | Screen poll rate in milliseconds (~20 fps) |
| `SCREEN_WIDTH` / `SCREEN_HEIGHT` | `1920` / `1080` | Must match your display resolution |
| `SMOOTHING_FACTOR` | `0.3` | Higher values produce smoother but slower transitions |
| `SATURATION_BOOST` | `1.2` | Values above 1.0 make colors more vivid |
| `BLACK_THRESHOLD` | `10` | Prevents dim scenes from producing faint unwanted color |

> **Tip:** If your strip flickers, increase `SMOOTHING_FACTOR`. If colors feel sluggish to respond, decrease it.

---

## Usage

Start the script with sudo:

```bash
sudo python3 NeoAmbi.py
```

The strip will immediately begin mirroring the screen. To stop, press `Ctrl+C` — the strip will be cleared on exit.

### Adjusting Brightness at Runtime

Modify `LED_BRIGHTNESS` in the script and restart. Do not exceed 200 unless your power supply is rated for the full current draw of your strip length.

### Turning the Strip Off Without Stopping the Script

Lower `LED_BRIGHTNESS` to `0` in `NeoAmbi.py` and restart, or send a `SIGTERM` to the process — the shutdown handler clears all LEDs before exiting.

---

## Troubleshooting

### Strip does not light up

- Confirm you are running with `sudo`.
- Verify `LED_PIN` is set to `18` (hardware PWM is required).
- Check that `LED_COUNT` matches the actual number of LEDs on your strip.
- Confirm your external 5 V PSU is powered and the ground is shared with the Pi.

### Colors are wrong / strip shows incorrect colors

- WS2812B LEDs use GRB color order, not RGB. If colors are swapped, verify the color order setting in the `rpi_ws281x` initializer inside `NeoAmbi.py`.
- Check the data line for voltage level issues — a 300–470 Ω resistor on DIN is required.

### Script crashes with "Permission denied" or PWM error

- Ensure you are running as root with `sudo`.
- Confirm no other process is using GPIO 18 or DMA channel 10.
- Reboot the Pi and try again.

### LEDs flicker or behave erratically

- Add a 1000 µF capacitor across the strip's VCC and GND at the input end.
- Shorten or replace the data wire — keep it under 1 metre where possible.
- Increase `SMOOTHING_FACTOR` to reduce rapid color changes.

### Screen capture is slow / high CPU usage

- Increase `CAPTURE_INTERVAL_MS` to reduce capture frequency.
- Reduce `SCREEN_WIDTH` and `SCREEN_HEIGHT` to match a lower-resolution capture region.
- Consider lowering the Pi's desktop resolution if ambient accuracy is acceptable at a lower res.

### Strip stays lit after script exits

- The exit handler should clear the strip on clean exits (`Ctrl+C`).
- If the script is killed forcefully (`kill -9`), the strip will hold its last state. Restart the script and exit cleanly, or cycle power to the strip.

---

## Version History

- **v2.0 — NeoAmbi Update (Current)**
  - Rewrote capture and color-sampling pipeline for improved performance
  - Added per-frame smoothing to reduce flickering
  - Added saturation boost and black threshold configuration
  - Improved shutdown handling to reliably clear the strip on exit

- **v1.0 — Initial Release**
  - Basic screen capture and NeoPixel color output
  - Single-zone color averaging
  - GPIO 18 PWM output via `rpi_ws281x`

---

## Acknowledgments

Built on the [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) library by Jeremy Garff. Screen capture powered by [Pillow](https://python-pillow.org/). Inspired by the Philips Ambilight concept.
