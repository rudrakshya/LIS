"""
Task Scheduler Service - Periodic task management
Handles scheduled tasks like data cleanup, report generation, and system maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Any
from dataclasses import dataclass

from ..core.database import db_manager
from ..models.sample import Sample
from ..models.test_result import TestResult

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    name: str
    func: Callable
    interval_seconds: int
    next_run: datetime
    enabled: bool = True
    last_run: datetime = None
    run_count: int = 0
    error_count: int = 0


class TaskScheduler:
    """Scheduler for periodic tasks"""
    
    def __init__(self):
        self.running = False
        self.tasks: Dict[str, ScheduledTask] = {}
        
        # Register default tasks
        self._register_default_tasks()
        
        logger.info("TaskScheduler initialized")
    
    async def start(self):
        """Start the task scheduler"""
        self.running = True
        
        # Start the scheduler loop
        asyncio.create_task(self._scheduler_loop())
        
        logger.info("TaskScheduler service started")
    
    async def stop(self):
        """Stop the task scheduler"""
        self.running = False
        logger.info("TaskScheduler service stopped")
    
    def _register_default_tasks(self):
        """Register default scheduled tasks"""
        
        # Cleanup old logs - every hour
        self.add_task(
            "cleanup_logs",
            self._cleanup_old_logs,
            interval_seconds=3600  # 1 hour
        )
        
        # Database maintenance - every 6 hours
        self.add_task(
            "db_maintenance",
            self._database_maintenance,
            interval_seconds=21600  # 6 hours
        )
        
        # Generate daily reports - every 24 hours at 2 AM
        self.add_task(
            "daily_reports",
            self._generate_daily_reports,
            interval_seconds=86400,  # 24 hours
            start_time="02:00"
        )
        
        # System health check - every 5 minutes
        self.add_task(
            "health_check",
            self._system_health_check,
            interval_seconds=300  # 5 minutes
        )
        
        # Archive old data - every week
        self.add_task(
            "archive_data",
            self._archive_old_data,
            interval_seconds=604800  # 1 week
        )
    
    def add_task(self, name: str, func: Callable, interval_seconds: int, 
                 start_time: str = None, enabled: bool = True):
        """Add a new scheduled task"""
        
        # Calculate next run time
        now = datetime.now()
        if start_time:
            # Parse time string (HH:MM format)
            hour, minute = map(int, start_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)
        else:
            next_run = now + timedelta(seconds=interval_seconds)
        
        task = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            next_run=next_run,
            enabled=enabled
        )
        
        self.tasks[name] = task
        logger.info(f"Scheduled task '{name}' added, next run: {next_run}")
    
    def enable_task(self, name: str):
        """Enable a scheduled task"""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Task '{name}' enabled")
    
    def disable_task(self, name: str):
        """Disable a scheduled task"""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Task '{name}' disabled")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Starting task scheduler loop")
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check each task
                for task_name, task in self.tasks.items():
                    if not task.enabled:
                        continue
                    
                    if now >= task.next_run:
                        await self._run_task(task)
                
                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        try:
            logger.info(f"Running scheduled task: {task.name}")
            
            # Run the task
            if asyncio.iscoroutinefunction(task.func):
                await task.func()
            else:
                task.func()
            
            # Update task statistics
            task.last_run = datetime.now()
            task.run_count += 1
            task.next_run = task.last_run + timedelta(seconds=task.interval_seconds)
            
            logger.info(f"Task '{task.name}' completed successfully")
            
        except Exception as e:
            logger.error(f"Error running task '{task.name}': {str(e)}")
            task.error_count += 1
            
            # Still schedule next run
            task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)
    
    # Default task implementations
    
    async def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            # This would clean up log files older than a certain age
            # Implementation depends on your logging configuration
            logger.info("Performing log cleanup...")
            
            # Example: clean logs older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Add actual log cleanup logic here
            
            logger.info("Log cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in log cleanup: {str(e)}")
    
    async def _database_maintenance(self):
        """Perform database maintenance tasks"""
        try:
            logger.info("Performing database maintenance...")
            
            with db_manager.get_session() as session:
                # Update statistics
                session.execute("ANALYZE;")
                
                # Vacuum if using SQLite
                if 'sqlite' in str(session.get_bind().url):
                    session.execute("VACUUM;")
                
                session.commit()
            
            logger.info("Database maintenance completed")
            
        except Exception as e:
            logger.error(f"Error in database maintenance: {str(e)}")
    
    async def _generate_daily_reports(self):
        """Generate daily reports"""
        try:
            logger.info("Generating daily reports...")
            
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            with db_manager.get_session() as session:
                # Count samples processed yesterday
                samples_count = session.query(Sample).filter(
                    Sample.received_date >= yesterday,
                    Sample.received_date < today
                ).count()
                
                # Count results processed yesterday
                results_count = session.query(TestResult).filter(
                    TestResult.result_date >= yesterday,
                    TestResult.result_date < today
                ).count()
                
                logger.info(f"Daily report - Samples: {samples_count}, Results: {results_count}")
            
            # Here you could send email reports, generate PDF files, etc.
            
            logger.info("Daily reports generated")
            
        except Exception as e:
            logger.error(f"Error generating daily reports: {str(e)}")
    
    async def _system_health_check(self):
        """Perform system health checks"""
        try:
            logger.debug("Performing system health check...")
            
            # Check database connection
            if not db_manager.test_connection():
                logger.warning("Database health check failed")
                return
            
            # Check disk space
            # Check memory usage
            # Check service status
            # Add other health checks as needed
            
            logger.debug("System health check passed")
            
        except Exception as e:
            logger.error(f"Error in system health check: {str(e)}")
    
    async def _archive_old_data(self):
        """Archive old data"""
        try:
            logger.info("Archiving old data...")
            
            # Archive data older than 1 year
            cutoff_date = datetime.now() - timedelta(days=365)
            
            with db_manager.get_session() as session:
                # Count old results
                old_results = session.query(TestResult).filter(
                    TestResult.result_date < cutoff_date
                ).count()
                
                if old_results > 0:
                    logger.info(f"Found {old_results} old results to archive")
                    # Here you would implement archival logic
                    # For example: move to archive tables, export to files, etc.
                
                # Count old samples
                old_samples = session.query(Sample).filter(
                    Sample.received_date < cutoff_date
                ).count()
                
                if old_samples > 0:
                    logger.info(f"Found {old_samples} old samples to archive")
            
            logger.info("Data archival completed")
            
        except Exception as e:
            logger.error(f"Error in data archival: {str(e)}")
    
    def get_task_status(self) -> List[Dict[str, Any]]:
        """Get status of all scheduled tasks"""
        status = []
        
        for name, task in self.tasks.items():
            status.append({
                'name': name,
                'enabled': task.enabled,
                'next_run': task.next_run.isoformat(),
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'interval_seconds': task.interval_seconds
            })
        
        return status 