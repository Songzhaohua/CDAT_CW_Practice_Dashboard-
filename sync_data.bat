@echo off
REM Copies the live CSV into this repo's data/ folder and pushes it to git so
REM Streamlit Community Cloud picks up the fresh snapshot. Schedule this
REM periodically (e.g., Task Scheduler) on a machine with network + git access.
cd /d "%~dp0"
python sync_data.py
