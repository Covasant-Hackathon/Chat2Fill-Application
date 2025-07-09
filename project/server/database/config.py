import os
import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration management"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.db_dir = self.base_dir
        self.db_path = self.db_dir / "form_parser.db"

        # Ensure database directory exists
        self.db_dir.mkdir(exist_ok=True)

        # Database configuration
        self.database_url = f"sqlite:///{self.db_path}"
        self.engine_config = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30
            },
            "poolclass": StaticPool,
            "pool_pre_ping": True,
            "echo": False  # Set to True for SQL debugging
        }

        # Session configuration
        self.session_config = {
            "autocommit": False,
            "autoflush": False,
            "expire_on_commit": False
        }

        # Initialize engine and session factory
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database engine and session factory"""
        try:
            self.engine = create_engine(self.database_url, **self.engine_config)
            self.SessionLocal = sessionmaker(bind=self.engine, **self.session_config)
            logger.info(f"Database initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        return {
            "database_path": str(self.db_path),
            "database_url": self.database_url,
            "database_exists": self.db_path.exists(),
            "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0
        }

    def backup_database(self, backup_path: str = None) -> str:
        """Create database backup"""
        if not backup_path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_dir / f"form_parser_backup_{timestamp}.db"

        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create database backup: {str(e)}")
            raise

    def restore_database(self, backup_path: str):
        """Restore database from backup"""
        try:
            import shutil
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.db_path)
                logger.info(f"Database restored from: {backup_path}")
            else:
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to restore database: {str(e)}")
            raise

    def reset_database(self):
        """Reset database by removing the file"""
        try:
            if self.db_path.exists():
                os.remove(self.db_path)
                logger.info("Database reset successfully")
            else:
                logger.warning("Database file does not exist")
        except Exception as e:
            logger.error(f"Failed to reset database: {str(e)}")
            raise

# Global database configuration instance
db_config = DatabaseConfig()

# Database session dependency for FastAPI/other frameworks
def get_database_session():
    """Get database session for dependency injection"""
    db = db_config.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database tables
def initialize_database():
    """Initialize database with all tables"""
    try:
        from .models import Base, init_database

        # Create all tables
        Base.metadata.create_all(bind=db_config.engine)

        logger.info("Database tables created successfully")

        # Log database info
        db_info = db_config.get_database_info()
        logger.info(f"Database Info: {db_info}")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

# Database health check
def check_database_health() -> Dict[str, Any]:
    """Check database health and connectivity"""
    try:
        from .models import User

        # Test database connection
        db = db_config.SessionLocal()
        try:
            # Simple query to test connection
            from sqlalchemy import text
            result = db.execute(text("SELECT 1")).fetchone()
            db.close()

            db_info = db_config.get_database_info()

            return {
                "status": "healthy",
                "connection": "successful",
                "database_info": db_info,
                "message": "Database is healthy and accessible"
            }
        except Exception as e:
            db.close()
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "message": "Database connection failed"
            }
    except Exception as e:
        return {
            "status": "error",
            "connection": "unknown",
            "error": str(e),
            "message": "Database health check failed"
        }

# Development utilities
def create_sample_data():
    """Create sample data for testing"""
    try:
        from .models import User, Form, FormField, SessionLocal

        db = SessionLocal()

        # Create sample user
        sample_user = User(
            session_id="sample-session-123",
            preferred_language="en"
        )
        db.add(sample_user)
        db.commit()
        db.refresh(sample_user)

        # Create sample form
        sample_form = Form(
            user_id=sample_user.id,
            url="https://example.com/form",
            form_type="custom",
            title="Sample Form",
            description="A sample form for testing",
            original_schema={"fields": [{"name": "name", "type": "text"}]}
        )
        db.add(sample_form)
        db.commit()
        db.refresh(sample_form)

        # Create sample form field
        sample_field = FormField(
            form_id=sample_form.id,
            field_name="name",
            field_type="text",
            field_label="Your Name",
            field_placeholder="Enter your name",
            is_required=True,
            field_order=1
        )
        db.add(sample_field)
        db.commit()

        db.close()

        logger.info("Sample data created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create sample data: {str(e)}")
        return False

if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing database...")
    if initialize_database():
        print("Database initialized successfully!")

        # Check database health
        health = check_database_health()
        print(f"Database health: {health}")

        # Optionally create sample data
        # create_sample_data()
    else:
        print("Database initialization failed!")
