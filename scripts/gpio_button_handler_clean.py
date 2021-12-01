#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from logging.handlers import RotatingFileHandler

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
rfh = logging.handlers.RotatingFileHandler(
    filename=log_location,
    mode='a',
    maxBytes=5*1024*1024,
    backupCount=2,
    encoding=None,
    delay=0
)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        rfh
    ]
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
    log.info("Current klipper state is {}".format(klipper_state.upper()))
    return klipper_state.lower()

def get_printing_state():
    printing_state = ''
    klipper_info = requests.get('{}/printer/objects/query?display_status&print_stats'.format(moonraker_url), headers=request_header).json()
    try:
        printing_state = klipper_info['result']['status']['print_stats']['state'].lower()
    except Exception as e:
        log.error("Could not get printing state Error: {}".format(e))
    log.info("Current printing state is {}".format(printing_state.upper()))
    return printing_state

def mcu_startup():
    log.info("MCU startup called")
    mcu_boot = requests.post('{}/machine/device_power/device?device={}&action=on'.format(moonraker_url, power_device), headers=request_header)
    return

def mcu_shutdown():
    log.info("MCU shutdown was called")
    button_state = read_button_state(side_red, 2.00)
    if button_state:
        log.info("Button {} triggered but it was not held down for 2 seconds".format(gpio_lookup[side_red]))
    else:
        log.info("Calling MCU shutdown now!")
        send_macro(shutdown_macro)

def firmware_restart():
    log.info("Initiating firmware restart...")
    try:
        requests.post('{}/printer/firmware_restart'.format(moonraker_url), headers=request_header)
    except Exception as e:
        log.info("Error restarting firmware Error: {}".format(e))

def restart_klipper_service():
    log.info("Restarting the klipper service...")
    try:
        requests.post('{}/machine/services/start?service=klipper'.format(moonraker_url), headers=request_header)
    except Exception as e:
        log.info("Error restarting klipper service Error: {}".format(e))

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
    log.info("Sending macro to klipper: {}".format(macro.upper()))
    try:
        requests.post('{}/printer/gcode/script?script={}'.format(moonraker_url, macro), headers=request_header)
    except Exception as e:
        log.info("Error sending macro to klipper Error: {}".format(e))

def front_red_action():
    return

def green_action():
    return

def blue_action():
    send_macro('PREHEAT_ABS_PC')

def read_button_state(gpio,time):
    sleep(time)
    state = GPIO.input(gpio)
    log.info("STATE_CHECK: Current state of {} is {}...".format(gpio_lookup[gpio], state_lookup[state]))
    return state

def button_pushed(gpio):
    if loop is None:
        log.error("Loop ended")
        return  # should not come to this
    button_state = read_button_state(gpio, 0.10)
    if button_state:
        log.info("Button {} was triggered but is not being pressed".format(gpio_lookup[gpio]))
    else:
        klippy_state = get_klipper_state()
        printing_state = get_printing_state()
        if klippy_state == "ready" and printing_state in ['standby', 'complete']:
            if gpio == blue:
                log.info("Blue button was triggered!")
                loop.call_soon_threadsafe(blue_action)
            if gpio == side_red:
                log.info("Side Red button was triggered!")
                loop.call_soon_threadsafe(mcu_shutdown)
        elif klippy_state == "ready" and printing_state == 'printing':
            log.info("Button {} was pressed. Ignoring! Klipper State: {} Printer State: {}".format(
                                                                                                   gpio_lookup[gpio],
                                                                                                   klippy_state.upper(),
                                                                                                   printing_state.upper()
                                                                                                   ))
        elif klippy_state == "ready" and printing_state != 'printing':
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
        elif klippy_state in ['shutdown', 'service unavailable']:
            if gpio == side_red:
                loop.call_soon_threadsafe(printer_startup)
        else:
            log.info("Button {} was pressed. Ignoring! KLIPPER_STATE: {} PRINTING_STATE: {}".format(
                                                                                                    gpio_lookup[gpio],
                                                                                                    klippy_state.upper(),
                                                                                                    printing_state.upper()
                                                                                                    ))

def exit_handler():
    log.info('Exit Handler')
    GPIO.cleanup()
    loop.close()

# GPIO
log.info("Starting GPIO Button Handler...")
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
