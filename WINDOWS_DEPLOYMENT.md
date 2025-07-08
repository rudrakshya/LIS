# Laboratory Information System (LIS) - Windows Deployment Guide

## Overview

This guide explains how to deploy and run the Laboratory Information System (LIS) on Windows 7 and Windows 10 **without Docker**. The system runs as a native Windows service and automatically processes laboratory data without user interaction.

## 🖥️ **Windows Compatibility**

### Supported Windows Versions
- ✅ **Windows 10** (All editions)
- ✅ **Windows 7** (Service Pack 1 required)
- ✅ **Windows Server 2012/2016/2019/2022**

### System Requirements
- **OS**: Windows 7 SP1+ or Windows 10
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB free space minimum
- **Network**: Internet connection for initial setup
- **Privileges**: Administrator access required for installation

## 🚀 **Quick Installation (Recommended)**

### Option 1: One-Click Installation
1. **Download** the LIS system files to your computer
2. **Right-click** on `deployment\windows\install.bat`
3. **Select** "Run as administrator"
4. **Follow** the on-screen prompts

That's it! The system will automatically:
- Install Python if needed
- Set up the virtual environment
- Install all dependencies
- Create the Windows service
- Configure firewall rules
- Start the LIS service

### Option 2: PowerShell Installation
```powershell
# Open PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd deployment\windows
.\deploy.ps1
```

## 🔧 **Manual Installation**

### Step 1: Install Python (if needed)
Download and install Python 3.11 from [python.org](https://www.python.org/downloads/):
- ✅ Check "Add Python to PATH"
- ✅ Choose "Install for all users"

### Step 2: Run Deployment Script
```cmd
# Open Command Prompt as Administrator
cd deployment\windows
install.bat
```

### Step 3: Verify Installation
```cmd
# Check service status
sc query "LIS-Service"

# Test health endpoint
curl http://localhost:8080/health
```

## 📁 **Installation Structure**

After installation, you'll find:

```
C:\LIS\                           # Main installation directory
├── lis_service.py               # Main service application
├── requirements.txt             # Python dependencies
├── .env                         # Configuration file
├── src\                         # Source code
├── venv\                        # Python virtual environment
├── logs\                        # Log files
│   ├── lis.log                 # Application logs
│   ├── service.log             # Service output
│   └── service-error.log       # Service errors
├── data\                        # Database and data files
│   └── lis.db                  # SQLite database
├── tools\                       # Utilities
│   └── nssm.exe                # Service manager
├── start-service.bat           # Start service
├── stop-service.bat            # Stop service
├── service-status.bat          # Check status
└── view-logs.bat               # View logs
```

## 🎛️ **Service Management**

### Windows Service Commands
```cmd
# Start LIS service
net start "LIS-Service"

# Stop LIS service
net stop "LIS-Service"

# Check service status
sc query "LIS-Service"

# View service configuration
sc qc "LIS-Service"
```

### Management Scripts
Double-click these files in `C:\LIS\`:
- **`start-service.bat`** - Start the LIS service
- **`stop-service.bat`** - Stop the LIS service  
- **`service-status.bat`** - Check service status and health
- **`view-logs.bat`** - View recent log entries

### Services Management Console
1. Press `Win + R`, type `services.msc`
2. Find "**Laboratory Information System**"
3. Right-click for options (Start, Stop, Restart, Properties)

## 🔧 **Configuration**

### Environment Configuration
Edit `C:\LIS\.env` to customize settings:

```bash
# Basic Settings
ENVIRONMENT=production
COMM_TCP_PORT=8000          # Equipment connection port
API_PORT=8080               # REST API port

# Database (SQLite by default)
DATABASE_URL=sqlite:///C:/LIS/data/lis.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=C:\\LIS\\logs\\lis.log

# Auto-processing (No user interaction)
AUTO_PROCESS_MESSAGES=True
AUTO_STORE_RESULTS=True
```

### Windows Firewall
The installer automatically configures firewall rules:
- **Port 8000**: TCP server for medical equipment
- **Port 8080**: REST API for external systems

To manually configure:
```cmd
# Allow equipment connections
netsh advfirewall firewall add rule name="LIS TCP Server" dir=in action=allow protocol=TCP localport=8000

# Allow API access
netsh advfirewall firewall add rule name="LIS REST API" dir=in action=allow protocol=TCP localport=8080
```

## 🏥 **How It Works on Windows**

### Automatic Operation
1. **Service Startup**: Windows starts LIS service automatically on boot
2. **Equipment Connection**: Medical equipment connects to port 8000
3. **Message Processing**: HL7/ASTM messages processed automatically
4. **Data Storage**: Results stored in SQLite database
5. **No User Interaction**: Everything happens automatically

### Data Flow
```
Medical Equipment → Windows Service → SQLite Database
                                   ↓
              Web Interface ← REST API
```

### Background Processing
- **Windows Service**: Runs in background 24/7
- **Auto-restart**: Service automatically restarts if it crashes
- **Event Logging**: Windows Event Log integration
- **Resource Management**: Memory and CPU limits configured

## 📊 **Monitoring**

### Health Checks
```cmd
# Basic health check
curl http://localhost:8080/health

# Detailed system status
curl http://localhost:8080/system/status

# Performance metrics
curl http://localhost:8080/system/metrics
```

### Windows Event Viewer
1. Open **Event Viewer** (`eventvwr.msc`)
2. Navigate to **Windows Logs → Application**
3. Filter by source: **nssm** or **LIS-Service**

### Log Files
- **Application logs**: `C:\LIS\logs\lis.log`
- **Service output**: `C:\LIS\logs\service.log`
- **Service errors**: `C:\LIS\logs\service-error.log`

### Task Manager
Monitor the LIS service process:
1. Open **Task Manager** (`Ctrl+Shift+Esc`)
2. Go to **Services** tab
3. Find **LIS-Service**

## 🚨 **Troubleshooting**

### Service Won't Start
```cmd
# Check service status
sc query "LIS-Service"

# View service configuration
sc qc "LIS-Service"

# Check Python installation
C:\LIS\venv\Scripts\python.exe --version

# Test manual start
cd C:\LIS
venv\Scripts\python.exe lis_service.py
```

### Port Already in Use
```cmd
# Check what's using port 8000
netstat -an | findstr :8000

# Check what's using port 8080
netstat -an | findstr :8080
```

### Python Issues
```cmd
# Reinstall virtual environment
cd C:\LIS
rmdir /s venv
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### Database Issues
```cmd
# Check database file
dir C:\LIS\data\lis.db

# Test database connection
cd C:\LIS
venv\Scripts\python.exe -c "from src.core.database import db_manager; print(db_manager.test_connection())"
```

### Windows 7 Specific Issues

**PowerShell Version**: Windows 7 has PowerShell 2.0 by default
```cmd
# Upgrade to PowerShell 4.0+ for full compatibility
# Download Windows Management Framework 4.0 from Microsoft
```

**TLS Issues**: Windows 7 may have TLS connectivity issues
```cmd
# Enable TLS 1.2
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\.NETFramework\v4.0.30319" /v SchUseStrongCrypto /t REG_DWORD /d 1
```

## 🔄 **Updates**

### Updating the LIS System
1. **Stop the service**:
   ```cmd
   net stop "LIS-Service"
   ```

2. **Backup configuration**:
   ```cmd
   copy C:\LIS\.env C:\LIS\.env.backup
   ```

3. **Update files**:
   - Copy new `lis_service.py` and `src\` folder
   - Update `requirements.txt` if needed

4. **Update dependencies**:
   ```cmd
   cd C:\LIS
   venv\Scripts\pip install -r requirements.txt --upgrade
   ```

5. **Start the service**:
   ```cmd
   net start "LIS-Service"
   ```

## 🗑️ **Uninstallation**

### Complete Removal
1. **Run uninstaller** as Administrator:
   ```cmd
   deployment\windows\uninstall.bat
   ```

### Manual Removal
```cmd
# Stop and remove service
net stop "LIS-Service"
sc delete "LIS-Service"

# Remove firewall rules
netsh advfirewall firewall delete rule name="LIS TCP Server"
netsh advfirewall firewall delete rule name="LIS REST API"

# Remove installation directory
rmdir /s /q C:\LIS
```

## 📞 **Support**

### System Information
```cmd
# Windows version
ver

# System info
systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"System Type"

# LIS service info
sc query "LIS-Service"
sc qc "LIS-Service"
```

### Common Endpoints
- **Health Check**: http://localhost:8080/health
- **System Status**: http://localhost:8080/system/status
- **API Documentation**: http://localhost:8080/docs

### Log Locations
- **Application**: `C:\LIS\logs\lis.log`
- **Service**: `C:\LIS\logs\service.log`
- **Windows Events**: Event Viewer → Application Log

## 🎯 **Production Tips**

### Performance
- **Dedicated Server**: Use a dedicated Windows machine for production
- **Antivirus**: Exclude `C:\LIS\` from real-time scanning
- **Windows Updates**: Keep Windows updated for security

### Security
- **Firewall**: Only open required ports (8000, 8080)
- **User Account**: Run service with limited user account
- **Network**: Use VPN for remote equipment connections

### Backup
```cmd
# Backup database
copy C:\LIS\data\lis.db C:\Backup\lis.db.%date%

# Backup configuration
copy C:\LIS\.env C:\Backup\.env.%date%
```

## ✅ **Quick Start Checklist**

1. ✅ Download LIS files
2. ✅ Right-click `deployment\windows\install.bat`
3. ✅ Select "Run as administrator"  
4. ✅ Wait for installation to complete
5. ✅ Test: http://localhost:8080/health
6. ✅ Connect medical equipment to port 8000
7. ✅ Monitor logs in `C:\LIS\logs\lis.log`

Your LIS system is now running as a Windows service and will automatically process laboratory data from connected equipment!

## 📋 **Differences from Linux Version**

| Feature | Windows | Linux |
|---------|---------|-------|
| **Service Manager** | NSSM + Windows Services | systemd |
| **Database** | SQLite (default) | PostgreSQL |
| **Installation** | `C:\LIS\` | `/opt/lis/` |
| **Service Control** | `net start/stop` | `systemctl` |
| **Logs** | `C:\LIS\logs\` | `/var/log/lis/` |
| **Configuration** | `C:\LIS\.env` | `/opt/lis/.env` |

The core functionality and automatic processing capabilities are identical across both platforms. 