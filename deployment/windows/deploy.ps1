# Laboratory Information System (LIS) - Windows Deployment Script
# Deploys LIS system on Windows 7/10 without Docker

param(
    [string]$InstallPath = "C:\LIS",
    [string]$ServiceName = "LIS-Service",
    [string]$PythonPath = "",
    [switch]$SkipPython = $false,
    [switch]$Force = $false
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Write-Error-Log {
    param([string]$Message)
    Write-Log "ERROR: $Message" $Red
}

function Write-Success {
    param([string]$Message)
    Write-Log "SUCCESS: $Message" $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Log "WARNING: $Message" $Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Log "INFO: $Message" $Blue
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Install Python if needed
function Install-Python {
    if ($SkipPython) {
        Write-Info "Skipping Python installation as requested"
        return
    }

    Write-Info "Checking for Python installation..."
    
    if ($PythonPath -and (Test-Path $PythonPath)) {
        Write-Info "Using provided Python path: $PythonPath"
        return $PythonPath
    }

    # Check for existing Python installation
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3\.([89]|1[0-9])") {
            $pythonExe = (Get-Command python).Source
            Write-Success "Found compatible Python: $pythonVersion at $pythonExe"
            return $pythonExe
        }
    }
    catch {
        Write-Warning "Python not found in PATH"
    }

    Write-Info "Downloading and installing Python 3.11..."
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    
    try {
        Write-Info "Downloading Python installer..."
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
        
        Write-Info "Installing Python..."
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
        
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        Remove-Item $pythonInstaller -ErrorAction SilentlyContinue
        
        # Verify installation
        $pythonExe = (Get-Command python).Source
        Write-Success "Python installed successfully at $pythonExe"
        return $pythonExe
    }
    catch {
        Write-Error-Log "Failed to install Python: $_"
        throw
    }
}

# Download and install NSSM for service management
function Install-NSSM {
    Write-Info "Installing NSSM (Non-Sucking Service Manager)..."
    
    $nssmPath = "$InstallPath\tools\nssm.exe"
    if (Test-Path $nssmPath) {
        Write-Info "NSSM already installed"
        return $nssmPath
    }

    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmExtract = "$env:TEMP\nssm"
    
    try {
        Write-Info "Downloading NSSM..."
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip -UseBasicParsing
        
        Write-Info "Extracting NSSM..."
        Expand-Archive -Path $nssmZip -DestinationPath $nssmExtract -Force
        
        # Create tools directory
        $toolsDir = "$InstallPath\tools"
        if (!(Test-Path $toolsDir)) {
            New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
        }
        
        # Copy appropriate NSSM executable
        $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        Copy-Item "$nssmExtract\nssm-2.24\$arch\nssm.exe" $nssmPath -Force
        
        # Cleanup
        Remove-Item $nssmZip -ErrorAction SilentlyContinue
        Remove-Item $nssmExtract -Recurse -ErrorAction SilentlyContinue
        
        Write-Success "NSSM installed successfully"
        return $nssmPath
    }
    catch {
        Write-Error-Log "Failed to install NSSM: $_"
        throw
    }
}

# Create installation directories
function Create-Directories {
    Write-Info "Creating installation directories..."
    
    $directories = @(
        $InstallPath,
        "$InstallPath\src",
        "$InstallPath\logs",
        "$InstallPath\data",
        "$InstallPath\config",
        "$InstallPath\tools"
    )
    
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Info "Created directory: $dir"
        }
    }
    
    Write-Success "Directories created successfully"
}

# Copy application files
function Copy-Application {
    Write-Info "Copying application files..."
    
    try {
        # Copy source code
        $sourceDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
        
        # Copy main files
        Copy-Item "$sourceDir\lis_service.py" "$InstallPath\" -Force
        Copy-Item "$sourceDir\requirements.txt" "$InstallPath\" -Force
        Copy-Item "$sourceDir\README.md" "$InstallPath\" -Force -ErrorAction SilentlyContinue
        
        # Copy source directory
        if (Test-Path "$sourceDir\src") {
            Copy-Item "$sourceDir\src" "$InstallPath\" -Recurse -Force
        }
        
        Write-Success "Application files copied successfully"
    }
    catch {
        Write-Error-Log "Failed to copy application files: $_"
        throw
    }
}

# Setup Python virtual environment
function Setup-VirtualEnvironment {
    param([string]$PythonExe)
    
    Write-Info "Setting up Python virtual environment..."
    
    $venvPath = "$InstallPath\venv"
    
    try {
        if (Test-Path $venvPath) {
            if ($Force) {
                Write-Info "Removing existing virtual environment..."
                Remove-Item $venvPath -Recurse -Force
            } else {
                Write-Info "Virtual environment already exists"
                return "$venvPath\Scripts\python.exe"
            }
        }
        
        # Create virtual environment
        Write-Info "Creating virtual environment..."
        & $PythonExe -m venv $venvPath
        
        # Upgrade pip
        Write-Info "Upgrading pip..."
        & "$venvPath\Scripts\python.exe" -m pip install --upgrade pip
        
        # Install requirements
        Write-Info "Installing Python packages..."
        & "$venvPath\Scripts\pip.exe" install -r "$InstallPath\requirements.txt"
        
        Write-Success "Virtual environment setup complete"
        return "$venvPath\Scripts\python.exe"
    }
    catch {
        Write-Error-Log "Failed to setup virtual environment: $_"
        throw
    }
}

# Create Windows environment configuration
function Create-WindowsConfig {
    Write-Info "Creating Windows configuration..."
    
    $configContent = @"
# Laboratory Information System (LIS) - Windows Configuration
# Environment Configuration for Windows deployment

# Application Environment
ENVIRONMENT=production
APP_NAME=Laboratory Information System
APP_VERSION=1.0.0
DEBUG=False

# Security Settings
SECURITY_SECRET_KEY=your-windows-secret-key-change-this
SECURITY_ALGORITHM=HS256
SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Configuration (SQLite for Windows)
DATABASE_URL=sqlite:///$($InstallPath.Replace('\', '/').Replace(':', ''))/data/lis.db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# TCP Communication Settings
COMM_TCP_HOST=0.0.0.0
COMM_TCP_PORT=8000
COMM_TCP_BUFFER_SIZE=4096
COMM_SERIAL_TIMEOUT=30

# API Configuration
API_HOST=127.0.0.1
API_PORT=8080
API_DEBUG=False
API_RELOAD=False

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=$($InstallPath.Replace('\', '\\'))\\logs\\lis.log
LOG_MAX_SIZE=50485760
LOG_BACKUP_COUNT=10

# Device Configuration
DEVICE_AUTO_DISCOVER_DEVICES=True
DEVICE_SCAN_INTERVAL=300
DEVICE_TIMEOUT=60
DEVICE_RESPONSE_TIMEOUT=30

# Auto-processing Settings
AUTO_PROCESS_MESSAGES=True
AUTO_STORE_RESULTS=True
AUTO_GENERATE_REPORTS=True
AUTO_ARCHIVE_DATA=True

# Queue and Processing Settings
MESSAGE_QUEUE_SIZE=10000
PROCESSING_BATCH_SIZE=100
PROCESSING_TIMEOUT=60
MAX_PROCESSING_ERRORS=10

# Performance Settings
PERFORMANCE_MAX_CONNECTIONS=100
PERFORMANCE_CONNECTION_TIMEOUT=60
PERFORMANCE_REQUEST_TIMEOUT=120
PERFORMANCE_THREAD_POOL_SIZE=10
"@

    $configFile = "$InstallPath\.env"
    Set-Content -Path $configFile -Value $configContent -Encoding UTF8
    Write-Success "Configuration file created: $configFile"
}

# Install Windows service using NSSM
function Install-WindowsService {
    param([string]$PythonExe, [string]$NssmPath)
    
    Write-Info "Installing Windows service..."
    
    try {
        # Check if service already exists
        $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($existingService) {
            if ($Force) {
                Write-Info "Removing existing service..."
                & $NssmPath stop $ServiceName
                & $NssmPath remove $ServiceName confirm
                Start-Sleep -Seconds 2
            } else {
                Write-Warning "Service '$ServiceName' already exists. Use -Force to reinstall."
                return
            }
        }
        
        # Install service
        Write-Info "Creating Windows service '$ServiceName'..."
        & $NssmPath install $ServiceName $PythonExe "$InstallPath\lis_service.py"
        
        # Configure service
        & $NssmPath set $ServiceName AppDirectory $InstallPath
        & $NssmPath set $ServiceName DisplayName "Laboratory Information System"
        & $NssmPath set $ServiceName Description "LIS for medical equipment integration"
        & $NssmPath set $ServiceName Start SERVICE_AUTO_START
        
        # Set service to restart on failure
        & $NssmPath set $ServiceName AppExit Default Restart
        & $NssmPath set $ServiceName AppRestartDelay 5000
        
        # Set output redirection
        & $NssmPath set $ServiceName AppStdout "$InstallPath\logs\service.log"
        & $NssmPath set $ServiceName AppStderr "$InstallPath\logs\service-error.log"
        
        Write-Success "Windows service installed successfully"
    }
    catch {
        Write-Error-Log "Failed to install Windows service: $_"
        throw
    }
}

# Start the service
function Start-LISService {
    Write-Info "Starting LIS service..."
    
    try {
        Start-Service -Name $ServiceName
        Start-Sleep -Seconds 5
        
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq "Running") {
            Write-Success "LIS service started successfully"
        } else {
            Write-Error-Log "Service failed to start. Status: $($service.Status)"
        }
    }
    catch {
        Write-Error-Log "Failed to start service: $_"
        throw
    }
}

# Perform health check
function Test-HealthCheck {
    Write-Info "Performing health check..."
    
    Start-Sleep -Seconds 10  # Give service time to start
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 30
        if ($response.status -eq "healthy") {
            Write-Success "Health check passed: $($response.status)"
        } else {
            Write-Warning "Health check returned: $($response.status)"
        }
    }
    catch {
        Write-Warning "Health check failed (service may still be starting): $_"
    }
}

# Create management scripts
function Create-ManagementScripts {
    Write-Info "Creating management scripts..."
    
    # Start service script
    $startScript = @"
@echo off
echo Starting LIS service...
net start "$ServiceName"
echo.
echo Service status:
sc query "$ServiceName"
pause
"@
    
    Set-Content -Path "$InstallPath\start-service.bat" -Value $startScript
    
    # Stop service script
    $stopScript = @"
@echo off
echo Stopping LIS service...
net stop "$ServiceName"
echo.
echo Service status:
sc query "$ServiceName"
pause
"@
    
    Set-Content -Path "$InstallPath\stop-service.bat" -Value $stopScript
    
    # Status script
    $statusScript = @"
@echo off
echo LIS Service Status:
echo ==================
sc query "$ServiceName"
echo.
echo Health Check:
echo =============
curl -s http://localhost:8080/health 2>nul || echo Health check failed
echo.
pause
"@
    
    Set-Content -Path "$InstallPath\service-status.bat" -Value $statusScript
    
    # Logs script
    $logsScript = @"
@echo off
echo Opening LIS logs...
echo Recent log entries:
echo ==================
type "$InstallPath\logs\lis.log" | findstr /C:"ERROR" /C:"WARNING" /C:"INFO" | more
echo.
echo Full log location: $InstallPath\logs\lis.log
pause
"@
    
    Set-Content -Path "$InstallPath\view-logs.bat" -Value $logsScript
    
    Write-Success "Management scripts created in $InstallPath"
}

# Configure Windows Firewall
function Configure-Firewall {
    Write-Info "Configuring Windows Firewall..."
    
    try {
        # Allow TCP port 8000 (equipment communication)
        netsh advfirewall firewall add rule name="LIS TCP Server" dir=in action=allow protocol=TCP localport=8000
        
        # Allow TCP port 8080 (REST API)
        netsh advfirewall firewall add rule name="LIS REST API" dir=in action=allow protocol=TCP localport=8080
        
        Write-Success "Firewall rules configured"
    }
    catch {
        Write-Warning "Failed to configure firewall. You may need to configure manually."
    }
}

# Main deployment function
function Deploy-LIS {
    Write-Info "Starting LIS Windows deployment..."
    Write-Info "Target installation path: $InstallPath"
    Write-Info "Service name: $ServiceName"
    
    try {
        # Check administrator privileges
        if (!(Test-Administrator)) {
            Write-Error-Log "This script must be run as Administrator"
            throw "Administrator privileges required"
        }
        
        # Create directories
        Create-Directories
        
        # Install Python
        $pythonExe = Install-Python
        
        # Install NSSM
        $nssmPath = Install-NSSM
        
        # Copy application files
        Copy-Application
        
        # Setup virtual environment
        $venvPython = Setup-VirtualEnvironment -PythonExe $pythonExe
        
        # Create configuration
        Create-WindowsConfig
        
        # Install Windows service
        Install-WindowsService -PythonExe $venvPython -NssmPath $nssmPath
        
        # Configure firewall
        Configure-Firewall
        
        # Create management scripts
        Create-ManagementScripts
        
        # Start service
        Start-LISService
        
        # Health check
        Test-HealthCheck
        
        Write-Success "LIS deployment completed successfully!"
        
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host "   LIS Windows Deployment Complete" -ForegroundColor Green
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Installation Path: $InstallPath" -ForegroundColor Cyan
        Write-Host "Service Name: $ServiceName" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Services:" -ForegroundColor Yellow
        Write-Host "  - TCP Server: localhost:8000" -ForegroundColor White
        Write-Host "  - REST API: http://localhost:8080" -ForegroundColor White
        Write-Host ""
        Write-Host "Management Commands:" -ForegroundColor Yellow
        Write-Host "  - Start service: net start `"$ServiceName`"" -ForegroundColor White
        Write-Host "  - Stop service: net stop `"$ServiceName`"" -ForegroundColor White
        Write-Host "  - Service status: sc query `"$ServiceName`"" -ForegroundColor White
        Write-Host ""
        Write-Host "Management Scripts (in $InstallPath):" -ForegroundColor Yellow
        Write-Host "  - start-service.bat" -ForegroundColor White
        Write-Host "  - stop-service.bat" -ForegroundColor White
        Write-Host "  - service-status.bat" -ForegroundColor White
        Write-Host "  - view-logs.bat" -ForegroundColor White
        Write-Host ""
        Write-Host "Configuration:" -ForegroundColor Yellow
        Write-Host "  - Environment: $InstallPath\.env" -ForegroundColor White
        Write-Host "  - Logs: $InstallPath\logs\" -ForegroundColor White
        Write-Host "  - Data: $InstallPath\data\" -ForegroundColor White
        Write-Host ""
        
    }
    catch {
        Write-Error-Log "Deployment failed: $_"
        Write-Host "Check the error messages above and try again." -ForegroundColor Red
        exit 1
    }
}

# Run deployment
Deploy-LIS 