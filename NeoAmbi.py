#!/usr/bin/python
# Must be run under sudo
# Requires: sudo pip3 install rpi_ws281x

import colorsys
import os
import pwd
import grp
import glob
import logging
from logging.handlers import RotatingFileHandler
from time import sleep, time
from datetime import datetime
import _rpi_ws281x as ws

# Configuration Constants
LED_COUNT = 30  # Number of LEDs
LED_CHANNEL = 0  # Channel
LED_FREQ_HZ = 800000  # Frequency of the LED signal
LED_DMA_NUM = 5  # DMA channel to use
LED_GPIO = 18  # GPIO connected to the LED signal line
LED_INVERT = 0  # Signal inversion
QUIET_HOURS_START = 23  # Start of quiet hours
QUIET_HOURS_END = 6  # End of quiet hours
LOG_PATH = 'led_brightness.log'

def set_file_ownership(file_path, user, group):
    """Change the ownership of the specified file."""
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid
        os.chown(file_path, uid, gid)
    except Exception as e:
        logging.warning(f"Failed to set ownership of {file_path}: {e}")

def fix_log_file_ownerships(log_path, user, group):
    """Ensure ownership of all log files."""
    log_files = glob.glob(f"{log_path}*")
    for log_file in log_files:
        set_file_ownership(log_file, user, group)

# Logging Configuration
LOG_HANDLER = RotatingFileHandler(
    filename=LOG_PATH,
    maxBytes=4 * 1024 * 1024,  # 4 MB per log file
    backupCount=7  # Keep up to 7 backup log files
)
LOG_HANDLER.namer = lambda name: f"{name}"
LOG_HANDLER.rotator = lambda source, dest: (
    os.rename(source, dest),
    fix_log_file_ownerships(LOG_PATH, 'pi', 'pi')
)

logging.basicConfig(
    handlers=[LOG_HANDLER],
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initial log file ownership setup
fix_log_file_ownerships(LOG_PATH, 'pi', 'pi')

class LEDController:
    """Encapsulates LED operations."""
    
    def __init__(self, count, gpio, channel, freq, dma, invert):
        self.count = count
        self.leds = ws.new_ws2811_t()

        # Configure LED channel
        self.channel_config = ws.ws2811_channel_get(self.leds, channel)
        ws.ws2811_channel_t_count_set(self.channel_config, count)
        ws.ws2811_channel_t_gpionum_set(self.channel_config, gpio)
        ws.ws2811_channel_t_invert_set(self.channel_config, invert)

        ws.ws2811_t_freq_set(self.leds, freq)
        ws.ws2811_t_dmanum_set(self.leds, dma)

        # Initialize LED
        resp = ws.ws2811_init(self.leds)
        if resp != 0:
            raise RuntimeError(f'ws2811_init failed with code {resp}')

    def set_color(self, index, color):
        """Set the color of a single LED."""
        ws.ws2811_led_set(self.channel_config, index, color)

    def render(self):
        """Render the current LED states."""
        resp = ws.ws2811_render(self.leds)
        if resp != 0:
            raise RuntimeError(f'ws2811_render failed with code {resp}')

    def cleanup(self):
        """Turn off all LEDs and clean up resources."""
        for i in range(self.count):
            self.set_color(i, 0)
        self.render()
        ws.ws2811_fini(self.leds)
        ws.delete_ws2811_t(self.leds)

def to_neopixel_color(r, g, b):
    """Convert RGB values to NeoPixel format."""
    r, g, b = max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b))
    return ((int(r * 255) & 0xff) << 16 | (int(g * 255) & 0xff) << 8 | (int(b * 255) & 0xff))

def is_led_time_allowed():
    """Return True if the current time is outside quiet hours."""
    now = datetime.now()
    return not (QUIET_HOURS_START <= now.hour or now.hour < QUIET_HOURS_END)

def get_brightness():
    """Calculate brightness based on the time of day."""
    now = datetime.now()
    hour = now.hour
    if QUIET_HOURS_END <= hour < (QUIET_HOURS_START - 9):
        return min(10 + (hour - QUIET_HOURS_END) * 12, 100)
    elif (QUIET_HOURS_START - 9) <= hour < (QUIET_HOURS_START - 8):
        return 100
    elif (QUIET_HOURS_START - 8) <= hour < QUIET_HOURS_START:
        return max(94 - (hour - (QUIET_HOURS_START - 8)) * 12, 10)
    else:
        return 0

def log_brightness_periodically():
    """Log brightness 1 minute before the hour."""
    now = datetime.now()
    if now.minute in {59, 0}:
        brightness = get_brightness()
        logging.info(f'Brightness: {brightness}% | Hour: {now.hour} | Minute: {now.minute}')

def set_led_color(controller, index, fraction_of_minute):
    """Set the color of an LED based on its position and time."""
    p = index / float(controller.count)
    q = (p + fraction_of_minute) % 1.0
    r, g, b = colorsys.hsv_to_rgb(q, 1.0, 1.0)
    controller.set_color(index, to_neopixel_color(r, g, b))

# Main Execution
led_controller = LEDController(
    count=LED_COUNT,
    gpio=LED_GPIO,
    channel=LED_CHANNEL,
    freq=LED_FREQ_HZ,
    dma=LED_DMA_NUM,
    invert=LED_INVERT
)

try:
    while True:
        log_brightness_periodically()
        brightness = get_brightness()

        if is_led_time_allowed() and brightness > 0:
            ws.ws2811_channel_t_brightness_set(led_controller.channel_config, int(brightness * 255 / 100))
            fraction_of_minute = (time() % 60.0) / 60.0
            for i in range(LED_COUNT):
                set_led_color(led_controller, i, fraction_of_minute)
            led_controller.render()
        else:
            for i in range(LED_COUNT):
                led_controller.set_color(i, 0)
            led_controller.render()

        fix_log_file_ownerships(LOG_PATH, 'pi', 'pi')  # Ensure ownership periodically
        sleep(0.3)

finally:
    led_controller.cleanup()
    logging.info("LED cleanup complete.")
