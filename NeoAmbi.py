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
LED_COUNT = 30
LED_CHANNEL = 0
LED_FREQ_HZ = 800000
LED_DMA_NUM = 5
LED_GPIO = 18
LED_INVERT = 0
QUIET_HOURS_START = 22
QUIET_HOURS_END = 6
LOG_PATH = 'led_brightness.log'

def set_file_ownership(file_path, user, group):
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid
        os.chown(file_path, uid, gid)
    except Exception as e:
        logging.warning(f"Failed to set ownership of {file_path}: {e}")

def fix_log_file_ownerships(log_path, user, group):
    log_files = glob.glob(f"{log_path}*")
    for log_file in log_files:
        set_file_ownership(log_file, user, group)

LOG_HANDLER = RotatingFileHandler(
    filename=LOG_PATH,
    maxBytes=4 * 1024 * 1024,
    backupCount=7
)

def custom_namer(source):
    import os
    base, ext = os.path.splitext(source)
    if base.endswith('.log'):
        base = base[:-4]
    number = ext.lstrip('.')
    if number:
        return f"{base}.{number}.log"
    return f"{base}.log"

LOG_HANDLER.namer = custom_namer

LOG_HANDLER.rotator = lambda source, dest: (
    os.rename(source, dest),
    fix_log_file_ownerships(LOG_PATH, 'pi', 'pi')
)

class LEDController:
    def __init__(self, count, gpio, channel, freq, dma, invert):
        self.count = count
        self.leds = ws.new_ws2811_t()

        self.channel_config = ws.ws2811_channel_get(self.leds, channel)
        ws.ws2811_channel_t_count_set(self.channel_config, count)
        ws.ws2811_channel_t_gpionum_set(self.channel_config, gpio)
        ws.ws2811_channel_t_invert_set(self.channel_config, invert)

        ws.ws2811_t_freq_set(self.leds, freq)
        ws.ws2811_t_dmanum_set(self.leds, dma)

        resp = ws.ws2811_init(self.leds)
        if resp != 0:
            raise RuntimeError(f'ws2811_init failed with code {resp}')

    def set_color(self, index, color):
        ws.ws2811_led_set(self.channel_config, index, color)

    def render(self):
        resp = ws.ws2811_render(self.leds)
        if resp != 0:
            raise RuntimeError(f'ws2811_render failed with code {resp}')

    def cleanup(self):
        for i in range(self.count):
            self.set_color(i, 0)
        self.render()
        ws.ws2811_fini(self.leds)
        ws.delete_ws2811_t(self.leds)

def to_neopixel_color(r, g, b):
    r, g, b = max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b))
    return ((int(r * 255) & 0xff) << 16 |
            (int(g * 255) & 0xff) << 8 |
            (int(b * 255) & 0xff))

def is_led_time_allowed():
    now = datetime.now()
    return not (QUIET_HOURS_START <= now.hour or now.hour < QUIET_HOURS_END)

def get_brightness():
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
    now = datetime.now()
    if now.minute in {59, 0}:
        brightness = get_brightness()
        logging.info(f'Brightness: {brightness}% | Hour: {now.hour} | Minute: {now.minute}')

def set_led_color(controller, index, fraction_of_minute):
    p = index / float(controller.count)
    q = (p + fraction_of_minute) % 1.0
    r, g, b = colorsys.hsv_to_rgb(q, 1.0, 1.0)
    controller.set_color(index, to_neopixel_color(r, g, b))

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

        fix_log_file_ownerships(LOG_PATH, 'pi', 'pi')
        sleep(0.3)

finally:
    led_controller.cleanup()
    logging.info("LED cleanup complete.")
