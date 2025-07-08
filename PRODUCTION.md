# Laboratory Information System (LIS) - Production Deployment Guide

## Overview

This guide explains how to deploy and run the Laboratory Information System (LIS) in production. The LIS automatically processes laboratory data from medical equipment without requiring user interaction.

## Production Features

### Automatic Operation
- **No Menu Interaction Required**: The system runs autonomously as a service
- **Automatic Message Processing**: Incoming HL7/ASTM messages are processed automatically
- **Auto-Storage**: Test results are automatically stored in the database
- **Real-time Processing**: Messages are processed as they arrive from equipment

### Service Management
- **Systemd Integration**: Runs as a Linux service with automatic restart
- **Docker Support**: Can be deployed using Docker containers
- **Health Monitoring**: Built-in health checks and monitoring endpoints
- **Graceful Shutdown**: Proper cleanup on service stop

### Data Processing
- **Message Queue**: Incoming messages are queued for reliable processing
- **Batch Processing**: Configurable batch sizes for optimal performance
- **Error Handling**: Failed messages are logged for analysis
- **Data Validation**: Automatic validation of incoming data

## Deployment Options

### Option 1: Native Linux Deployment

#### Prerequisites
- Ubuntu/Debian Linux server
- Python 3.11+
- PostgreSQL 12+
- 4GB+ RAM
- 50GB+ storage

#### Quick Deployment
```bash
# Clone repository
git clone <repository-url>
cd lis

# Run deployment script (as root)
sudo chmod +x deployment/deploy.sh
sudo ./deployment/deploy.sh
```

#### Manual Steps
1. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv postgresql nginx
   ```

2. **Create LIS User**
   ```bash
   sudo useradd -r -d /opt/lis -s /bin/bash lis
   sudo mkdir -p /opt/lis
   sudo chown lis:lis /opt/lis
   ```

3. **Deploy Application**
   ```bash
   sudo cp -r src/ /opt/lis/
   sudo cp lis_service.py /opt/lis/
   sudo cp requirements.txt /opt/lis/
   sudo chown -R lis:lis /opt/lis
   ```

4. **Setup Python Environment**
   ```bash
   sudo -u lis python3 -m venv /opt/lis/venv
   sudo -u lis /opt/lis/venv/bin/pip install -r /opt/lis/requirements.txt
   ```

5. **Configure Database**
   ```bash
   sudo -u postgres createuser lis
   sudo -u postgres createdb lis_db -O lis
   sudo -u postgres psql -c "ALTER USER lis WITH PASSWORD 'lis_password';"
   ```

6. **Setup Environment**
   ```bash
   sudo cp env.production /opt/lis/.env
   sudo chown lis:lis /opt/lis/.env
   sudo chmod 600 /opt/lis/.env
   # Edit /opt/lis/.env with your production settings
   ```

7. **Install Service**
   ```bash
   sudo cp deployment/lis.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable lis
   sudo systemctl start lis
   ```

### Option 2: Docker Deployment

#### Using Docker Compose (Recommended)
```bash
# Clone repository
git clone <repository-url>
cd lis/deployment

# Configure environment
cp ../env.production .env
# Edit .env file with your settings

# Deploy
docker-compose up -d
```

#### Manual Docker Deployment
```bash
# Build image
docker build -t lis:latest -f deployment/Dockerfile .

# Run container
docker run -d \
  --name lis-production \
  -p 8000:8000 \
  -p 8080:8080 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=postgresql://lis_user:password@db:5432/lis_db \
  -v /opt/lis/logs:/app/logs \
  -v /opt/lis/data:/app/data \
  lis:latest
```

## Configuration

### Environment Variables

Key production settings in `.env` file:

```bash
# Environment
ENVIRONMENT=production
DEBUG=False

# Database
DATABASE_URL=postgresql://lis_user:password@localhost:5432/lis_db

# Security
SECURITY_SECRET_KEY=your-secret-key-here

# Services
COMM_TCP_HOST=0.0.0.0
COMM_TCP_PORT=8000
API_HOST=127.0.0.1
API_PORT=8080

# Auto-processing
AUTO_PROCESS_MESSAGES=True
AUTO_STORE_RESULTS=True
MESSAGE_QUEUE_SIZE=10000
```

### Service Ports

- **8000**: TCP server for equipment communication
- **8080**: REST API for external systems
- **80/443**: Web interface (via nginx)
- **5432**: PostgreSQL database
- **9090**: Prometheus monitoring (optional)
- **3000**: Grafana dashboard (optional)

## How It Works

### Message Flow
1. **Equipment Connection**: Medical equipment connects to TCP server (port 8000)
2. **Message Reception**: System receives HL7/ASTM messages
3. **Queue Processing**: Messages are queued for processing
4. **Data Extraction**: System parses patient, sample, and result data
5. **Database Storage**: Data is automatically stored in PostgreSQL
6. **Acknowledgment**: Equipment receives confirmation

### Data Processing
```
Equipment → TCP Server → Message Queue → Data Processor → Database
     ↓
 Acknowledgment ← TCP Server ← Processing Status ← Data Processor
```

### No User Interaction Required
- System starts automatically on boot
- Messages are processed automatically
- No menus or manual input needed
- All operations are logged for monitoring

## Monitoring and Management

### Service Management
```bash
# Check service status
systemctl status lis

# Start service
systemctl start lis

# Stop service
systemctl stop lis

# Restart service
systemctl restart lis

# View logs
journalctl -u lis -f
```

### Health Checks
```bash
# Basic health check
curl http://localhost:8080/health

# System status
curl http://localhost:8080/system/status

# System metrics
curl http://localhost:8080/system/metrics
```

### Log Monitoring
```bash
# View real-time logs
tail -f /opt/lis/logs/lis.log

# Search for errors
grep ERROR /opt/lis/logs/lis.log

# Check processing statistics
grep "processed message" /opt/lis/logs/lis.log
```

## Performance and Scaling

### Performance Settings
- **Message Queue Size**: 10,000 messages default
- **Processing Batch Size**: 100 messages per batch
- **Connection Pool**: 10 database connections
- **Memory Limit**: 1GB default (configurable)

### Scaling Options
- **Vertical Scaling**: Increase server resources
- **Database Optimization**: Use connection pooling, indexing
- **Load Balancing**: Multiple API instances behind nginx
- **Message Queuing**: External queue systems (Redis, RabbitMQ)

## Security

### Network Security
- Use firewall to restrict access
- Enable SSL/TLS for API endpoints
- VPN for equipment connections
- Network segmentation

### Application Security
- Strong secret keys
- Database credentials in environment variables
- Limited user permissions
- Regular security updates

### Data Security
- Database encryption at rest
- Encrypted backups
- Audit logging
- HIPAA compliance considerations

## Maintenance

### Backup Strategy
```bash
# Database backup
pg_dump lis_db > backup_$(date +%Y%m%d).sql

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d).tar.gz /opt/lis/.env /etc/systemd/system/lis.service
```

### Updates
```bash
# Stop service
systemctl stop lis

# Update code
cd /opt/lis
git pull origin main

# Update dependencies
venv/bin/pip install -r requirements.txt

# Start service
systemctl start lis
```

### Log Rotation
Logs are automatically rotated based on size and age. Configure in `/etc/logrotate.d/lis`:

```
/opt/lis/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload lis
    endscript
}
```

## Troubleshooting

### Common Issues

**Service Won't Start**
```bash
# Check logs
journalctl -u lis --no-pager
# Check configuration
sudo -u lis /opt/lis/venv/bin/python /opt/lis/lis_service.py
```

**Database Connection Issues**
```bash
# Test database connection
sudo -u lis psql -h localhost -U lis_user -d lis_db
```

**Port Already in Use**
```bash
# Check what's using the port
sudo netstat -tlnp | grep :8000
sudo lsof -i :8000
```

**Memory Issues**
```bash
# Check memory usage
free -h
# Monitor process memory
top -p $(pgrep -f lis_service.py)
```

### Debug Mode
For troubleshooting, run in debug mode:
```bash
sudo -u lis ENVIRONMENT=development /opt/lis/venv/bin/python /opt/lis/lis_service.py
```

## Support

### Monitoring Endpoints
- Health: `GET /health`
- Status: `GET /system/status`
- Metrics: `GET /system/metrics`
- Logs: `GET /system/logs`

### Important Files
- Service file: `/etc/systemd/system/lis.service`
- Application: `/opt/lis/`
- Configuration: `/opt/lis/.env`
- Logs: `/opt/lis/logs/lis.log`

### Contact Information
For production support, maintain documentation of:
- System administrators
- Database administrators
- Application developers
- Equipment vendors

This production deployment ensures your LIS system runs reliably and processes laboratory data automatically without requiring manual intervention. 