# Database package initialization
"""
Database package for the Chat2Fill conversational interface system.

This package provides:
- Database models and schema definitions
- Database services and operations
- Database configuration and setup
- Database administration tools
- Integration layer for form parsing and conversation management
"""

# Import main components for easy access
from .config import initialize_database, check_database_health
from .models import Base, User, Form, FormField, Prompt, MultilingualContent, UserResponse, ConversationHistory, SystemLog
from .services import DatabaseService, DatabaseContext
from .admin import DatabaseAdmin

# Version information
__version__ = "1.0.0"
__author__ = "Chat2Fill Development Team"

# Package level exports
__all__ = [
    'initialize_database',
    'check_database_health',
    'Base',
    'User',
    'Form',
    'FormField',
    'Prompt',
    'MultilingualContent',
    'UserResponse',
    'ConversationHistory',
    'SystemLog',
    'DatabaseService',
    'DatabaseContext',
    'DatabaseAdmin'
]
