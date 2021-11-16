#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path


path = '/home/pi/gcode_files'
go_recursively = True
patterns = ['*.gcode']
ignore_patterns = ['*.arc.gcode']
ignore_directories = True
case_sensitive = False
arc_welder_location = '/home/pi/bin/ArcWelder'
log_location = '/tmp/arc_welder.log'

# Set up the log file
logging.basicConfig(
    filename=log_location,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('ArcWelder')

file_observer = Observer()

def append_arc(filename):
    path = Path(filename)
    return path.with_name(f"{path.stem}.arc{path.suffix}")

def arc_welder(source_file, des_file):
    time.sleep(1)
    command = f"\042{arc_welder_location}\042 \042{source_file}\042 \042{des_file}\042"
    log.info("Spawning command:{}".format(command))
    arc_process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
    with arc_process.stdout:
        try:
            for line in iter(arc_process.stdout.readline, b''):
                log.info(line.decode("utf-8").strip())
        except CalledProcessError as e:
            log.error(f"{str(e)}")
    try:
        log.info("Deleting file: {}".format(source_file))
        os.remove(f"{source_file}")
    except Exception as e:
        log.eror("Error deleting file: {}".format(e))

def arc_trigger(event):
    log.info(f"Event: {event}")
    log.info(f"Proccessing {event.src_path}")
    arc_welder(f"{event.src_path}", append_arc(event.src_path))

if __name__ == "__main__":
    log.info("Starting ArcWelder Hander...")
    file_watch = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    ## TRIGGERS
    file_watch.on_created = arc_trigger
    #file_watch.on_closed = arc_trigger
    #file_watch.on_moved = arc_trigger
    file_observer.schedule(file_watch, path, recursive=go_recursively)
    file_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        file_observer.stop()
        file_observer.join()
