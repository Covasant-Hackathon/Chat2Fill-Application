import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Configuration settings for the database."""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from environment variables or defaults."""
        return {
            'database_path': os.getenv('DATABASE_PATH', './database/form_bot.db'),
            'backup_path': os.getenv('DATABASE_BACKUP_PATH', './database/backups'),
            'session_timeout_days': int(os.getenv('SESSION_TIMEOUT_DAYS', '7')),
            'auto_backup_enabled': os.getenv('AUTO_BACKUP_ENABLED', 'true').lower() == 'true',
            'backup_interval_hours': int(os.getenv('BACKUP_INTERVAL_HOURS', '24')),
            'max_backups': int(os.getenv('MAX_BACKUPS', '7')),
            'pragma_settings': {
                'journal_mode': os.getenv('SQLITE_JOURNAL_MODE', 'WAL'),
                'synchronous': os.getenv('SQLITE_SYNCHRONOUS', 'NORMAL'),
                'cache_size': int(os.getenv('SQLITE_CACHE_SIZE', '10000')),
                'temp_store': os.getenv('SQLITE_TEMP_STORE', 'MEMORY'),
                'mmap_size': int(os.getenv('SQLITE_MMAP_SIZE', '268435456')),  # 256MB
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def get_database_path(self) -> str:
        """Get database file path."""
        return self.config['database_path']

    def get_backup_path(self) -> str:
        """Get backup directory path."""
        return self.config['backup_path']

    def get_pragma_settings(self) -> Dict[str, Any]:
        """Get SQLite PRAGMA settings."""
        return self.config['pragma_settings']

    def is_auto_backup_enabled(self) -> bool:
        """Check if auto backup is enabled."""
        return self.config['auto_backup_enabled']

    def get_session_timeout_days(self) -> int:
        """Get session timeout in days."""
        return self.config['session_timeout_days']

    def get_backup_interval_hours(self) -> int:
        """Get backup interval in hours."""
        return self.config['backup_interval_hours']

    def get_max_backups(self) -> int:
        """Get maximum number of backups to keep."""
        return self.config['max_backups']

    def validate_config(self) -> bool:
        """Validate configuration settings."""
        try:
            # Check database path
            db_dir = os.path.dirname(self.get_database_path())
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")

            # Check backup path
            backup_dir = self.get_backup_path()
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
                logger.info(f"Created backup directory: {backup_dir}")

            # Validate numeric settings
            if self.get_session_timeout_days() <= 0:
                logger.warning("Session timeout days must be positive, using default: 7")
                self.config['session_timeout_days'] = 7

            if self.get_backup_interval_hours() <= 0:
                logger.warning("Backup interval hours must be positive, using default: 24")
                self.config['backup_interval_hours'] = 24

            if self.get_max_backups() <= 0:
                logger.warning("Max backups must be positive, using default: 7")
                self.config['max_backups'] = 7

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

    def __repr__(self) -> str:
        """String representation of config."""
        return f"DatabaseConfig(database_path='{self.get_database_path()}')"
