#!/usr/bin/env python3
"""
Manage klipper/moonraker with asyncio and GPIOs.
"""

import RPi.GPIO as GPIO
import atexit
import sys
import asyncio
import requests
import json
import logging
from time import sleep

## Moonraker setup
moonraker_url = "http://localhost:7125"
power_device = "MCU"
shutdown_macro = "POWER_OFF_MCU"
request_header = {'X-Api-Key': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'}
## GPIO setup
green = 21
front_red = 20
blue = 16
side_red = 12
## Async
loop = None
timer = None
## Log location
log_location = '/tmp/gpio_buttons.log'
## GPIO lookup
gpio_lookup = {
21: 'Green',
20: 'Front Red',
16: 'Blue',
12: 'Side Red'
}
## Button state mapping
state_lookup = {
1: "RELEASED",
0: "PRESSED"
}
# Timer
bouncetime = 1000  # in ms

# Set up the log file
logging.basicConfig(
    filename=log_location,
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('GPIO_Buttons')

class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


async def timeout_callback():
    log.debug("timeout callback")

def get_klipper_state():
    klipper_info = requests.get('{}/printer/info'.format(moonraker_url), headers=request_header).json()
    try:
        klipper_state = klipper_info['error']['message']
    except:
        klipper_state = klipper_info['result']['state']
    log.debug("Current klipper state is {}".format(klipper_state.upper()))
    return klipper_state.lower()

def mcu_startup():
    log.debug("MCU startup called")
    mcu_boot = requests.post('{}/machine/device_power/device?device={}&action=on'.format(moonraker_url, power_device), headers=request_header)
    return

def mcu_shutdown():
    log.debug("MCU shutdown was called")
    button_state = read_button_state(side_red, 2.00)
    if button_state:
        log.debug("Button {} triggered but it was not held down for 2 seconds".format(gpio_lookup[side_red]))
    else:
        log.debug("Calling MCU shutdown now!")
        mcu_boot = requests.post('{}/printer/gcode/script?script={}'.format(moonraker_url, shutdown_macro), headers=request_header)
    return

def firmware_restart():
    log.debug("Initiating firmware restart...")
    mcu_boot = requests.post('{}/printer/firmware_restart'.format(moonraker_url), headers=request_header)
    return

def restart_klipper_service():
    log.debug("Restarting the klipper service...")
    mcu_boot = requests.post('{}/machine/services/start?service=klipper'.format(moonraker_url), headers=request_header)
    return

def check_klipper_restart():
    log.info("Checking klipper state... Waiting 20 seconds...")
    sleep(20)
    klipper_state = get_klipper_state()
    if klipper_state != "ready":
        log.info("Initating a firmware restart...")
        firmware_restart()
        log.info("Waiting 10 seconds to check klipper's state and see if a service restart is required...")
        sleep(10)
        klipper_state = get_klipper_state()
        if klipper_state != "ready":
            restart_klipper_service()
        else:
            log.info("Klipper service restart aborted. Klipper is in {} state".format(klipper_state.upper()))
    else:
        log.info("Klipper firmware restart aborted. Klipper is in {} state".format(klipper_state.upper()))

def printer_startup():
    mcu_startup()
    check_klipper_restart()

def send_macro(macro):
    requests.post('{}/printer/gcode/script?script={}'.format(moonraker_url, macro), headers=request_header)

def front_red_action():
    return

def green_action():
    return

def blue_action():
    send_macro('PREHEAT_ABS_PC')

def read_button_state(gpio,time):
    sleep(time)
    state = GPIO.input(gpio)
    log.debug("STATE_CHECK: Current state of {} is {}...".format(gpio_lookup[gpio], state_lookup[state]))
    return state

def button_pushed(gpio):
    if loop is None:
        log.error("Loop ended")
        return  # should not come to this
    button_state = read_button_state(gpio, 0.10)
    if button_state:
        log.debug("Button {} was triggered but is not being pressed".format(gpio_lookup[gpio]))
    else:
        klippy_state = get_klipper_state()
        if klippy_state == "ready":
            if gpio == front_red:
                log.info("Front Red button was triggered!")
                loop.call_soon_threadsafe(front_red_action)
            if gpio == green:
                log.info("Green button was triggered!")
                loop.call_soon_threadsafe(green_action)
            if gpio == blue:
                log.info("Blue button was triggered!")
                loop.call_soon_threadsafe(blue_action)
            if gpio == side_red:
                log.info("Side Red button was triggered!")
                loop.call_soon_threadsafe(mcu_shutdown)
        elif klippy_state == "idle":
            if gpio == blue:
                log.info("Blue button was triggered!")
                loop.call_soon_threadsafe(blue_action)
        elif klippy_state == "shutdown" or "service unavailable":
            if gpio == side_red:
                loop.call_soon_threadsafe(printer_startup)
            else:
                log.info("Klipper is in {} state. Button {} was pressed. Ignoring!".format(gpio_lookup[gpio], klippy_state.upper()))
        else:
            log.info("Klipper is in {} state. Button {} was pressed. Ignoring!".format(gpio_lookup[gpio], klippy_state.upper()))

def exit_handler():
    log.info('Exit Handler')
    GPIO.cleanup()
    loop.close()

# GPIO
try:
    GPIO.setwarnings(True)  # Set warnings
    GPIO.setmode(GPIO.BCM)  # Use GPIO numbering

    # Set pins to input/output
    GPIO.setup(front_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(green, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(blue, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(side_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(
        green, GPIO.FALLING, callback=button_pushed, bouncetime=bouncetime,
    )
    GPIO.add_event_detect(
        front_red, GPIO.FALLING, callback=button_pushed, bouncetime=bouncetime,
    )
    GPIO.add_event_detect(
        blue, GPIO.FALLING, callback=button_pushed, bouncetime=bouncetime,
    )
    GPIO.add_event_detect(
        side_red, GPIO.FALLING, callback=button_pushed, bouncetime=bouncetime,
    )

    atexit.register(exit_handler)
    loop = asyncio.get_event_loop()
    loop.run_forever()

except:
    log.error("Error:", sys.exc_info()[0])
