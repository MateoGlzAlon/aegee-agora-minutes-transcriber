#!/bin/bash
set -e
if [ "$1" = "daemon" ]; then
    exec python daemon.py
else
    exec python main.py "$@"
fi
