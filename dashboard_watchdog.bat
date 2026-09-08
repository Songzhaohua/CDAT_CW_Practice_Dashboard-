@echo off
REM Keeps the CW Practice Dashboard running: relaunches it if it ever exits/crashes.
REM Launched hidden via start_dashboard_silent.vbs from a Scheduled Task.
cd /d "%~dp0"

:loop
netstat -an | findstr /c:":8501 " | findstr /c:"LISTENING" >nul
if %errorlevel% equ 0 (
    echo [%date% %time%] Port 8501 already in use by another process, not starting a duplicate. >> dashboard_watchdog.log
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%date% %time%] Starting dashboard... >> dashboard_watchdog.log
REM --server.port is explicit so Streamlit fails fast instead of drifting to another port.
python -m streamlit run CDAT_CW_Practice_Dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.baseUrlPath CDAT_CW_Practice_Dashboard >> dashboard_watchdog.log 2>&1
echo [%date% %time%] Dashboard exited, restarting in 10s... >> dashboard_watchdog.log
timeout /t 10 /nobreak >nul
goto loop
