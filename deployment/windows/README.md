# Windows Deployment Files

This directory contains Windows-specific deployment files for the Laboratory Information System (LIS).

## 🚀 Quick Start

### For Windows 7/10 (No Docker)

1. **Right-click** `install.bat` 
2. **Select** "Run as administrator"
3. **Wait** for installation to complete
4. **Done!** LIS is now running as a Windows service

## 📁 Files in this Directory

| File | Description |
|------|-------------|
| `install.bat` | **One-click installer** (Run as Administrator) |
| `deploy.ps1` | PowerShell deployment script (main installer) |
| `uninstall.bat` | Complete removal script |
| `README.md` | This file |

## 🎯 What the Installer Does

1. ✅ **Checks** for Administrator privileges
2. ✅ **Installs** Python 3.11 (if needed)
3. ✅ **Downloads** NSSM service manager
4. ✅ **Creates** installation directory (`C:\LIS\`)
5. ✅ **Copies** application files
6. ✅ **Sets up** Python virtual environment
7. ✅ **Installs** all Python dependencies
8. ✅ **Configures** Windows service
9. ✅ **Sets up** Windows Firewall rules
10. ✅ **Starts** the LIS service
11. ✅ **Creates** management scripts

## 📋 System Requirements

- **Windows 7 SP1+** or **Windows 10**
- **2GB RAM** minimum
- **1GB free space**
- **Administrator access**
- **Internet connection** (for initial setup)

## 🎛️ After Installation

### Service Management
```cmd
# Start service
net start "LIS-Service"

# Stop service
net stop "LIS-Service"

# Check status
sc query "LIS-Service"
```

### Management Scripts (in C:\LIS\)
- `start-service.bat` - Start the service
- `stop-service.bat` - Stop the service
- `service-status.bat` - Check status and health
- `view-logs.bat` - View recent logs

### Access Points
- **TCP Server**: localhost:8000 (for equipment)
- **REST API**: http://localhost:8080 (for web access)
- **Health Check**: http://localhost:8080/health

## 🏥 How It Works

The LIS system runs as a **Windows service** that:

1. **Automatically starts** when Windows boots
2. **Listens** for medical equipment on port 8000
3. **Processes** HL7/ASTM messages automatically
4. **Stores** results in SQLite database
5. **Requires no user interaction**

## 🔧 Configuration

Edit `C:\LIS\.env` to customize:
- Database settings
- Port numbers
- Logging levels
- Auto-processing options

## 📊 Monitoring

### Health Check
```cmd
curl http://localhost:8080/health
```

### View Logs
```cmd
type C:\LIS\logs\lis.log
```

### Windows Services
1. Press `Win + R`
2. Type `services.msc`
3. Find "Laboratory Information System"

## 🚨 Troubleshooting

### Common Issues

**"Not recognized as Administrator"**
- Right-click the .bat file and select "Run as administrator"

**"Python not found"**
- The installer will download and install Python automatically

**"Port already in use"**
```cmd
netstat -an | findstr :8000
netstat -an | findstr :8080
```

**Service won't start**
```cmd
# Check service status
sc query "LIS-Service"

# View configuration
sc qc "LIS-Service"

# Test manual start
cd C:\LIS
venv\Scripts\python.exe lis_service.py
```

## 🗑️ Uninstallation

To completely remove the LIS system:

1. **Right-click** `uninstall.bat`
2. **Select** "Run as administrator"
3. **Confirm** removal when prompted

This will:
- Stop and remove the Windows service
- Remove all files from `C:\LIS\`
- Remove Windows Firewall rules

## 📞 Support

### Log Files
- Application: `C:\LIS\logs\lis.log`
- Service: `C:\LIS\logs\service.log`
- Errors: `C:\LIS\logs\service-error.log`

### Health Endpoints
- Basic: http://localhost:8080/health
- Status: http://localhost:8080/system/status
- Metrics: http://localhost:8080/system/metrics

### Windows Event Viewer
1. Open Event Viewer (`eventvwr.msc`)
2. Go to **Windows Logs → Application**
3. Filter by source: **LIS-Service**

## 🎯 Production Notes

- **Antivirus**: Exclude `C:\LIS\` from real-time scanning
- **Windows Updates**: Keep system updated
- **Firewall**: Only required ports (8000, 8080) are opened
- **Backup**: Database is at `C:\LIS\data\lis.db`

## ✅ Installation Complete!

After running the installer, your LIS system will be:
- ✅ Running as a Windows service
- ✅ Processing laboratory data automatically
- ✅ Accessible via REST API
- ✅ Ready for medical equipment connections

**No further configuration required for basic operation!** 