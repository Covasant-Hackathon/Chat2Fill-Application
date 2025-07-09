import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import json

# Create database engine
DATABASE_URL = "sqlite:///./database/form_parser.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

class User(Base):
    """User model for session management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    preferred_language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)

    # Relationships
    forms = relationship("Form", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("ConversationHistory", back_populates="user", cascade="all, delete-orphan")

class Form(Base):
    """Form model for storing parsed form information"""
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String(2000), nullable=True)
    form_type = Column(String(50), nullable=False)  # google, typeform, microsoft, custom
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    original_schema = Column(SQLiteJSON, nullable=False)  # Original form schema
    parsed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="forms")
    fields = relationship("FormField", back_populates="form", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="form", cascade="all, delete-orphan")

class FormField(Base):
    """Individual form field information"""
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    field_name = Column(String(200), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, email, select, checkbox, etc.
    field_label = Column(String(500), nullable=True)
    field_placeholder = Column(String(500), nullable=True)
    is_required = Column(Boolean, default=False)
    field_options = Column(SQLiteJSON, nullable=True)  # For select, radio, checkbox options
    field_order = Column(Integer, default=0)
    field_metadata = Column(SQLiteJSON, nullable=True)  # Additional field info

    # Relationships
    form = relationship("Form", back_populates="fields")
    prompts = relationship("Prompt", back_populates="field", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="field", cascade="all, delete-orphan")
    multilingual_content = relationship("MultilingualContent", back_populates="field", cascade="all, delete-orphan")

class Prompt(Base):
    """Generated prompts/questions for form fields"""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    original_prompt = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    prompt_type = Column(String(50), default="question")  # question, instruction, validation
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    field = relationship("FormField", back_populates="prompts")
    multilingual_content = relationship("MultilingualContent", back_populates="prompt", cascade="all, delete-orphan")

class MultilingualContent(Base):
    """Multilingual translations for prompts and field labels"""
    __tablename__ = "multilingual_content"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=True)
    language_code = Column(String(10), nullable=False)
    content_type = Column(String(50), nullable=False)  # label, placeholder, prompt, option
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    translation_source = Column(String(50), default="llm")  # llm, manual, api
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    field = relationship("FormField", back_populates="multilingual_content")
    prompt = relationship("Prompt", back_populates="multilingual_content")

    # Ensure unique translations per content type and language
    __table_args__ = (
        UniqueConstraint('field_id', 'prompt_id', 'language_code', 'content_type', name='unique_translation'),
    )

class UserResponse(Base):
    """User responses to form fields"""
    __tablename__ = "user_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    response_text = Column(Text, nullable=True)
    response_data = Column(SQLiteJSON, nullable=True)  # For complex responses
    language_code = Column(String(10), nullable=False)
    confidence_score = Column(Integer, default=0)  # 0-100 confidence in response
    is_final = Column(Boolean, default=False)
    responded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="responses")
    form = relationship("Form", back_populates="responses")
    field = relationship("FormField", back_populates="responses")

class ConversationHistory(Base):
    """Chat history for conversational interactions"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_type = Column(String(20), nullable=False)  # human, ai, system
    message_content = Column(Text, nullable=False)
    language_code = Column(String(10), nullable=False)
    context_data = Column(SQLiteJSON, nullable=True)  # Additional context
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="conversations")

class SystemLog(Base):
    """System logs for debugging and monitoring"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    log_level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    log_message = Column(Text, nullable=False)
    log_data = Column(SQLiteJSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Database utility functions
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)

def init_database():
    """Initialize database with tables"""
    # Ensure database directory exists
    os.makedirs("database", exist_ok=True)

    # Create tables
    create_tables()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
