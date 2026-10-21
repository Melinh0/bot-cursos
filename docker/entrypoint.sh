#!/bin/bash

set -e

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

sleep 2

echo "Starting bot..."
exec python main.py