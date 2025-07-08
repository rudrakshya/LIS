@echo off
REM Laboratory Information System (LIS) - Windows Uninstaller

echo =========================================
echo  LIS Uninstaller
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

set SERVICE_NAME=LIS-Service
set INSTALL_PATH=C:\LIS

echo WARNING: This will completely remove the LIS system!
echo.
echo This will:
echo - Stop and remove the LIS Windows service
echo - Remove installation directory: %INSTALL_PATH%
echo - Remove Windows Firewall rules
echo.
set /p CONFIRM="Are you sure you want to continue? (yes/no): "

if /i not "%CONFIRM%"=="yes" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo Stopping LIS service...
net stop "%SERVICE_NAME%" 2>nul

echo Removing Windows service...
if exist "%INSTALL_PATH%\tools\nssm.exe" (
    "%INSTALL_PATH%\tools\nssm.exe" remove "%SERVICE_NAME%" confirm
) else (
    sc delete "%SERVICE_NAME%"
)

echo Removing Windows Firewall rules...
netsh advfirewall firewall delete rule name="LIS TCP Server" 2>nul
netsh advfirewall firewall delete rule name="LIS REST API" 2>nul

echo Removing installation directory...
if exist "%INSTALL_PATH%" (
    rmdir /s /q "%INSTALL_PATH%"
    echo Installation directory removed: %INSTALL_PATH%
) else (
    echo Installation directory not found: %INSTALL_PATH%
)

echo.
echo =========================================
echo  LIS Uninstallation Complete
echo =========================================
echo.
echo The LIS system has been completely removed from your system.
echo.

pause 