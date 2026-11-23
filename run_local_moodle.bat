@echo off
cd /d %~dp0
set PLATFORM=moodle
set HEADLESS=false
set BROWSER_PERSISTENT_PROFILE=true
set LLM_MODEL=qwen2.5:0.5b
python main.py
