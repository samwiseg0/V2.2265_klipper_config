#!/bin/sh

# Light Preset=$1
# TORCH = 1
# IDLE = 2
# PAUSED = 3
# PRINTING = 4
# HEATING = 5
# PRINT_COMP = 6
# UNKN = 7

/usr/bin/curl "http://192.168.20.44/win&PL=$1"
/usr/bin/curl "http://192.168.20.251/win&PL=$1"
