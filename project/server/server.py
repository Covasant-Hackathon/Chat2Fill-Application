import logging
import json
import os
import time
import threading
import asyncio
from typing import Dict, List, Any
from fastmcp import FastMCP
import google.generativeai as genai
from form_parser import FormParser
from llm_conversation import LLMConversation
from multilingual_support import MultilingualSupport
from form_autofiller import FormAutofiller
from database_manager import DatabaseManager
from utils.database_config import DatabaseConfig
from utils.session_manager import SessionManager
from dotenv import load_dotenv
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
parent_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(parent_path)
logger.info("Loading environment variables")

# Directory for saving questions
QUESTIONS_DIR = "questions"
if not os.path.exists(QUESTIONS_DIR):
    os.makedirs(QUESTIONS_DIR)

# Cleanup thread for question files
def cleanup_question_files():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(QUESTIONS_DIR):
                file_path = os.path.join(QUESTIONS_DIR, filename)
                if os.path.isfile(file_path) and filename.startswith("questions_") and filename.endswith(".json"):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 24 * 3600:
                        os.remove(file_path)
                        logger.info(f"Deleted old question file: {file_path}")
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Error during question file cleanup: {str(e)}")
            time.sleep(3600)

cleanup_thread = threading.Thread(target=cleanup_question_files, daemon=True)
cleanup_thread.start()

# Database cleanup thread
def cleanup_database():
    while True:
        try:
            # Clean up old sessions and data every hour
            if 'session_manager' in globals():
                session_manager.cleanup_expired_sessions()
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            time.sleep(3600)

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in .env file")
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=GEMINI_API_KEY)
logger.info("Gemini API configured")

# Initialize Gemini model
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("Gemini model initialized")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    raise

# Initialize database and session management
try:
    db_config = DatabaseConfig()
    db_config.validate_config()
    db_manager = DatabaseManager(db_config)
    session_manager = SessionManager(db_manager)
    logger.info("Database and session management initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise

# Start database cleanup thread
db_cleanup_thread = threading.Thread(target=cleanup_database, daemon=True)
db_cleanup_thread.start()

# Initialize components with database support
try:
    llm_conv = LLMConversation(db_manager)
    multilingual = MultilingualSupport(db_manager)
    autofiller = FormAutofiller()
    logger.info("LLMConversation, MultilingualSupport, and FormAutofiller initialized")
except Exception as e:
    logger.error(f"Failed to initialize components: {str(e)}")
    raise

# Initialize FastMCP
try:
    mcp = FastMCP("Form Parser Server")
    logger.info("FastMCP server initialized with name: Form Parser Server")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {str(e)}")
    raise

@mcp.tool()
async def create_session(ip_address: str = None, user_agent: str = None,
                        preferred_language: str = "en") -> Dict[str, Any]:
    """Create a new user session."""
    try:
        session_info = session_manager.create_session(
            ip_address=ip_address,
            user_agent=user_agent,
            preferred_language=preferred_language
        )
        logger.info(f"Created new session: {session_info['session_id']}")
        return {
            "status": "success",
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return {
            "status": "error",
            "error": f"Failed to create session: {str(e)}"
        }

@mcp.tool()
async def parse_form(url: str, form_type: str, language: str = "en",
                    session_id: str = None) -> Dict[str, Any]:
    """Parse a form from URL with database integration."""
    logger.info(f"Received parse_form request: url={url}, form_type={form_type}, language={language}")

    # Create session if not provided
    if not session_id:
        session_info = session_manager.create_session(preferred_language=language)
        session_id = session_info['session_id']

    # Validate session
    session_data = session_manager.get_session(session_id)
    if not session_data:
        # Auto-create session if it doesn't exist
        logger.info(f"Session {session_id} not found, creating new session")
        session_data = session_manager.create_session(
            ip_address="127.0.0.1",
            user_agent="Chat2Fill-Frontend",
            preferred_language=language,
            additional_data={"auto_created": True, "original_session_id": session_id}
        )
        if not session_data:
            return {
                "status": "error",
                "error": "Failed to create session",
                "session_id": session_id
            }

    try:
        if not url or len(url) > 2000:
            logger.warning(f"Invalid URL: {url[:50]}...")
            return {
                "status": "error",
                "error": "URL is empty or exceeds maximum length of 2000 characters",
                "session_id": session_id,
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        if form_type not in {'google', 'typeform', 'microsoft', 'custom'}:
            logger.warning(f"Invalid form type: {form_type}")
            return {
                "status": "error",
                "error": "Invalid form type. Must be one of: google, typeform, microsoft, custom",
                "session_id": session_id,
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        prompt = f"""
        You are a web form expert. Validate the provided URL and form type.
        - Check if the URL appears to be a valid web form URL.
        - Confirm if the form type matches the expected platform.
        - If ambiguous, suggest the most likely type or default to 'custom'.
        Input: URL: {url}, Form Type: {form_type}
        Output format: {{ "url": "validated URL", "form_type": "validated form type", "is_valid": true/false, "message": "explanation" }}
        """
        gemini_response = model.generate_content(prompt)

        if not hasattr(gemini_response, 'text') or not gemini_response.text:
            logger.error("Invalid Gemini response: No text content")
            return {
                "status": "error",
                "error": "Invalid Gemini response: No text content",
                "session_id": session_id,
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        gemini_data = gemini_response.text.strip()
        if gemini_data.startswith("```json"):
            gemini_data = gemini_data[7:].strip()
        if gemini_data.endswith("```"):
            gemini_data = gemini_data[:-3].strip()

        try:
            gemini_result = json.loads(gemini_data)
            logger.info("Gemini response parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {str(e)}")
            return {
                "status": "error",
                "error": "Failed to parse Gemini response",
                "session_id": session_id,
                "gemini_message": gemini_data,
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        validated_url = gemini_result.get("url")
        validated_form_type = gemini_result.get("form_type")
        if not validated_url or not gemini_result.get("is_valid"):
            logger.warning(f"Invalid input from Gemini: {gemini_result.get('message')}")
            return {
                "status": "error",
                "error": gemini_result.get("message", "Invalid input from Gemini"),
                "session_id": session_id,
                "gemini_message": gemini_result.get("message", ""),
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        parser = FormParser(use_profile=(validated_form_type == 'microsoft'), debug_mode=True)
        form_schema = await parser.parse_form_from_url(validated_url, validated_form_type)

        # Save form to database
        user_id = session_data['user_id']
        form_id = db_manager.save_form(
            user_id=user_id,
            form_url=validated_url,
            form_type=validated_form_type,
            form_schema=form_schema,
            form_title=form_schema.get('title', 'Untitled Form'),
            form_description=form_schema.get('description', '')
        )

        # Save form fields
        if form_schema.get('forms') and form_schema['forms'][0].get('fields'):
            fields = form_schema['forms'][0]['fields']
            field_ids = db_manager.save_form_fields(form_id, fields)
            logger.info(f"Saved {len(field_ids)} fields to database")

        # Update session with current form
        session_manager.set_current_form(session_id, form_id)

        # Translate form schema
        translated_form_schema = multilingual.translate_form_fields(form_schema, language)

        # Generate questions with database persistence
        questions = llm_conv.generate_questions(
            form_schema,
            context=f"Parsing a {validated_form_type} form from {validated_url}",
            language=language,
            form_id=form_id
        )

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        questions_file = os.path.join(QUESTIONS_DIR, f"questions_{timestamp}.json")
        try:
            with open(questions_file, "w", encoding='utf-8') as f:
                json.dump(questions, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved questions to {questions_file}")
        except Exception as e:
            logger.error(f"Failed to save questions to {questions_file}: {str(e)}")

        return {
            "status": "success",
            "form_id": form_id,
            "form_schema": form_schema,
            "translated_form_schema": translated_form_schema,
            "gemini_url": validated_url,
            "gemini_form_type": validated_form_type,
            "gemini_message": gemini_result.get("message", ""),
            "questions": questions,
            "session_id": session_id
        }

    except ValueError as e:
        logger.error(f"ValueError while parsing form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id,
            "gemini_message": gemini_result.get("message", "") if 'gemini_result' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error processing form at '{url}': {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "session_id": session_id,
            "gemini_message": gemini_result.get("message", "") if 'gemini_result' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }

@mcp.tool()
async def parse_html_form(html_input: str, is_file: bool = False, language: str = "en",
                         session_id: str = None) -> Dict[str, Any]:
    """Parse HTML form with database integration."""
    logger.info(f"Received parse_html_form request: is_file={is_file}, language={language}")

    # Create session if not provided
    if not session_id:
        session_info = session_manager.create_session(preferred_language=language)
        session_id = session_info['session_id']

    # Validate session
    session_data = session_manager.get_session(session_id)
    if not session_data:
        # Auto-create session if it doesn't exist
        logger.info(f"Session {session_id} not found, creating new session")
        session_data = session_manager.create_session(
            ip_address="127.0.0.1",
            user_agent="Chat2Fill-Frontend",
            preferred_language=language,
            additional_data={"auto_created": True, "original_session_id": session_id}
        )
        if not session_data:
            return {
                "status": "error",
                "error": "Failed to create session",
                "session_id": session_id
            }

    try:
        if not html_input:
            logger.warning("Empty HTML input provided")
            return {
                "status": "error",
                "error": "HTML input cannot be empty",
                "session_id": session_id,
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        prompt = f"""
        You are a web form expert. Validate the provided HTML content for a valid form structure.
        - Check for <form> tag or form-like elements (input, select, textarea).
        - Return a message indicating validity.
        Input: HTML: {html_input[:1000]}... (truncated)
        Output format: {{ "is_valid": true/false, "message": "explanation" }}
        """
        gemini_response = model.generate_content(prompt)

        gemini_message = ""
        if hasattr(gemini_response, 'text') and gemini_response.text:
            gemini_data = gemini_response.text.strip()
            if gemini_data.startswith("```json"):
                gemini_data = gemini_data[7:].strip()
            if gemini_data.endswith("```"):
                gemini_data = gemini_data[:-3].strip()
            try:
                gemini_result = json.loads(gemini_data)
                gemini_message = gemini_result.get("message", "")
                if not gemini_result.get("is_valid"):
                    logger.warning(f"Gemini validation failed: {gemini_message}")
                    return {
                        "status": "error",
                        "error": gemini_message or "Invalid HTML form structure",
                        "session_id": session_id,
                        "gemini_message": gemini_message,
                        "form_schema": {},
                        "translated_form_schema": {},
                        "questions": []
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini response: {str(e)}")
                gemini_message = gemini_data

        parser = FormParser(debug_mode=True)
        form_schema = await parser.parse_html_content(html_input, is_file)

        # Save form to database
        user_id = session_data['user_id']
        form_id = db_manager.save_form(
            user_id=user_id,
            form_url="<HTML_CONTENT>",
            form_type="html",
            form_schema=form_schema,
            form_title=form_schema.get('title', 'HTML Form'),
            form_description=form_schema.get('description', '')
        )

        # Save form fields
        if form_schema.get('forms') and form_schema['forms'][0].get('fields'):
            fields = form_schema['forms'][0]['fields']
            field_ids = db_manager.save_form_fields(form_id, fields)
            logger.info(f"Saved {len(field_ids)} fields to database")

        # Update session with current form
        session_manager.set_current_form(session_id, form_id)

        # Translate form schema
        translated_form_schema = multilingual.translate_form_fields(form_schema, language)

        # Generate questions with database persistence
        questions = llm_conv.generate_questions(
            form_schema,
            context="Parsing a static HTML form",
            language=language,
            form_id=form_id
        )

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        questions_file = os.path.join(QUESTIONS_DIR, f"questions_{timestamp}.json")
        try:
            with open(questions_file, "w", encoding='utf-8') as f:
                json.dump(questions, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved questions to {questions_file}")
        except Exception as e:
            logger.error(f"Failed to save questions to {questions_file}: {str(e)}")

        return {
            "status": "success",
            "form_id": form_id,
            "form_schema": form_schema,
            "translated_form_schema": translated_form_schema,
            "gemini_message": gemini_message,
            "questions": questions,
            "session_id": session_id
        }

    except ValueError as e:
        logger.error(f"ValueError while parsing HTML: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id,
            "gemini_message": gemini_message if 'gemini_message' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error parsing HTML: {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "session_id": session_id,
            "gemini_message": gemini_message if 'gemini_message' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }

@mcp.tool()
async def start_conversation(session_id: str, form_id: int, language: str = "en") -> Dict[str, Any]:
    """Start a new conversation for a form."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language=language,
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        user_id = session_data['user_id']
        conversation_id = llm_conv.start_conversation(user_id, form_id, language)

        if conversation_id:
            session_manager.set_current_conversation(session_id, conversation_id)
            return {
                "status": "success",
                "conversation_id": conversation_id,
                "session_id": session_id,
                "form_id": form_id,
                "language": language
            }
        else:
            return {"status": "error", "error": "Failed to start conversation"}
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def submit_response(session_id: str, conversation_id: int, prompt_id: int,
                         response_text: str, language: str = "en") -> Dict[str, Any]:
    """Submit a user response to a conversation."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language=language,
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        # Get form and field information
        conversation = db_manager.get_conversation(conversation_id)
        if not conversation:
            return {"status": "error", "error": "Invalid conversation"}

        form_id = conversation['form_id']
        form_fields = db_manager.get_form_fields(form_id)

        # Find the relevant field for this prompt
        prompts = []
        for field in form_fields:
            field_prompts = db_manager.get_prompts_for_field(field['id'], language)
            prompts.extend(field_prompts)

        prompt = next((p for p in prompts if p['id'] == prompt_id), None)
        if not prompt:
            return {"status": "error", "error": "Invalid prompt"}

        # Find the corresponding field
        field = next((f for f in form_fields if f['id'] == prompt['form_field_id']), None)
        if not field:
            return {"status": "error", "error": "Invalid field"}

        # Parse and validate response
        response_data = llm_conv.parse_response(
            response_text,
            field,
            language,
            conversation_id,
            prompt_id
        )

        return {
            "status": "success",
            "response_id": response_data.get("response_id"),
            "valid": response_data["valid"],
            "error": response_data.get("error"),
            "conversation_id": conversation_id,
            "prompt_id": prompt_id
        }
    except Exception as e:
        logger.error(f"Error submitting response: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def get_conversation_status(session_id: str, conversation_id: int) -> Dict[str, Any]:
    """Get the status of a conversation."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language="en",
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        conversation = db_manager.get_conversation(conversation_id)
        if not conversation:
            return {"status": "error", "error": "Invalid conversation"}

        responses = db_manager.get_conversation_responses(conversation_id)

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "conversation_status": conversation['conversation_status'],
            "current_field_index": conversation['current_field_index'],
            "language": conversation['language'],
            "started_at": conversation['started_at'],
            "completed_at": conversation.get('completed_at'),
            "responses": responses
        }
    except Exception as e:
        logger.error(f"Error getting conversation status: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get session information and statistics."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language="en",
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        user_id = session_data['user_id']
        user_stats = db_manager.get_user_statistics(user_id)

        return {
            "status": "success",
            "session_id": session_id,
            "user_id": user_id,
            "preferred_language": session_data.get('preferred_language'),
            "created_at": session_data.get('created_at'),
            "last_activity": session_data.get('last_activity'),
            "current_form_id": session_data.get('current_form_id'),
            "current_conversation_id": session_data.get('current_conversation_id'),
            "statistics": user_stats
        }
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def cleanup_sessions() -> Dict[str, Any]:
    """Clean up expired sessions and old data."""
    try:
        cleaned_sessions = session_manager.cleanup_expired_sessions()

        # Also backup database
        backup_path = db_manager.backup_database()

        return {
            "status": "success",
            "cleaned_sessions": cleaned_sessions,
            "backup_path": backup_path
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def get_database_info() -> Dict[str, Any]:
    """Get database information and statistics."""
    try:
        db_info = db_manager.get_database_info()
        session_stats = session_manager.get_session_statistics()

        return {
            "status": "success",
            "database_info": db_info,
            "session_statistics": session_stats
        }
    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def get_next_question(session_id: str, conversation_id: int, language: str = "en") -> Dict[str, Any]:
    """Get the next question in the conversation."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language=language,
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        conversation = db_manager.get_conversation(conversation_id)
        if not conversation:
            return {"status": "error", "error": "Invalid conversation"}

        form_id = conversation['form_id']
        current_index = conversation['current_field_index']

        # Get form fields
        form_fields = db_manager.get_form_fields(form_id)

        # Check if conversation is complete
        if current_index >= len(form_fields):
            return {
                "status": "complete",
                "message": "All questions have been answered",
                "conversation_id": conversation_id
            }

        # Get the current field
        current_field = form_fields[current_index]

        # Get prompts for the current field
        prompts = db_manager.get_prompts_for_field(current_field['id'], language)

        if not prompts:
            # Generate prompt if not exists
            prompt_text = llm_conv.generate_question_for_field(current_field, language)
            prompt_id = db_manager.create_prompt(current_field['id'], prompt_text, language)
            prompts = [{"id": prompt_id, "prompt_text": prompt_text}]

        current_prompt = prompts[0]  # Use the first prompt

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "field_name": current_field['field_name'],
            "field_type": current_field['field_type'],
            "field_label": current_field['field_label'],
            "field_required": current_field['field_required'],
            "field_options": current_field.get('field_options'),
            "question": current_prompt['prompt_text'],
            "prompt_id": current_prompt['id'],
            "current_index": current_index,
            "total_fields": len(form_fields),
            "language": language
        }
    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def submit_user_response(session_id: str, conversation_id: int, field_name: str,
                              response_text: str, language: str = "en") -> Dict[str, Any]:
    """Submit a user response and get the next question."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language=language,
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        conversation = db_manager.get_conversation(conversation_id)
        if not conversation:
            return {"status": "error", "error": "Invalid conversation"}

        form_id = conversation['form_id']
        current_index = conversation['current_field_index']

        # Get form fields
        form_fields = db_manager.get_form_fields(form_id)

        if current_index >= len(form_fields):
            return {"status": "error", "error": "No more fields to answer"}

        current_field = form_fields[current_index]

        # Get the prompt for this field
        prompts = db_manager.get_prompts_for_field(current_field['id'], language)
        if not prompts:
            return {"status": "error", "error": "No prompt found for field"}

        prompt_id = prompts[0]['id']

        # Validate and save response
        validation_result = llm_conv.validate_response(response_text, current_field, language)
        confidence_score = validation_result.get('confidence', 0.8)

        # Save the response
        response_id = db_manager.save_user_response(
            conversation_id,
            prompt_id,
            response_text,
            language,
            confidence_score
        )

        # Update conversation progress
        db_manager.update_conversation_progress(conversation_id, current_index + 1)

        # Check if conversation is complete
        if current_index + 1 >= len(form_fields):
            db_manager.complete_conversation(conversation_id)
            return {
                "status": "complete",
                "message": "Form completed successfully!",
                "conversation_id": conversation_id,
                "response_id": response_id
            }

        # Get next question
        next_question_result = await get_next_question(session_id, conversation_id, language)

        return {
            "status": "success",
            "message": "Response saved successfully",
            "response_id": response_id,
            "next_question": next_question_result,
            "conversation_id": conversation_id
        }
    except Exception as e:
        logger.error(f"Error submitting response: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def get_conversation_summary(session_id: str, conversation_id: int) -> Dict[str, Any]:
    """Get a summary of the completed conversation."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            # Auto-create session if it doesn't exist
            logger.info(f"Session {session_id} not found, creating new session")
            session_data = session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Chat2Fill-Frontend",
                preferred_language="en",
                additional_data={"auto_created": True, "original_session_id": session_id}
            )
            if not session_data:
                return {"status": "error", "error": "Failed to create session"}

        conversation = db_manager.get_conversation(conversation_id)
        if not conversation:
            return {"status": "error", "error": "Invalid conversation"}

        # Get all responses for this conversation
        responses = db_manager.get_conversation_responses(conversation_id)

        # Get form details
        form_id = conversation['form_id']
        form_info = db_manager.get_form_by_id(form_id)
        form_fields = db_manager.get_form_fields(form_id)

        # Build summary
        summary = {
            "status": "success",
            "conversation_id": conversation_id,
            "form_title": form_info.get('form_title', 'Untitled Form'),
            "form_url": form_info.get('form_url', ''),
            "language": conversation['language'],
            "started_at": conversation['started_at'],
            "completed_at": conversation.get('completed_at'),
            "total_fields": len(form_fields),
            "responses": []
        }

        # Map responses to fields
        for response in responses:
            # Find the field for this response
            field_id = None
            for field in form_fields:
                prompts = db_manager.get_prompts_for_field(field['id'], conversation['language'])
                if prompts and prompts[0]['id'] == response['prompt_id']:
                    field_id = field['id']
                    break

            if field_id:
                field = next((f for f in form_fields if f['id'] == field_id), None)
                if field:
                    summary["responses"].append({
                        "field_name": field['field_name'],
                        "field_label": field['field_label'],
                        "field_type": field['field_type'],
                        "question": response.get('prompt_text', ''),
                        "answer": response['response_text'],
                        "confidence_score": response.get('confidence_score', 0.0),
                        "timestamp": response.get('created_at', '')
                    })

        return summary
    except Exception as e:
        logger.error(f"Error getting conversation summary: {str(e)}")
        return {"status": "error", "error": f"Server error: {str(e)}"}

@mcp.tool()
async def autofill_form(url: str, form_schema: Dict[str, Any], responses: List[Dict[str, Any]],
                       language: str = "en") -> Dict[str, Any]:
    """
    Autofill a web form using Playwright based on schema and responses.

    Args:
        url: URL of the form to autofill.
        form_schema: Parsed form schema from parse_form.
        responses: List of field responses from LLMConversation.
        language: Language for translated field labels.

    Returns:
        dict: Autofill status, filled fields, errors, screenshots, and logs.
    """
    logger.info(f"Received autofill_form request: url={url}, language={language}")
    try:
        if not url:
            return {"status": "error", "error": "URL is empty", "filled_fields": [], "errors": [], "screenshots": [], "log_file": ""}

        await autofiller.initialize()
        translated_schema = multilingual.translate_form_fields(form_schema, language)
        result = await autofiller.autofill_form(url, translated_schema, responses)
        return result

    except Exception as e:
        logger.error(f"Error autofilling form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "filled_fields": [],
            "errors": [str(e)],
            "screenshots": [],
            "log_file": ""
        }
    finally:
        await autofiller.close()

if __name__ == "__main__":
    try:
        logger.info("Starting FastMCP server with stdio transport")
        mcp.run(transport="stdio")
        logger.info("FastMCP server started successfully")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
