@echo off
REM Regenerates the CW Practice HTML report on the shared network drive.
cd /d "%~dp0"
python generate_report.py
