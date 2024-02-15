#!/bin/sh

# Light Preset=$1

# PRINT_READY = 1
# IDLE = 2
# PAUSED = 3
# PRINTING = 4
# HEATING = 5
# PRINT_COLD = 6
# PRINT_HOT = 7
# PRINT_CANCEL = 8
# BUSY = 9

/usr/bin/curl "http://192.168.20.44/win&PL=$1"