import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List
from .database_config import DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions with database persistence and security features."""

    def __init__(self, db_manager = None):
        if db_manager is None:
            # Import locally to avoid circular import
            from database_manager import DatabaseManager
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = db_manager
        self.config = self.db_manager.config
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout_hours = 24  # Default session timeout
        self._initialize_session_cleanup()

    def _initialize_session_cleanup(self):
        """Initialize session cleanup settings."""
        # Load any active sessions from database on startup
        self._load_active_sessions()
        logger.info("Session manager initialized")

    def _load_active_sessions(self):
        """Load active sessions from database."""
        try:
            # This would load recent sessions from database
            # For now, we'll start with empty active sessions
            self.active_sessions = {}
            logger.info("Active sessions loaded from database")
        except Exception as e:
            logger.error(f"Failed to load active sessions: {str(e)}")
            self.active_sessions = {}

    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)

    def _hash_ip_address(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        if not ip_address:
            return ""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    def _get_client_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Create a client fingerprint for additional security."""
        if not user_agent or not ip_address:
            return ""
        combined = f"{user_agent}:{ip_address}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def create_session(self, ip_address: str = None, user_agent: str = None,
                      preferred_language: str = 'en', additional_data: Dict = None) -> Dict[str, Any]:
        """
        Create a new user session.

        Args:
            ip_address: Client IP address
            user_agent: Client user agent string
            preferred_language: User's preferred language
            additional_data: Additional session data

        Returns:
            dict: Session information including session_id
        """
        try:
            # Generate session ID
            session_id = self._generate_session_id()

            # Hash sensitive data
            hashed_ip = self._hash_ip_address(ip_address)
            client_fingerprint = self._get_client_fingerprint(user_agent, ip_address)

            # Create session in database
            db_session_id = self.db_manager.create_user_session(
                ip_address=hashed_ip,
                user_agent=user_agent,
                preferred_language=preferred_language
            )

            # Prepare session data
            session_data = {
                'session_id': session_id,
                'db_session_id': db_session_id,
                'user_id': None,  # Will be set when user data is retrieved
                'ip_address': hashed_ip,
                'user_agent': user_agent,
                'preferred_language': preferred_language,
                'client_fingerprint': client_fingerprint,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'active': True,
                'current_form_id': None,
                'current_conversation_id': None,
                'additional_data': additional_data or {}
            }

            # Store in active sessions
            self.active_sessions[session_id] = session_data

            # Get user data from database
            user_data = self.db_manager.get_user_by_session(db_session_id)
            if user_data:
                session_data['user_id'] = user_data['id']

            logger.info(f"Created new session: {session_id}")

            return {
                'session_id': session_id,
                'user_id': session_data['user_id'],
                'preferred_language': preferred_language,
                'created_at': session_data['created_at'].isoformat(),
                'status': 'active'
            }

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by session ID.

        Args:
            session_id: Session ID

        Returns:
            dict or None: Session data if found and valid
        """
        try:
            # Check active sessions first
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]

                # Check if session is expired
                if self._is_session_expired(session_data):
                    self._expire_session(session_id)
                    return None

                # Update last activity
                session_data['last_activity'] = datetime.now()

                # Update database
                if session_data.get('db_session_id'):
                    self.db_manager.update_user_activity(session_data['db_session_id'])

                return session_data

            # Session not in active sessions, might be in database
            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            updates: Dictionary of updates to apply

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False

            # Update session data
            for key, value in updates.items():
                if key in ['session_id', 'db_session_id', 'created_at']:
                    continue  # Protect immutable fields
                session_data[key] = value

            # Update last activity
            session_data['last_activity'] = datetime.now()

            # Update database if needed
            if 'preferred_language' in updates and session_data.get('db_session_id'):
                self.db_manager.update_user_language(
                    session_data['db_session_id'],
                    updates['preferred_language']
                )

            logger.info(f"Updated session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {str(e)}")
            return False

    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if session is expired."""
        if not session_data.get('last_activity'):
            return True

        expiry_time = session_data['last_activity'] + timedelta(hours=self.session_timeout_hours)
        return datetime.now() > expiry_time

    def _expire_session(self, session_id: str):
        """Expire a session."""
        try:
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                session_data['active'] = False
                del self.active_sessions[session_id]
                logger.info(f"Expired session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to expire session {session_id}: {str(e)}")

    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session.

        Args:
            session_id: Session ID to terminate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if session_id in self.active_sessions:
                self._expire_session(session_id)
                logger.info(f"Terminated session: {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {str(e)}")
            return False

    def validate_session(self, session_id: str, ip_address: str = None,
                        user_agent: str = None) -> bool:
        """
        Validate session with additional security checks.

        Args:
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False

            # Check if session is active
            if not session_data.get('active'):
                return False

            # Optional: Validate client fingerprint for additional security
            if ip_address and user_agent:
                current_fingerprint = self._get_client_fingerprint(user_agent, ip_address)
                stored_fingerprint = session_data.get('client_fingerprint')

                if stored_fingerprint and current_fingerprint != stored_fingerprint:
                    logger.warning(f"Client fingerprint mismatch for session: {session_id}")
                    # Optionally, you might want to terminate the session here
                    # return False

            return True

        except Exception as e:
            logger.error(f"Failed to validate session {session_id}: {str(e)}")
            return False

    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            list: List of session data
        """
        try:
            sessions = []
            for session_id, session_data in self.active_sessions.items():
                if session_data.get('user_id') == user_id:
                    sessions.append({
                        'session_id': session_id,
                        'created_at': session_data['created_at'].isoformat(),
                        'last_activity': session_data['last_activity'].isoformat(),
                        'preferred_language': session_data.get('preferred_language'),
                        'active': session_data.get('active', False)
                    })
            return sessions
        except Exception as e:
            logger.error(f"Failed to get user sessions for user {user_id}: {str(e)}")
            return []

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            expired_sessions = []

            for session_id, session_data in self.active_sessions.items():
                if self._is_session_expired(session_data):
                    expired_sessions.append(session_id)

            # Remove expired sessions
            for session_id in expired_sessions:
                self._expire_session(session_id)

            # Also clean up old sessions from database
            db_cleanup_count = self.db_manager.cleanup_old_sessions()

            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions from memory")
            logger.info(f"Cleaned up {db_cleanup_count} old sessions from database")

            return len(expired_sessions) + db_cleanup_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0

    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            dict: Session statistics
        """
        try:
            active_count = len(self.active_sessions)
            total_sessions = active_count

            # Get language distribution
            language_stats = {}
            for session_data in self.active_sessions.values():
                lang = session_data.get('preferred_language', 'en')
                language_stats[lang] = language_stats.get(lang, 0) + 1

            return {
                'active_sessions': active_count,
                'total_sessions': total_sessions,
                'language_distribution': language_stats,
                'session_timeout_hours': self.session_timeout_hours
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {str(e)}")
            return {}

    def set_current_form(self, session_id: str, form_id: int) -> bool:
        """Set current form for a session."""
        return self.update_session(session_id, {'current_form_id': form_id})

    def set_current_conversation(self, session_id: str, conversation_id: int) -> bool:
        """Set current conversation for a session."""
        return self.update_session(session_id, {'current_conversation_id': conversation_id})

    def get_current_form(self, session_id: str) -> Optional[int]:
        """Get current form ID for a session."""
        session_data = self.get_session(session_id)
        return session_data.get('current_form_id') if session_data else None

    def get_current_conversation(self, session_id: str) -> Optional[int]:
        """Get current conversation ID for a session."""
        session_data = self.get_session(session_id)
        return session_data.get('current_conversation_id') if session_data else None

    def __del__(self):
        """Cleanup on destruction."""
        try:
            # Optionally save active sessions to database
            logger.info("Session manager shutting down")
        except:
            pass
