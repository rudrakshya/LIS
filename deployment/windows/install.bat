@echo off
REM Laboratory Information System (LIS) - Windows Installation
REM Simple wrapper for PowerShell deployment script

echo =========================================
echo  Laboratory Information System (LIS)
echo  Windows Installation
echo =========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Starting LIS deployment...
echo.

REM Check PowerShell execution policy
powershell -Command "if ((Get-ExecutionPolicy) -eq 'Restricted') { Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force }"

REM Run PowerShell deployment script
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*

if %errorLevel% EQU 0 (
    echo.
    echo =========================================
    echo  LIS Installation Completed Successfully!
    echo =========================================
    echo.
    echo Your LIS system is now running as a Windows service.
    echo.
    echo Management files are located in C:\LIS\
    echo.
    echo Quick Commands:
    echo   Start Service: net start "LIS-Service"
    echo   Stop Service:  net stop "LIS-Service"
    echo   View Status:   sc query "LIS-Service"
    echo.
    echo Health Check: http://localhost:8080/health
    echo.
) else (
    echo.
    echo =========================================
    echo  Installation Failed!
    echo =========================================
    echo.
    echo Please check the error messages above and try again.
    echo.
)

pause 