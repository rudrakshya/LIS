#!/bin/bash

# Laboratory Information System (LIS) - Production Deployment Script
# This script deploys the LIS system to a production environment

set -e  # Exit on any error

# Configuration
LIS_USER="lis"
LIS_GROUP="lis"
LIS_HOME="/opt/lis"
SERVICE_NAME="lis"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        nginx \
        supervisor \
        curl \
        git \
        build-essential \
        libpq-dev
    
    success "System dependencies installed"
}

# Create LIS user and group
create_user() {
    log "Creating LIS user and group..."
    
    if ! getent group $LIS_GROUP > /dev/null 2>&1; then
        groupadd $LIS_GROUP
        log "Created group: $LIS_GROUP"
    fi
    
    if ! getent passwd $LIS_USER > /dev/null 2>&1; then
        useradd -r -g $LIS_GROUP -d $LIS_HOME -s /bin/bash $LIS_USER
        log "Created user: $LIS_USER"
    fi
    
    success "User setup completed"
}

# Create directories
create_directories() {
    log "Creating application directories..."
    
    mkdir -p $LIS_HOME/{logs,data,backups,config}
    chown -R $LIS_USER:$LIS_GROUP $LIS_HOME
    chmod 755 $LIS_HOME
    
    success "Directories created"
}

# Setup Python environment
setup_python() {
    log "Setting up Python environment..."
    
    cd $LIS_HOME
    sudo -u $LIS_USER python3 -m venv venv
    sudo -u $LIS_USER $LIS_HOME/venv/bin/pip install --upgrade pip
    
    success "Python environment created"
}

# Deploy application
deploy_application() {
    log "Deploying LIS application..."
    
    # Copy application files (assuming they're in the current directory)
    cp -r ../src $LIS_HOME/
    cp ../lis_service.py $LIS_HOME/
    cp ../requirements.txt $LIS_HOME/
    cp ../env.example $LIS_HOME/.env
    
    # Set ownership
    chown -R $LIS_USER:$LIS_GROUP $LIS_HOME
    
    # Install Python dependencies
    sudo -u $LIS_USER $LIS_HOME/venv/bin/pip install -r $LIS_HOME/requirements.txt
    
    success "Application deployed"
}

# Setup database
setup_database() {
    log "Setting up PostgreSQL database..."
    
    sudo -u postgres createuser $LIS_USER 2>/dev/null || true
    sudo -u postgres createdb lis_db -O $LIS_USER 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER $LIS_USER WITH PASSWORD 'lis_password';" 2>/dev/null || true
    
    success "Database setup completed"
}

# Install systemd service
install_service() {
    log "Installing systemd service..."
    
    cp lis.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    success "Service installed"
}

# Configure nginx
configure_nginx() {
    log "Configuring nginx..."
    
    cat > /etc/nginx/sites-available/lis <<EOF
server {
    listen 80;
    server_name _;
    
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location / {
        root /var/www/html;
        index index.html index.htm;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/lis /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    nginx -t && systemctl reload nginx
    
    success "Nginx configured"
}

# Setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 22/tcp    # SSH
        ufw allow 80/tcp    # HTTP
        ufw allow 443/tcp   # HTTPS
        ufw allow 8000/tcp  # LIS TCP server
        ufw --force enable
        
        success "Firewall configured"
    else
        warning "UFW not found, skipping firewall configuration"
    fi
}

# Create production environment file
create_env_file() {
    log "Creating production environment file..."
    
    cat > $LIS_HOME/.env <<EOF
# Production Environment Configuration
ENVIRONMENT=production
DATABASE_URL=postgresql://lis_user:lis_password@localhost:5432/lis_db
SECURITY_SECRET_KEY=$(openssl rand -hex 32)
LOG_LEVEL=INFO
API_DEBUG=False
COMM_TCP_HOST=0.0.0.0
COMM_TCP_PORT=8000
API_HOST=127.0.0.1
API_PORT=8080
EOF
    
    chown $LIS_USER:$LIS_GROUP $LIS_HOME/.env
    chmod 600 $LIS_HOME/.env
    
    success "Environment file created"
}

# Start services
start_services() {
    log "Starting services..."
    
    systemctl start postgresql
    systemctl start nginx
    systemctl start $SERVICE_NAME
    
    # Wait for services to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet $SERVICE_NAME; then
        success "LIS service started successfully"
    else
        error "Failed to start LIS service"
        exit 1
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check if API is responding
    if curl -f http://localhost:8080/health >/dev/null 2>&1; then
        success "Health check passed"
    else
        warning "Health check failed - service may still be starting"
    fi
}

# Main deployment function
main() {
    log "Starting LIS production deployment..."
    
    check_root
    install_dependencies
    create_user
    create_directories
    setup_python
    deploy_application
    setup_database
    create_env_file
    install_service
    configure_nginx
    setup_firewall
    start_services
    health_check
    
    success "LIS deployment completed successfully!"
    
    echo
    echo "=========================================="
    echo "   LIS Production Deployment Complete"
    echo "=========================================="
    echo
    echo "Services:"
    echo "  - TCP Server: localhost:8000"
    echo "  - REST API: http://localhost:8080"
    echo "  - Web Interface: http://localhost/"
    echo
    echo "Management Commands:"
    echo "  - Start service: systemctl start lis"
    echo "  - Stop service: systemctl stop lis"
    echo "  - Service status: systemctl status lis"
    echo "  - View logs: journalctl -u lis -f"
    echo
    echo "Configuration files:"
    echo "  - Application: $LIS_HOME"
    echo "  - Environment: $LIS_HOME/.env"
    echo "  - Service: /etc/systemd/system/lis.service"
    echo
}

# Run main function
main "$@" 