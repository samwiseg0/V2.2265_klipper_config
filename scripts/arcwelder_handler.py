#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
from subprocess import Popen, PIPE, STDOUT
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path


path = '/home/pi/gcode_files'
go_recursively = False
patterns = ['*.gcode']
ignore_patterns = ['*.arc.gcode']
ignore_directories = False
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

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        log.info("{}".format(line))

def append_filename(filename):
    path = Path(filename)
    return path.with_name(f"{path.stem}.arc{path.suffix}")

def arc_welder(source_file, des_file):
    time.sleep(1)
    arc_process = Popen([f"{arc_welder_location}", f"{source_file}", f"{des_file}"], stdout=PIPE, stderr=STDOUT)
    with arc_process.stdout:
        log_subprocess_output(arc_process.stdout)
    exitcode = arc_process.wait()
    log.info(f"ArcWelder exit code: {exitcode}")
    #if exitcode == 0:
        #time.sleep(5)
        #log.info(f"Deleting source file: {source_file}")
        #os.remove(source_file)
    #else:
        #log.error(f"ArcWlder Failed! Exit code: {exitcode}")

def on_closed(event):
    log.info(f"Proccessing {event.src_path}")
    arc_welder(f"{event.src_path}", append_filename(event.src_path))

if __name__ == "__main__":
    log.info("Starting ArcWelder Hander...")
    file_watch = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    ## TRIGGERS
    file_watch.on_any_event = on_closed
    #file_watch.on_moved = arc_trigger
    file_observer.schedule(file_watch, path, recursive=go_recursively)
    file_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        file_observer.stop()
        file_observer.join()
