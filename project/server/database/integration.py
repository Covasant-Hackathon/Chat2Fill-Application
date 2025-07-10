import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from .models import User, Form, FormField, Prompt, MultilingualContent, UserResponse, ConversationHistory
from .services import DatabaseService, DatabaseContext
from .config import db_config
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FormParserDatabaseIntegration:
    """Integration layer between form parsing and database operations"""

    def __init__(self):
        self.db_config = db_config

    def store_parsed_form(self, session_id: str, url: str, form_type: str,
                         form_schema: Dict[str, Any], language: str = "en",
                         title: str = None, description: str = None) -> Tuple[int, int]:
        """
        Store parsed form data in database

        Returns:
            Tuple[int, int]: (user_id, form_id)
        """
        try:
            with DatabaseContext() as db_service:
                # Get or create user
                user = db_service.get_or_create_user(session_id, language)

                # Create form record
                form = db_service.create_form(
                    user_id=user.id,
                    url=url,
                    form_type=form_type,
                    title=title,
                    description=description,
                    original_schema=form_schema
                )

                # Store form fields
                field_ids = []
                for field_data in form_schema.get('fields', []):
                    field = db_service.create_form_field(
                        form_id=form.id,
                        field_name=field_data.get('name', ''),
                        field_type=field_data.get('type', 'text'),
                        field_label=field_data.get('label', ''),
                        field_placeholder=field_data.get('placeholder', ''),
                        is_required=field_data.get('required', False),
                        field_options=field_data.get('options', []),
                        field_order=field_data.get('order', 0),
                        field_metadata=field_data.get('metadata', {})
                    )
                    field_ids.append(field.id)

                # Log successful storage
                db_service.log_system_event(
                    log_level="INFO",
                    log_message=f"Form parsed and stored successfully",
                    user_id=user.id,
                    log_data={
                        "form_id": form.id,
                        "form_type": form_type,
                        "fields_count": len(field_ids),
                        "url": url
                    }
                )

                logger.info(f"Stored form {form.id} with {len(field_ids)} fields for user {user.id}")
                return user.id, form.id

        except Exception as e:
            logger.error(f"Error storing parsed form: {str(e)}")
            raise

    def store_generated_prompts(self, form_id: int, prompts: List[Dict[str, Any]],
                              language: str = "en") -> List[int]:
        """
        Store generated prompts for form fields

        Returns:
            List[int]: List of prompt IDs
        """
        try:
            with DatabaseContext() as db_service:
                prompt_ids = []

                for prompt_data in prompts:
                    # Find the corresponding field
                    field_name = prompt_data.get('field_name', '')
                    field = None

                    form_fields = db_service.get_form_fields(form_id)
                    for f in form_fields:
                        if f.field_name == field_name:
                            field = f
                            break

                    if not field:
                        logger.warning(f"Field not found for prompt: {field_name}")
                        continue

                    # Create prompt
                    prompt = db_service.create_prompt(
                        field_id=field.id,
                        original_prompt=prompt_data.get('prompt', ''),
                        context=prompt_data.get('context', ''),
                        prompt_type=prompt_data.get('type', 'question')
                    )
                    prompt_ids.append(prompt.id)

                    # Store multilingual content for the prompt
                    if language != "en":
                        db_service.create_multilingual_content(
                            language_code=language,
                            content_type="prompt",
                            original_text=prompt_data.get('prompt', ''),
                            translated_text=prompt_data.get('translated_prompt', prompt_data.get('prompt', '')),
                            prompt_id=prompt.id
                        )

                logger.info(f"Stored {len(prompt_ids)} prompts for form {form_id}")
                return prompt_ids

        except Exception as e:
            logger.error(f"Error storing generated prompts: {str(e)}")
            raise

    def store_multilingual_translations(self, form_id: int, translated_schema: Dict[str, Any],
                                      language: str) -> bool:
        """
        Store multilingual translations for form fields

        Returns:
            bool: Success status
        """
        try:
            with DatabaseContext() as db_service:
                form_fields = db_service.get_form_fields(form_id)

                for field in form_fields:
                    # Find corresponding translated field
                    translated_field = None
                    for trans_field in translated_schema.get('fields', []):
                        if trans_field.get('name') == field.field_name:
                            translated_field = trans_field
                            break

                    if not translated_field:
                        continue

                    # Store label translation
                    if translated_field.get('label'):
                        db_service.create_multilingual_content(
                            language_code=language,
                            content_type="label",
                            original_text=field.field_label or '',
                            translated_text=translated_field.get('label', ''),
                            field_id=field.id
                        )

                    # Store placeholder translation
                    if translated_field.get('placeholder'):
                        db_service.create_multilingual_content(
                            language_code=language,
                            content_type="placeholder",
                            original_text=field.field_placeholder or '',
                            translated_text=translated_field.get('placeholder', ''),
                            field_id=field.id
                        )

                    # Store option translations
                    if translated_field.get('options'):
                        for i, option in enumerate(translated_field.get('options', [])):
                            original_option = field.field_options[i] if field.field_options and i < len(field.field_options) else ''
                            db_service.create_multilingual_content(
                                language_code=language,
                                content_type="option",
                                original_text=str(original_option),
                                translated_text=str(option),
                                field_id=field.id
                            )

                logger.info(f"Stored multilingual translations for form {form_id} in language {language}")
                return True

        except Exception as e:
            logger.error(f"Error storing multilingual translations: {str(e)}")
            return False

    def store_user_response(self, session_id: str, form_id: int, field_name: str,
                          response_text: str, language: str = "en",
                          confidence_score: int = 0, is_final: bool = False) -> Optional[int]:
        """
        Store user response to a form field

        Returns:
            Optional[int]: Response ID if successful
        """
        try:
            with DatabaseContext() as db_service:
                # Get user by session
                user = db_service.get_user_by_session(session_id)
                if not user:
                    logger.error(f"User not found for session: {session_id}")
                    return None

                # Find field by name
                form_fields = db_service.get_form_fields(form_id)
                field = None
                for f in form_fields:
                    if f.field_name == field_name:
                        field = f
                        break

                if not field:
                    logger.error(f"Field not found: {field_name}")
                    return None

                # Create response
                response = db_service.create_user_response(
                    user_id=user.id,
                    form_id=form_id,
                    field_id=field.id,
                    response_text=response_text,
                    language_code=language,
                    confidence_score=confidence_score,
                    is_final=is_final
                )

                # Update user activity
                db_service.update_user_activity(user.id)

                logger.info(f"Stored user response for field {field_name}")
                return response.id

        except Exception as e:
            logger.error(f"Error storing user response: {str(e)}")
            return None

    def get_user_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user session data

        Returns:
            Dict containing user data, forms, and responses
        """
        try:
            with DatabaseContext() as db_service:
                user = db_service.get_user_by_session(session_id)
                if not user:
                    return {"error": "User session not found"}

                # Get user forms
                forms = db_service.get_user_forms(user.id)

                # Get user responses
                responses = db_service.get_user_responses(user.id)

                # Get conversation history
                conversations = db_service.get_conversation_history(user.id)

                return {
                    "user": {
                        "id": user.id,
                        "session_id": user.session_id,
                        "preferred_language": user.preferred_language,
                        "created_at": user.created_at.isoformat(),
                        "last_active": user.last_active.isoformat(),
                        "is_active": user.is_active
                    },
                    "forms": [
                        {
                            "id": form.id,
                            "url": form.url,
                            "form_type": form.form_type,
                            "title": form.title,
                            "description": form.description,
                            "parsed_at": form.parsed_at.isoformat(),
                            "is_active": form.is_active
                        }
                        for form in forms
                    ],
                    "responses": [
                        {
                            "id": response.id,
                            "form_id": response.form_id,
                            "field_id": response.field_id,
                            "response_text": response.response_text,
                            "language_code": response.language_code,
                            "confidence_score": response.confidence_score,
                            "is_final": response.is_final,
                            "responded_at": response.responded_at.isoformat()
                        }
                        for response in responses
                    ],
                    "conversation_count": len(conversations)
                }

        except Exception as e:
            logger.error(f"Error getting user session data: {str(e)}")
            return {"error": str(e)}

    def get_form_with_prompts(self, form_id: int, language: str = "en") -> Dict[str, Any]:
        """
        Get form with fields and prompts in specified language

        Returns:
            Dict containing form data with translated prompts
        """
        try:
            with DatabaseContext() as db_service:
                form = db_service.get_form_by_id(form_id)
                if not form:
                    return {"error": "Form not found"}

                fields = db_service.get_form_fields(form_id)

                form_data = {
                    "id": form.id,
                    "url": form.url,
                    "form_type": form.form_type,
                    "title": form.title,
                    "description": form.description,
                    "parsed_at": form.parsed_at.isoformat(),
                    "fields": []
                }

                for field in fields:
                    field_data = {
                        "id": field.id,
                        "name": field.field_name,
                        "type": field.field_type,
                        "label": field.field_label,
                        "placeholder": field.field_placeholder,
                        "required": field.is_required,
                        "options": field.field_options,
                        "order": field.field_order,
                        "prompts": []
                    }

                    # Get translations if language is not English
                    if language != "en":
                        translations = db_service.get_field_translations(field.id, language)
                        for trans in translations:
                            if trans.content_type == "label":
                                field_data["translated_label"] = trans.translated_text
                            elif trans.content_type == "placeholder":
                                field_data["translated_placeholder"] = trans.translated_text

                    # Get prompts for this field
                    prompts = db_service.get_field_prompts(field.id)
                    for prompt in prompts:
                        prompt_data = {
                            "id": prompt.id,
                            "original_prompt": prompt.original_prompt,
                            "context": prompt.context,
                            "type": prompt.prompt_type,
                            "generated_at": prompt.generated_at.isoformat()
                        }

                        # Get prompt translations
                        if language != "en":
                            prompt_translations = db_service.get_prompt_translations(prompt.id, language)
                            for trans in prompt_translations:
                                if trans.content_type == "prompt":
                                    prompt_data["translated_prompt"] = trans.translated_text

                        field_data["prompts"].append(prompt_data)

                    form_data["fields"].append(field_data)

                return form_data

        except Exception as e:
            logger.error(f"Error getting form with prompts: {str(e)}")
            return {"error": str(e)}

    def add_conversation_message(self, session_id: str, message_type: str,
                               message_content: str, language: str = "en",
                               context_data: Dict = None) -> bool:
        """
        Add a conversation message to history

        Returns:
            bool: Success status
        """
        try:
            with DatabaseContext() as db_service:
                user = db_service.get_user_by_session(session_id)
                if not user:
                    logger.error(f"User not found for session: {session_id}")
                    return False

                db_service.add_conversation_message(
                    user_id=user.id,
                    message_type=message_type,
                    message_content=message_content,
                    language_code=language,
                    context_data=context_data
                )

                return True

        except Exception as e:
            logger.error(f"Error adding conversation message: {str(e)}")
            return False

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user session

        Returns:
            List of conversation messages
        """
        try:
            with DatabaseContext() as db_service:
                user = db_service.get_user_by_session(session_id)
                if not user:
                    return []

                conversations = db_service.get_conversation_history(user.id, limit)

                return [
                    {
                        "id": conv.id,
                        "message_type": conv.message_type,
                        "message_content": conv.message_content,
                        "language_code": conv.language_code,
                        "context_data": conv.context_data,
                        "timestamp": conv.timestamp.isoformat()
                    }
                    for conv in conversations
                ]

        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

    def get_form_completion_status(self, session_id: str, form_id: int) -> Dict[str, Any]:
        """
        Get form completion status for a user

        Returns:
            Dict containing completion statistics
        """
        try:
            with DatabaseContext() as db_service:
                user = db_service.get_user_by_session(session_id)
                if not user:
                    return {"error": "User session not found"}

                return db_service.get_form_completion_status(user.id, form_id)

        except Exception as e:
            logger.error(f"Error getting form completion status: {str(e)}")
            return {"error": str(e)}

    def cleanup_old_sessions(self, hours: int = 24):
        """
        Cleanup old user sessions and related data

        Args:
            hours: Number of hours after which to consider sessions inactive
        """
        try:
            with DatabaseContext() as db_service:
                db_service.deactivate_inactive_users(hours)
                db_service.cleanup_old_data(days=30)  # Clean up data older than 30 days

                logger.info(f"Cleaned up inactive sessions older than {hours} hours")

        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {str(e)}")

# Global integration instance
form_db_integration = FormParserDatabaseIntegration()
