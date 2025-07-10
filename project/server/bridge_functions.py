#!/usr/bin/env python3
"""
Bridge functions - Direct implementations without MCP decorators for the bridge server
"""

import logging
import json
import os
import uuid
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the required components
from database_manager import DatabaseManager
from utils.database_config import DatabaseConfig
from utils.session_manager import SessionManager
from form_parser import FormParser
from llm_conversation import LLMConversation
from multilingual_support import MultilingualSupport
from form_autofiller import FormAutofiller
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize components
logger.info("Initializing bridge components...")

# Initialize database and session management
db_config = DatabaseConfig()
db_manager = DatabaseManager(db_config)
session_manager = SessionManager(db_manager)

# Initialize Gemini API
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY is required")

genai.configure(api_key=gemini_api_key)
logger.info("Gemini API configured")

# Initialize Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")
logger.info("Gemini model initialized")

# Initialize LLM conversation and multilingual support
llm_conv = LLMConversation(db_manager, model)
multilingual_support = MultilingualSupport(db_manager, model)
form_autofiller = FormAutofiller()

logger.info("Bridge components initialized successfully")

# Bridge function implementations

async def bridge_parse_form(url: str, form_type: str, language: str = "en",
                           session_id: str = None) -> Dict[str, Any]:
    """Parse a form from URL with database integration."""
    logger.info(f"Bridge: parse_form request: url={url}, form_type={form_type}, language={language}")

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
            return {
                "status": "error",
                "error": "Invalid URL length",
                "session_id": session_id
            }

        # Validate form type
        valid_types = ["google", "typeform", "microsoft", "custom"]
        if form_type not in valid_types:
            return {
                "status": "error",
                "error": f"Invalid form type. Must be one of: {valid_types}",
                "session_id": session_id
            }

        # Parse form
        parser = FormParser(use_profile=(form_type == 'microsoft'), debug_mode=True)
        form_schema = await parser.parse_form_from_url(url, form_type)

        if not form_schema:
            return {
                "status": "error",
                "error": "Failed to parse form",
                "session_id": session_id
            }

        # Store form in database
        user_id = session_data['user_id']
        form_id = db_manager.save_form(
            user_id=user_id,
            url=url,
            form_type=form_type,
            title=form_schema.get('title', 'Untitled Form'),
            description=form_schema.get('description', ''),
            original_schema=form_schema,
            language=language
        )

        # Store form fields
        fields = form_schema.get('fields', [])
        field_count = db_manager.save_form_fields(form_id, fields)

        # Generate questions for fields
        questions_generated = await llm_conv.generate_questions_for_form(form_id, language)

        logger.info(f"Form parsed successfully: {field_count} fields, {questions_generated} questions")

        return {
            "status": "success",
            "form_id": form_id,
            "session_id": session_id,
            "form_schema": form_schema,
            "fields_count": field_count,
            "questions_generated": questions_generated,
            "message": "Form parsed successfully"
        }

    except Exception as e:
        logger.error(f"Error parsing form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id
        }

async def bridge_parse_html_form(html_input: str, is_file: bool = False, language: str = "en",
                                session_id: str = None) -> Dict[str, Any]:
    """Parse HTML form with database integration."""
    logger.info(f"Bridge: parse_html_form request: is_file={is_file}, language={language}")

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
            return {
                "status": "error",
                "error": "HTML input is required",
                "session_id": session_id
            }

        # Parse HTML form
        parser = FormParser(debug_mode=True)
        form_schema = await parser.parse_html_content(html_input, is_file)

        if not form_schema:
            return {
                "status": "error",
                "error": "Failed to parse HTML form",
                "session_id": session_id
            }

        # Store form in database
        user_id = session_data['user_id']
        form_id = db_manager.save_form(
            user_id=user_id,
            url=None,
            form_type="custom",
            title=form_schema.get('title', 'HTML Form'),
            description=form_schema.get('description', ''),
            original_schema=form_schema,
            language=language
        )

        # Store form fields
        fields = form_schema.get('fields', [])
        field_count = db_manager.save_form_fields(form_id, fields)

        # Generate questions for fields
        questions_generated = await llm_conv.generate_questions_for_form(form_id, language)

        logger.info(f"HTML form parsed successfully: {field_count} fields, {questions_generated} questions")

        return {
            "status": "success",
            "form_id": form_id,
            "session_id": session_id,
            "form_schema": form_schema,
            "fields_count": field_count,
            "questions_generated": questions_generated,
            "message": "HTML form parsed successfully"
        }

    except Exception as e:
        logger.error(f"Error parsing HTML form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id
        }

async def bridge_start_conversation(session_id: str, form_id: int, language: str = "en") -> Dict[str, Any]:
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
                "message": "Conversation started successfully"
            }
        else:
            return {"status": "error", "error": "Failed to start conversation"}

    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return {"status": "error", "error": str(e)}

async def bridge_get_next_question(session_id: str, conversation_id: int, language: str = "en") -> Dict[str, Any]:
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
                "conversation_id": conversation_id,
                "progress": {
                    "current": len(form_fields),
                    "total": len(form_fields)
                }
            }

        # Get current field
        current_field = form_fields[current_index]

        # Get or generate question for current field
        question = await llm_conv.get_question_for_field(
            form_id=form_id,
            field_name=current_field['field_name'],
            language=language
        )

        if question:
            return {
                "status": "success",
                "question": question,
                "field_name": current_field['field_name'],
                "field_type": current_field['field_type'],
                "field_required": current_field.get('is_required', False),
                "field_options": current_field.get('field_options', []),
                "conversation_id": conversation_id,
                "progress": {
                    "current": current_index + 1,
                    "total": len(form_fields)
                }
            }
        else:
            return {"status": "error", "error": "Failed to get question"}

    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        return {"status": "error", "error": str(e)}

async def bridge_submit_user_response(session_id: str, conversation_id: int, field_name: str,
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
        user_id = session_data['user_id']

        # Process and validate the response
        processed_response = await llm_conv.process_user_response(
            response_text=response_text,
            field_name=field_name,
            form_id=form_id,
            language=language
        )

        if processed_response['is_valid']:
            # Store the response
            response_id = db_manager.store_user_response(
                user_id=user_id,
                form_id=form_id,
                field_name=field_name,
                response_text=processed_response['processed_text'],
                language=language,
                confidence_score=processed_response['confidence_score']
            )

            # Update conversation progress
            db_manager.update_conversation_progress(conversation_id)

            # Get next question
            next_question_result = await bridge_get_next_question(session_id, conversation_id, language)

            return {
                "status": "success",
                "response_id": response_id,
                "processed_response": processed_response['processed_text'],
                "confidence_score": processed_response['confidence_score'],
                "next_question": next_question_result,
                "message": "Response submitted successfully"
            }
        else:
            return {
                "status": "error",
                "error": processed_response['error_message'],
                "suggestions": processed_response.get('suggestions', [])
            }

    except Exception as e:
        logger.error(f"Error submitting user response: {str(e)}")
        return {"status": "error", "error": str(e)}

async def bridge_get_conversation_summary(session_id: str, conversation_id: int) -> Dict[str, Any]:
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

        form_id = conversation['form_id']
        user_id = session_data['user_id']

        # Get form information
        form_info = db_manager.get_form_info(form_id)
        if not form_info:
            return {"status": "error", "error": "Form not found"}

        # Get all user responses for this form
        user_responses = db_manager.get_user_responses(user_id, form_id)

        # Generate summary
        summary = {
            "conversation_id": conversation_id,
            "form_id": form_id,
            "form_title": form_info.get('title', 'Untitled Form'),
            "form_description": form_info.get('description', ''),
            "total_fields": len(form_info.get('fields', [])),
            "completed_fields": len(user_responses),
            "completion_percentage": (len(user_responses) / len(form_info.get('fields', []))) * 100 if form_info.get('fields') else 0,
            "responses": user_responses,
            "conversation_status": conversation.get('status', 'active'),
            "created_at": conversation.get('created_at'),
            "updated_at": conversation.get('updated_at')
        }

        return {
            "status": "success",
            "summary": summary,
            "message": "Conversation summary retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting conversation summary: {str(e)}")
        return {"status": "error", "error": str(e)}

async def bridge_autofill_form(url: str, form_schema: Dict[str, Any], responses: List[Dict[str, Any]],
                              language: str = "en") -> Dict[str, Any]:
    """Autofill a web form using Playwright based on schema and responses."""
    try:
        logger.info(f"Bridge: Autofilling form at {url}")

        # Use the form autofiller
        result = await form_autofiller.autofill_form(
            url=url,
            form_schema=form_schema,
            responses=responses,
            language=language
        )

        return result

    except Exception as e:
        logger.error(f"Error autofilling form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to autofill form"
        }
