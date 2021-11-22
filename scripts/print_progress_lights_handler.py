#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update Print Progress lights.
"""

import atexit
import sys
import requests
import json
import logging
from time import sleep
from logging.handlers import RotatingFileHandler

## Moonraker setup
moonraker_url = "http://localhost:7125"
request_header = {'X-Api-Key': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'}
log_location = '/tmp/lights_progress.log'
wled_host = 'http://192.168.20.251/json/state'
wled_headers = {'content-type': 'application/json'}
check_interval = 10

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
log = logging.getLogger('progress_lights')

def update_wled_progress(percent_complete):
    wled_payload = {
      "on": True,
      "bri": 112,
      "transition": 7,
      "mainseg": 0,
      "seg": [
        {
          "id": 0,
          "start": 0,
          "stop": 28,
          "grp": 1,
          "spc": 0,
          "of": 0,
          "on": True,
          "bri": 171,
          "col": [
            [
              8,
              255,
              0,
              0
            ],
            [
              0,
              0,
              255,
              0
            ],
            [
              0,
              0,
              0,
              0
            ]
          ],
          "fx": 98,
          "sx": 39,
          "ix": percent_complete,
          "pal": 2,
          "sel": True,
          "rev": False,
          "mi": False
        },
        {
          "id": 1,
          "start": 28,
          "stop": 56,
          "grp": 1,
          "spc": 0,
          "of": 0,
          "on": True,
          "bri": 106,
          "col": [
            [
              13,
              0,
              255,
              0
            ],
            [
              0,
              0,
              0,
              0
            ],
            [
              0,
              0,
              0,
              0
            ]
          ],
          "fx": 65,
          "sx": 41,
          "ix": 50,
          "pal": 11,
          "sel": False,
          "rev": False,
          "mi": False
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        },
        {
          "stop": 0
        }
      ]
    }
    sender = requests.post(wled_host, headers=wled_headers, json=wled_payload)
    log.info('Sending upate to WLED. Progress: {}%'.format(percent_complete))

def get_printing_state():
    print_progress = 0
    klipper_info = requests.get('{}/printer/objects/query?display_status&print_stats'.format(moonraker_url), headers=request_header).json()
    try:
        printing_state = klipper_info['result']['status']['print_stats']['state'].lower()
        if printing_state == 'printing':
            try:
                print_progress = klipper_info['result']['status']['display_status']['progress']
            except Exception as e:
                log.error("Could not get print progress Error: {}".format(e))
    except Exception as e:
        log.error("Could not get printing state Error: {}".format(e))
    log.info("Printing State: {} Print Completion: {}%".format(printing_state.upper(), round((print_progress * 100))))
    return printing_state, round((print_progress * 100))

log.info('Starting Print Progress WLED Handler...')
while True:
    state = get_printing_state()
    if state[0] == 'printing':
        update_wled_progress(state[1])
        log.debug('Checking again in {} seconds...'.format(check_interval))
        sleep(check_interval)
    else:
        log.debug('Checking again in {} seconds...'.format(check_interval))
        sleep(check_interval)
