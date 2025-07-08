"""
Database connection and session management for the LIS system
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from .config import settings
from .exceptions import DatabaseException


# Create SQLAlchemy engine
def create_database_engine():
    """Create database engine based on configuration"""
    
    database_url = settings.database_url
    
    # Special handling for SQLite
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.is_development
        )
    else:
        # PostgreSQL or other databases
        engine = create_engine(
            database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            echo=settings.is_development
        )
    
    return engine


# Create engine instance
engine = create_database_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency function to get database session
    Used with FastAPI Depends()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Database error: {str(e)}")
    finally:
        session.close()


def create_tables():
    """Create all tables in the database"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise DatabaseException(f"Failed to create tables: {str(e)}")


def drop_tables():
    """Drop all tables from the database (use with caution)"""
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        raise DatabaseException(f"Failed to drop tables: {str(e)}")


def get_session() -> Session:
    """Get a database session (for non-FastAPI usage)"""
    return SessionLocal()


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def test_connection() -> bool:
        """Test database connection"""
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    @staticmethod
    def get_table_names() -> list:
        """Get list of all table names"""
        try:
            with engine.connect() as connection:
                # SQLAlchemy 2.x compatible way to get table names
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                return [row[0] for row in result]
        except Exception as e:
            raise DatabaseException(f"Failed to get table names: {str(e)}")
    
    @staticmethod
    def execute_sql(sql: str, params: dict = None):
        """Execute raw SQL (use with caution)"""
        try:
            with engine.connect() as connection:
                return connection.execute(text(sql), params or {})
        except Exception as e:
            raise DatabaseException(f"Failed to execute SQL: {str(e)}")


# Initialize database manager
db_manager = DatabaseManager() 