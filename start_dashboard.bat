@echo off
REM Starts the CW Practice Dashboard so other machines on the network can reach it.
REM NOTE: the dashboard auto-starts via the "CW Practice Dashboard" Scheduled Task + watchdog.
REM Only run this manually if that task/watchdog is not already running, to avoid a second
REM instance drifting onto a different port.
cd /d "%~dp0"
netstat -an | findstr /c:":8501 " | findstr /c:"LISTENING" >nul
if %errorlevel% equ 0 (
    echo Port 8501 is already in use - the dashboard is likely already running. Aborting.
    exit /b 1
)
python -m streamlit run CDAT_CW_Practice_Dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.baseUrlPath CDAT_CW_Practice_Dashboard
