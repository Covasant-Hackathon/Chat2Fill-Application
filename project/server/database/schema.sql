-- Database Schema for Form Parser Application
-- SQLite3 Database Schema

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Users table - stores user session information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferred_language TEXT DEFAULT 'en',
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    user_agent TEXT,
    ip_address TEXT
);

-- Forms table - stores parsed form information
CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    url TEXT,
    form_type TEXT NOT NULL, -- 'google', 'typeform', 'microsoft', 'custom', 'html'
    raw_schema TEXT, -- Original form schema as JSON
    parsed_schema TEXT, -- Processed form schema as JSON
    translated_schema TEXT, -- Translated schema as JSON
    gemini_validation TEXT, -- Gemini validation response
    status TEXT DEFAULT 'active', -- 'active', 'completed', 'abandoned'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Questions table - stores generated questions for form fields
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    field_type TEXT, -- 'text', 'email', 'number', 'select', 'textarea', etc.
    question_text_en TEXT NOT NULL,
    question_text_translated TEXT,
    is_required BOOLEAN DEFAULT 0,
    order_index INTEGER DEFAULT 0,
    field_options TEXT, -- JSON array of options for select/radio fields
    validation_rules TEXT, -- JSON object with validation rules
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
);

-- Responses table - stores user responses to questions
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    form_id INTEGER NOT NULL,
    response_text_en TEXT,
    response_text_translated TEXT,
    response_value TEXT, -- Actual form field value
    confidence_score REAL DEFAULT 0.0, -- LLM confidence in response
    is_validated BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
);

-- Conversations table - stores conversation history
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    form_id INTEGER NOT NULL,
    question_id INTEGER,
    message_type TEXT NOT NULL, -- 'user', 'assistant', 'system'
    message_text_en TEXT,
    message_text_translated TEXT,
    context_data TEXT, -- JSON object with additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL
);

-- Session activities table - tracks user session activities
CREATE TABLE IF NOT EXISTS session_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL, -- 'form_parse', 'question_answer', 'form_submit', 'session_start', 'session_end'
    activity_data TEXT, -- JSON object with activity details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Form submissions table - stores final form submission attempts
CREATE TABLE IF NOT EXISTS form_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    submission_status TEXT NOT NULL, -- 'success', 'failed', 'partial'
    submitted_data TEXT, -- JSON object with submitted form data
    error_message TEXT,
    submission_url TEXT,
    screenshots
