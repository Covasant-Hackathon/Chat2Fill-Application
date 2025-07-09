import sqlite3
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
import hashlib
from utils.database_config import DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for the form parsing and conversational bot system."""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.db_path = self.config.get_database_path()
        self.ensure_database_directory()
        self.initialize_database()
        self._apply_pragma_settings()

    def ensure_database_directory(self):
        """Create database directory if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

        # Apply pragma settings for optimization
        pragma_settings = self.config.get_pragma_settings()
        for pragma, value in pragma_settings.items():
            conn.execute(f"PRAGMA {pragma} = {value}")

        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {str(e)}")
            raise
        finally:
            conn.close()

    def _apply_pragma_settings(self):
        """Apply SQLite PRAGMA settings for optimization."""
        with self.get_db_connection() as conn:
            pragma_settings = self.config.get_pragma_settings()
            for pragma, value in pragma_settings.items():
                conn.execute(f"PRAGMA {pragma} = {value}")
            conn.commit()
            logger.info("Applied SQLite PRAGMA settings for optimization")

    def initialize_database(self):
        """Initialize database with all required tables."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Users table for session management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    preferred_language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Forms table to store parsed form schemas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    form_url TEXT,
                    form_type TEXT NOT NULL,
                    form_title TEXT,
                    form_description TEXT,
                    form_schema TEXT NOT NULL,  -- JSON string
                    parsing_status TEXT DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # Form fields table with multilingual support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS form_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    form_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    field_type TEXT NOT NULL,
                    field_label TEXT,
                    field_placeholder TEXT,
                    field_required BOOLEAN DEFAULT 0,
                    field_options TEXT,  -- JSON string for select/radio options
                    field_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (form_id) REFERENCES forms (id) ON DELETE CASCADE
                )
            """)

            # Prompts/Questions generated for form fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    form_field_id INTEGER NOT NULL,
                    prompt_text TEXT NOT NULL,
                    prompt_type TEXT DEFAULT 'question',
                    language TEXT DEFAULT 'en',
                    context_info TEXT,  -- Additional context for the prompt
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (form_field_id) REFERENCES form_fields (id) ON DELETE CASCADE
                )
            """)

            # Conversations to track user interaction sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    form_id INTEGER NOT NULL,
                    conversation_status TEXT DEFAULT 'active',
                    current_field_index INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (form_id) REFERENCES forms (id) ON DELETE CASCADE
                )
            """)

            # User responses to prompts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    response_language TEXT DEFAULT 'en',
                    confidence_score REAL DEFAULT 1.0,
                    validation_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE
                )
            """)

            # Translations table for multilingual support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_text TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    translation_type TEXT DEFAULT 'automatic',  -- automatic, manual, verified
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_text, source_language, target_language)
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_session ON users(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_forms_user ON forms(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_form_fields_form ON form_fields(form_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_field ON prompts(form_field_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_conversation ON user_responses(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_translations_source ON translations(source_text, source_language)")

            conn.commit()
            logger.info("Database initialized successfully")

    # User Management
    def create_user_session(self, ip_address: str = None, user_agent: str = None,
                           preferred_language: str = 'en') -> str:
        """Create a new user session and return session ID."""
        session_id = str(uuid.uuid4())

        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (session_id, ip_address, user_agent, preferred_language)
                VALUES (?, ?, ?, ?)
            """, (session_id, ip_address, user_agent, preferred_language))
            conn.commit()
            logger.info(f"Created new user session: {session_id}")
            return session_id

    def get_user_by_session(self, session_id: str) -> Optional[Dict]:
        """Get user by session ID."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_activity(self, session_id: str):
        """Update user's last activity timestamp."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()

    def update_user_language(self, session_id: str, language: str):
        """Update user's preferred language."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET preferred_language = ?
                WHERE session_id = ?
            """, (language, session_id))
            conn.commit()

    # Form Management
    def save_form(self, user_id: int, form_url: str, form_type: str, form_schema: Dict,
                  form_title: str = None, form_description: str = None) -> int:
        """Save parsed form schema to database."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO forms (user_id, form_url, form_type, form_title,
                                 form_description, form_schema)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, form_url, form_type, form_title, form_description,
                  json.dumps(form_schema)))
            conn.commit()
            form_id = cursor.lastrowid
            logger.info(f"Saved form with ID: {form_id}")
            return form_id

    def get_form(self, form_id: int) -> Optional[Dict]:
        """Get form by ID."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM forms WHERE id = ?", (form_id,))
            row = cursor.fetchone()
            if row:
                form_data = dict(row)
                form_data['form_schema'] = json.loads(form_data['form_schema'])
                return form_data
            return None

    def get_user_forms(self, user_id: int) -> List[Dict]:
        """Get all forms for a user."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM forms WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            forms = []
            for row in cursor.fetchall():
                form_data = dict(row)
                form_data['form_schema'] = json.loads(form_data['form_schema'])
                forms.append(form_data)
            return forms

    # Form Fields Management
    def save_form_fields(self, form_id: int, fields: List[Dict]) -> List[int]:
        """Save form fields to database."""
        field_ids = []
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            for i, field in enumerate(fields):
                cursor.execute("""
                    INSERT INTO form_fields (form_id, field_name, field_type, field_label,
                                           field_placeholder, field_required, field_options, field_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (form_id, field.get('name'), field.get('type'), field.get('label'),
                      field.get('placeholder'), field.get('required', False),
                      json.dumps(field.get('options', [])), i))
                field_ids.append(cursor.lastrowid)
            conn.commit()
            logger.info(f"Saved {len(field_ids)} form fields for form {form_id}")
            return field_ids

    def get_form_fields(self, form_id: int) -> List[Dict]:
        """Get all fields for a form."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM form_fields WHERE form_id = ?
                ORDER BY field_order
            """, (form_id,))
            fields = []
            for row in cursor.fetchall():
                field_data = dict(row)
                field_data['field_options'] = json.loads(field_data['field_options'])
                fields.append(field_data)
            return fields

    # Prompts Management
    def save_prompts(self, form_field_id: int, prompts: List[Dict]) -> List[int]:
        """Save generated prompts for form fields."""
        prompt_ids = []
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            for prompt in prompts:
                cursor.execute("""
                    INSERT INTO prompts (form_field_id, prompt_text, prompt_type,
                                       language, context_info)
                    VALUES (?, ?, ?, ?, ?)
                """, (form_field_id, prompt.get('text'), prompt.get('type', 'question'),
                      prompt.get('language', 'en'), prompt.get('context')))
                prompt_ids.append(cursor.lastrowid)
            conn.commit()
            logger.info(f"Saved {len(prompt_ids)} prompts for field {form_field_id}")
            return prompt_ids

    def get_prompts_for_field(self, form_field_id: int, language: str = 'en') -> List[Dict]:
        """Get prompts for a specific form field."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM prompts WHERE form_field_id = ? AND language = ?
                ORDER BY created_at
            """, (form_field_id, language))
            return [dict(row) for row in cursor.fetchall()]

    # Conversation Management
    def create_conversation(self, user_id: int, form_id: int, language: str = 'en') -> int:
        """Create a new conversation session."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (user_id, form_id, language)
                VALUES (?, ?, ?)
            """, (user_id, form_id, language))
            conn.commit()
            conversation_id = cursor.lastrowid
            logger.info(f"Created conversation: {conversation_id}")
            return conversation_id

    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        """Get conversation by ID."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_conversation_progress(self, conversation_id: int, current_field_index: int):
        """Update conversation progress."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations SET current_field_index = ?
                WHERE id = ?
            """, (current_field_index, conversation_id))
            conn.commit()

    def complete_conversation(self, conversation_id: int):
        """Mark conversation as completed."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations SET conversation_status = 'completed',
                                       completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (conversation_id,))
            conn.commit()

    # User Response Management
    def save_user_response(self, conversation_id: int, prompt_id: int, response_text: str,
                          response_language: str = 'en', confidence_score: float = 1.0) -> int:
        """Save user response to a prompt."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_responses (conversation_id, prompt_id, response_text,
                                          response_language, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, prompt_id, response_text, response_language, confidence_score))
            conn.commit()
            response_id = cursor.lastrowid
            logger.info(f"Saved user response: {response_id}")
            return response_id

    def get_conversation_responses(self, conversation_id: int) -> List[Dict]:
        """Get all responses for a conversation."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ur.*, p.prompt_text, p.prompt_type, ff.field_name, ff.field_label
                FROM user_responses ur
                JOIN prompts p ON ur.prompt_id = p.id
                JOIN form_fields ff ON p.form_field_id = ff.id
                WHERE ur.conversation_id = ?
                ORDER BY ur.created_at
            """, (conversation_id,))
            return [dict(row) for row in cursor.fetchall()]

    def update_response_validation(self, response_id: int, validation_status: str):
        """Update response validation status."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_responses SET validation_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (validation_status, response_id))
            conn.commit()

    # Translation Management
    def save_translation(self, source_text: str, source_language: str, target_text: str,
                        target_language: str, translation_type: str = 'automatic') -> int:
        """Save translation to database."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO translations
                (source_text, source_language, target_text, target_language, translation_type)
                VALUES (?, ?, ?, ?, ?)
            """, (source_text, source_language, target_text, target_language, translation_type))
            conn.commit()
            return cursor.lastrowid

    def get_translation(self, source_text: str, source_language: str,
                       target_language: str) -> Optional[str]:
        """Get translation from database."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT target_text FROM translations
                WHERE source_text = ? AND source_language = ? AND target_language = ?
            """, (source_text, source_language, target_language))
            row = cursor.fetchone()
            return row[0] if row else None

    # Analytics and Cleanup
    def get_user_statistics(self, user_id: int) -> Dict:
        """Get user statistics."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Get form count
            cursor.execute("SELECT COUNT(*) FROM forms WHERE user_id = ?", (user_id,))
            form_count = cursor.fetchone()[0]

            # Get conversation count
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
            conversation_count = cursor.fetchone()[0]

            # Get completed conversation count
            cursor.execute("""
                SELECT COUNT(*) FROM conversations
                WHERE user_id = ? AND conversation_status = 'completed'
            """, (user_id,))
            completed_conversations = cursor.fetchone()[0]

            # Get response count
            cursor.execute("""
                SELECT COUNT(*) FROM user_responses ur
                JOIN conversations c ON ur.conversation_id = c.id
                WHERE c.user_id = ?
            """, (user_id,))
            response_count = cursor.fetchone()[0]

            return {
                'form_count': form_count,
                'conversation_count': conversation_count,
                'completed_conversations': completed_conversations,
                'response_count': response_count
            }

    def cleanup_old_sessions(self, days_old: int = None):
        """Clean up old user sessions and related data."""
        if days_old is None:
            days_old = self.config.get_session_timeout_days()
        cutoff_date = datetime.now() - timedelta(days=days_old)

        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM users WHERE last_active < ?
            """, (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old user sessions")
            return deleted_count

    def backup_database(self, backup_path: str = None):
        """Create a backup of the database."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.config.get_backup_path()
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"form_bot_backup_{timestamp}.db")

        with self.get_db_connection() as conn:
            with sqlite3.connect(backup_path) as backup_conn:
                conn.backup(backup_conn)
        logger.info(f"Database backed up to: {backup_path}")

        # Clean up old backups
        self._cleanup_old_backups()
        return backup_path

    def _cleanup_old_backups(self):
        """Clean up old backup files."""
        backup_dir = self.config.get_backup_path()
        max_backups = self.config.get_max_backups()

        if not os.path.exists(backup_dir):
            return

        # Get all backup files
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("form_bot_backup_") and filename.endswith(".db"):
                file_path = os.path.join(backup_dir, filename)
                backup_files.append((file_path, os.path.getmtime(file_path)))

        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)

        # Delete excess backups
        for file_path, _ in backup_files[max_backups:]:
            try:
                os.remove(file_path)
                logger.info(f"Deleted old backup: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete backup {file_path}: {str(e)}")

    def get_database_info(self) -> Dict:
        """Get database information and statistics."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Get table sizes
            tables = ['users', 'forms', 'form_fields', 'prompts', 'conversations',
                     'user_responses', 'translations']
            table_sizes = {}

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_sizes[table] = cursor.fetchone()[0]

            # Get database file size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                'database_path': self.db_path,
                'database_size_bytes': db_size,
                'table_sizes': table_sizes,
                'config': {
                    'session_timeout_days': self.config.get_session_timeout_days(),
                    'auto_backup_enabled': self.config.is_auto_backup_enabled(),
                    'backup_interval_hours': self.config.get_backup_interval_hours(),
                    'max_backups': self.config.get_max_backups()
                }
            }

    def get_prompts_for_field(self, field_id: int, language: str = 'en') -> List[Dict]:
        """Get prompts for a specific field."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM prompts
                WHERE form_field_id = ? AND language = ?
                ORDER BY created_at
            """, (field_id, language))
            return [dict(row) for row in cursor.fetchall()]

    def create_prompt(self, form_field_id: int, prompt_text: str, language: str = 'en',
                     prompt_type: str = 'question', context_info: str = None) -> int:
        """Create a new prompt for a form field."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prompts (form_field_id, prompt_text, prompt_type, language, context_info)
                VALUES (?, ?, ?, ?, ?)
            """, (form_field_id, prompt_text, prompt_type, language, context_info))
            conn.commit()
            return cursor.lastrowid

    def get_form_by_id(self, form_id: int) -> Optional[Dict]:
        """Get form by ID."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM forms WHERE id = ?", (form_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_form_fields(self, form_id: int) -> List[Dict]:
        """Get all fields for a form."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM form_fields
                WHERE form_id = ?
                ORDER BY field_order, id
            """, (form_id,))
            return [dict(row) for row in cursor.fetchall()]

    def create_form(self, user_id: int, form_url: str, form_type: str,
                   form_title: str = None, form_schema: str = None) -> int:
        """Create a new form."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO forms (user_id, form_url, form_type, form_title, form_schema)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, form_url, form_type, form_title, form_schema))
            conn.commit()
            return cursor.lastrowid

    def create_form_field(self, form_id: int, field_name: str, field_type: str,
                         field_label: str = None, field_required: bool = False,
                         field_options: str = None, field_order: int = 0) -> int:
        """Create a new form field."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO form_fields (form_id, field_name, field_type, field_label,
                                       field_required, field_options, field_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (form_id, field_name, field_type, field_label, field_required, field_options, field_order))
            conn.commit()
            return cursor.lastrowid
