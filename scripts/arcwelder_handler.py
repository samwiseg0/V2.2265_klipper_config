#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Global Settings
path = '/home/pi/gcode_files'
go_recursively = True
patterns = ['*.gcode']
ignore_patterns = ['*.arcw.gcode', '*noarc*.gcode']
ignore_directories = True
case_sensitive = False
log_location = '/tmp/arc_welder.log'

# Arc Welder Settings
arc_welder_location = '/home/pi/bin/ArcWelder'
delete_source = True

# Klipper Estimator Settings
process_estimate = True
klipper_estimator_location = '/home/pi/klipper_estimator/target/release/klipper_estimator'
moonraker_location = 'http://localhost'

# Cancel Object Processor Settings
process_cancellation = True
python3_location = '/usr/bin/python3'
preprocess_cancellation = '/home/pi/cancelobject-preprocessor/preprocess_cancellation.py'

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
log = logging.getLogger('ArcWelder')

file_observer = Observer()

def cancelobject_preprocessor(source_file):
    command = f"\042{python3_location}\042 \042{preprocess_cancellation}\042 \042{source_file}\042"
    log.info("Spawning command:{}".format(command))
    co_process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True).wait()

def klipper_estimator(source_file):
    command = f"\042{klipper_estimator_location}\042 --config_moonraker_url \042{moonraker_location}\042 post-process \042{source_file}\042"
    log.info("Spawning command:{}".format(command))
    kest_process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True).wait()

def append_arc(filename):
    path = Path(filename)
    return path.with_name(f"{path.stem}.arcw{path.suffix}")

def file_processor(source_file, des_file):
    # Spawn cancel objects processor if enabled
    if process_cancellation:
        cancelobject_preprocessor(source_file)

    # Spawn klipper estimator if enabled
    if process_estimate:
        klipper_estimator(source_file)
    
    time.sleep(1)
    
    # Spawn arc welder
    command = f"\042{arc_welder_location}\042 \042{source_file}\042 \042{des_file}\042"
    log.info("Spawning command:{}".format(command))
    arc_process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
    
    # Send stdout to log file
    with arc_process.stdout:
        try:
            for line in iter(arc_process.stdout.readline, b''):
                log.info(line.decode("utf-8").strip())
        except CalledProcessError as e:
            log.error(f"{str(e)}")

    # Delete the source file if enabled
    if delete_source:
        try:
            log.info("Deleting file: {}".format(source_file))
            os.remove(f"{source_file}")
        except Exception as e:
            log.error("Error deleting file: {}".format(e))
    else:
        log.info("Keeping source file: {}".format(source_file))

def trigger_spawn(event):
    log.info(f"Event: {event}")
    log.info(f"Proccessing {event.src_path}")
    file_processor(f"{event.src_path}", append_arc(event.src_path))

if __name__ == "__main__":
    log.info("Starting ArcWelder Hander...")
    file_watch = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    ## Triggers
    file_watch.on_created = trigger_spawn
    #file_watch.on_closed = trigger_spawn
    #file_watch.on_moved = trigger_spawn
    file_observer.schedule(file_watch, path, recursive=go_recursively)
    file_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        file_observer.stop()
        file_observer.join()