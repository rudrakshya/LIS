#!/usr/bin/env python3
"""
Laboratory Information System (LIS) - Production Service Runner
Automatically runs all LIS services without user interaction for production deployment.
"""

import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime
from typing import Optional

import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import LIS components
from src.core.config import settings
from src.core.database import create_tables, db_manager
from src.communication.tcp_server import TCPServer
from src.api.rest_api import app
from src.services.data_processor import DataProcessor
from src.services.scheduler import TaskScheduler

console = Console()
logger = logging.getLogger(__name__)


class LISProductionService:
    """Production service manager for the Laboratory Information System"""
    
    def __init__(self):
        self.tcp_server: Optional[TCPServer] = None
        self.data_processor: Optional[DataProcessor] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.api_server_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("LIS Production Service initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def start_services(self):
        """Start all LIS services"""
        try:
            console.print("\n[bold blue]🏥 Starting LIS Production Services...[/bold blue]")
            
            # 1. Initialize database
            await self._initialize_database()
            
            # 2. Start data processor
            await self._start_data_processor()
            
            # 3. Start TCP server for equipment communication
            await self._start_tcp_server()
            
            # 4. Start REST API server
            await self._start_api_server()
            
            # 5. Start task scheduler
            await self._start_task_scheduler()
            
            # 6. Display service status
            self._display_service_status()
            
            self.running = True
            console.print("\n[bold green]✅ All LIS services started successfully![/bold green]")
            
            # Keep services running
            await self._run_services()
            
        except Exception as e:
            logger.error(f"Failed to start LIS services: {str(e)}")
            console.print(f"[bold red]❌ Failed to start services: {str(e)}[/bold red]")
            await self.stop_services()
            sys.exit(1)
    
    async def _initialize_database(self):
        """Initialize database and create tables"""
        try:
            console.print("📀 Initializing database...")
            
            # Test database connection
            if not db_manager.test_connection():
                raise Exception("Database connection failed")
            
            # Create tables if they don't exist
            create_tables()
            
            console.print("✅ Database initialized successfully")
            logger.info("Database initialized and tables created")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    async def _start_data_processor(self):
        """Start the data processor service"""
        try:
            console.print("🔄 Starting data processor...")
            
            self.data_processor = DataProcessor()
            await self.data_processor.start()
            
            console.print("✅ Data processor started")
            logger.info("Data processor service started")
            
        except Exception as e:
            logger.error(f"Failed to start data processor: {str(e)}")
            raise
    
    async def _start_tcp_server(self):
        """Start TCP server for equipment communication"""
        try:
            console.print(f"🌐 Starting TCP server on {settings.comm_tcp_host}:{settings.comm_tcp_port}...")
            
            # Pass data processor to TCP server for automatic message handling
            self.tcp_server = TCPServer(data_processor=self.data_processor)
            await self.tcp_server.start()
            
            console.print(f"✅ TCP server listening on {settings.comm_tcp_host}:{settings.comm_tcp_port}")
            logger.info(f"TCP server started on {settings.comm_tcp_host}:{settings.comm_tcp_port}")
            
        except Exception as e:
            logger.error(f"Failed to start TCP server: {str(e)}")
            raise
    
    async def _start_api_server(self):
        """Start REST API server in a separate thread"""
        try:
            console.print(f"🚀 Starting REST API server on {settings.api_host}:{settings.api_port}...")
            
            def run_api_server():
                uvicorn.run(
                    app,
                    host=settings.api_host,
                    port=settings.api_port,
                    log_level=settings.log_level.lower(),
                    access_log=not settings.is_production
                )
            
            self.api_server_thread = threading.Thread(target=run_api_server, daemon=True)
            self.api_server_thread.start()
            
            # Give the API server a moment to start
            await asyncio.sleep(2)
            
            console.print(f"✅ REST API server started on http://{settings.api_host}:{settings.api_port}")
            logger.info(f"REST API server started on {settings.api_host}:{settings.api_port}")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {str(e)}")
            raise
    
    async def _start_task_scheduler(self):
        """Start task scheduler for periodic operations"""
        try:
            console.print("⏰ Starting task scheduler...")
            
            self.task_scheduler = TaskScheduler()
            await self.task_scheduler.start()
            
            console.print("✅ Task scheduler started")
            logger.info("Task scheduler service started")
            
        except Exception as e:
            logger.error(f"Failed to start task scheduler: {str(e)}")
            raise
    
    def _display_service_status(self):
        """Display current service status"""
        status_text = Text()
        status_text.append("🏥 Laboratory Information System (LIS) - Production Mode\n\n", style="bold blue")
        status_text.append(f"Version: {settings.app_version}\n", style="green")
        status_text.append(f"Environment: {settings.environment}\n", style="yellow")
        status_text.append(f"Database: {settings.database_url}\n", style="cyan")
        status_text.append(f"TCP Server: {settings.comm_tcp_host}:{settings.comm_tcp_port}\n", style="magenta")
        status_text.append(f"REST API: http://{settings.api_host}:{settings.api_port}\n", style="cyan")
        status_text.append(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", style="white")
        
        panel = Panel(
            status_text,
            title="[bold]LIS Service Status[/bold]",
            border_style="green"
        )
        
        console.print(panel)
    
    async def _run_services(self):
        """Keep services running until shutdown signal received"""
        try:
            console.print("\n[bold cyan]🔄 LIS services are running... Press Ctrl+C to stop[/bold cyan]")
            
            while self.running:
                # Perform health checks
                await self._health_check()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        except Exception as e:
            logger.error(f"Error in service loop: {str(e)}")
        finally:
            await self.stop_services()
    
    async def _health_check(self):
        """Perform health checks on all services"""
        try:
            # Check database connection
            if not db_manager.test_connection():
                logger.warning("Database health check failed")
            
            # Check TCP server
            if self.tcp_server and not self.tcp_server.running:
                logger.warning("TCP server is not running")
            
            # Log service statistics
            if self.tcp_server:
                stats = self.tcp_server.get_server_stats()
                logger.info(f"TCP Server Stats: {stats}")
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
    
    async def stop_services(self):
        """Stop all services gracefully"""
        try:
            console.print("\n[bold yellow]🛑 Stopping LIS services...[/bold yellow]")
            
            # Stop task scheduler
            if self.task_scheduler:
                await self.task_scheduler.stop()
                console.print("✅ Task scheduler stopped")
            
            # Stop TCP server
            if self.tcp_server:
                await self.tcp_server.stop()
                console.print("✅ TCP server stopped")
            
            # Stop data processor
            if self.data_processor:
                await self.data_processor.stop()
                console.print("✅ Data processor stopped")
            
            console.print("[bold green]✅ All services stopped gracefully[/bold green]")
            logger.info("LIS services stopped gracefully")
            
        except Exception as e:
            logger.error(f"Error stopping services: {str(e)}")


async def main():
    """Main entry point for production service"""
    
    # Configure logging for production
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler() if settings.is_development else logging.NullHandler()
        ]
    )
    
    # Create and start LIS service
    lis_service = LISProductionService()
    await lis_service.start_services()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold blue]Thank you for using the LIS System![/bold blue]")
    except Exception as e:
        console.print(f"[bold red]Fatal error: {str(e)}[/bold red]")
        sys.exit(1) 