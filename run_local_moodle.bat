@echo off
cd /d %~dp0
set PLATFORM=moodle
set HEADLESS=false
set BROWSER_PERSISTENT_PROFILE=true
python main.py
