import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError
from .models import (
    User, Form, FormField, Prompt, MultilingualContent,
    UserResponse, ConversationHistory, SystemLog, get_db
)
import json
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service layer for database operations"""

    def __init__(self, db: Session):
        self.db = db

    # User Management
    def create_user(self, session_id: str = None, preferred_language: str = "en") -> User:
        """Create a new user session"""
        try:
            if not session_id:
                session_id = str(uuid.uuid4())

            user = User(
                session_id=session_id,
                preferred_language=preferred_language,
                created_at=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc)
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Created new user with session_id: {session_id}")
            return user

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise ValueError(f"User with session_id {session_id} already exists")

    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """Get user by session ID"""
        return self.db.query(User).filter(User.session_id == session_id).first()

    def update_user_activity(self, user_id: int) -> bool:
        """Update user's last active timestamp"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_active = datetime.now(timezone.utc)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user activity: {str(e)}")
            return False

    def get_or_create_user(self, session_id: str, preferred_language: str = "en") -> User:
        """Get existing user or create new one"""
        user = self.get_user_by_session(session_id)
        if not user:
            user = self.create_user(session_id, preferred_language)
        else:
            self.update_user_activity(user.id)
        return user

    def deactivate_inactive_users(self, hours: int = 24):
        """Deactivate users inactive for specified hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            self.db.query(User).filter(
                User.last_active < cutoff_time
            ).update({"is_active": False})
            self.db.commit()
            logger.info(f"Deactivated users inactive for {hours} hours")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating users: {str(e)}")

    # Form Management
    def create_form(self, user_id: int, url: str, form_type: str,
                   title: str = None, description: str = None,
                   original_schema: Dict = None) -> Form:
        """Create a new form record"""
        try:
            form = Form(
                user_id=user_id,
                url=url,
                form_type=form_type,
                title=title,
                description=description,
                original_schema=original_schema or {},
                parsed_at=datetime.now(timezone.utc)
            )
            self.db.add(form)
            self.db.commit()
            self.db.refresh(form)

            logger.info(f"Created new form for user {user_id}: {form.id}")
            return form

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating form: {str(e)}")
            raise

    def get_form_by_id(self, form_id: int) -> Optional[Form]:
        """Get form by ID"""
        return self.db.query(Form).filter(Form.id == form_id).first()

    def get_user_forms(self, user_id: int, limit: int = 10) -> List[Form]:
        """Get forms for a user"""
        return self.db.query(Form).filter(
            Form.user_id == user_id,
            Form.is_active == True
        ).order_by(desc(Form.parsed_at)).limit(limit).all()

    def update_form_schema(self, form_id: int, schema: Dict) -> bool:
        """Update form schema"""
        try:
            form = self.get_form_by_id(form_id)
            if form:
                form.original_schema = schema
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating form schema: {str(e)}")
            return False

    # Form Field Management
    def create_form_field(self, form_id: int, field_name: str, field_type: str,
                         field_label: str = None, field_placeholder: str = None,
                         is_required: bool = False, field_options: List = None,
                         field_order: int = 0, field_metadata: Dict = None) -> FormField:
        """Create a new form field"""
        try:
            field = FormField(
                form_id=form_id,
                field_name=field_name,
                field_type=field_type,
                field_label=field_label,
                field_placeholder=field_placeholder,
                is_required=is_required,
                field_options=field_options,
                field_order=field_order,
                field_metadata=field_metadata or {}
            )
            self.db.add(field)
            self.db.commit()
            self.db.refresh(field)

            logger.info(f"Created form field: {field_name} for form {form_id}")
            return field

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating form field: {str(e)}")
            raise

    def get_form_fields(self, form_id: int) -> List[FormField]:
        """Get all fields for a form"""
        return self.db.query(FormField).filter(
            FormField.form_id == form_id
        ).order_by(asc(FormField.field_order)).all()

    def get_field_by_id(self, field_id: int) -> Optional[FormField]:
        """Get form field by ID"""
        return self.db.query(FormField).filter(FormField.id == field_id).first()

    # Prompt Management
    def create_prompt(self, field_id: int, original_prompt: str,
                     context: str = None, prompt_type: str = "question") -> Prompt:
        """Create a new prompt for a field"""
        try:
            prompt = Prompt(
                field_id=field_id,
                original_prompt=original_prompt,
                context=context,
                prompt_type=prompt_type,
                generated_at=datetime.now(timezone.utc)
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)

            logger.info(f"Created prompt for field {field_id}")
            return prompt

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating prompt: {str(e)}")
            raise

    def get_field_prompts(self, field_id: int) -> List[Prompt]:
        """Get all prompts for a field"""
        return self.db.query(Prompt).filter(
            Prompt.field_id == field_id,
            Prompt.is_active == True
        ).order_by(desc(Prompt.generated_at)).all()

    def get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID"""
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()

    # Multilingual Content Management
    def create_multilingual_content(self, language_code: str, content_type: str,
                                  original_text: str, translated_text: str,
                                  field_id: int = None, prompt_id: int = None,
                                  translation_source: str = "llm") -> MultilingualContent:
        """Create multilingual content"""
        try:
            content = MultilingualContent(
                field_id=field_id,
                prompt_id=prompt_id,
                language_code=language_code,
                content_type=content_type,
                original_text=original_text,
                translated_text=translated_text,
                translation_source=translation_source,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(content)
            self.db.commit()
            self.db.refresh(content)

            logger.info(f"Created multilingual content: {content_type} in {language_code}")
            return content

        except IntegrityError as e:
            self.db.rollback()
            # Check if translation already exists
            existing = self.get_multilingual_content(
                language_code, content_type, field_id, prompt_id
            )
            if existing:
                # Update existing translation
                existing.translated_text = translated_text
                existing.translation_source = translation_source
                self.db.commit()
                return existing
            else:
                logger.error(f"Error creating multilingual content: {str(e)}")
                raise

    def get_multilingual_content(self, language_code: str, content_type: str,
                               field_id: int = None, prompt_id: int = None) -> Optional[MultilingualContent]:
        """Get multilingual content"""
        query = self.db.query(MultilingualContent).filter(
            MultilingualContent.language_code == language_code,
            MultilingualContent.content_type == content_type
        )

        if field_id:
            query = query.filter(MultilingualContent.field_id == field_id)
        if prompt_id:
            query = query.filter(MultilingualContent.prompt_id == prompt_id)

        return query.first()

    def get_field_translations(self, field_id: int, language_code: str) -> List[MultilingualContent]:
        """Get all translations for a field in a specific language"""
        return self.db.query(MultilingualContent).filter(
            MultilingualContent.field_id == field_id,
            MultilingualContent.language_code == language_code
        ).all()

    def get_prompt_translations(self, prompt_id: int, language_code: str) -> List[MultilingualContent]:
        """Get all translations for a prompt in a specific language"""
        return self.db.query(MultilingualContent).filter(
            MultilingualContent.prompt_id == prompt_id,
            MultilingualContent.language_code == language_code
        ).all()

    # User Response Management
    def create_user_response(self, user_id: int, form_id: int, field_id: int,
                           response_text: str = None, response_data: Dict = None,
                           language_code: str = "en", confidence_score: int = 0,
                           is_final: bool = False) -> UserResponse:
        """Create a user response"""
        try:
            response = UserResponse(
                user_id=user_id,
                form_id=form_id,
                field_id=field_id,
                response_text=response_text,
                response_data=response_data,
                language_code=language_code,
                confidence_score=confidence_score,
                is_final=is_final,
                responded_at=datetime.now(timezone.utc)
            )
            self.db.add(response)
            self.db.commit()
            self.db.refresh(response)

            logger.info(f"Created user response for field {field_id}")
            return response

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user response: {str(e)}")
            raise

    def get_user_responses(self, user_id: int, form_id: int = None) -> List[UserResponse]:
        """Get user responses"""
        query = self.db.query(UserResponse).filter(UserResponse.user_id == user_id)
        if form_id:
            query = query.filter(UserResponse.form_id == form_id)
        return query.order_by(desc(UserResponse.responded_at)).all()

    def get_field_response(self, user_id: int, field_id: int) -> Optional[UserResponse]:
        """Get user's response for a specific field"""
        return self.db.query(UserResponse).filter(
            UserResponse.user_id == user_id,
            UserResponse.field_id == field_id
        ).order_by(desc(UserResponse.responded_at)).first()

    def update_response_final(self, response_id: int, is_final: bool = True) -> bool:
        """Mark response as final"""
        try:
            response = self.db.query(UserResponse).filter(UserResponse.id == response_id).first()
            if response:
                response.is_final = is_final
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating response final status: {str(e)}")
            return False

    # Conversation History Management
    def add_conversation_message(self, user_id: int, message_type: str,
                               message_content: str, language_code: str = "en",
                               context_data: Dict = None) -> ConversationHistory:
        """Add a conversation message"""
        try:
            conversation = ConversationHistory(
                user_id=user_id,
                message_type=message_type,
                message_content=message_content,
                language_code=language_code,
                context_data=context_data,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"Added conversation message: {message_type} for user {user_id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding conversation message: {str(e)}")
            raise

    def get_conversation_history(self, user_id: int, limit: int = 50) -> List[ConversationHistory]:
        """Get conversation history for a user"""
        return self.db.query(ConversationHistory).filter(
            ConversationHistory.user_id == user_id
        ).order_by(desc(ConversationHistory.timestamp)).limit(limit).all()

    def clear_conversation_history(self, user_id: int) -> bool:
        """Clear conversation history for a user"""
        try:
            self.db.query(ConversationHistory).filter(
                ConversationHistory.user_id == user_id
            ).delete()
            self.db.commit()
            logger.info(f"Cleared conversation history for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error clearing conversation history: {str(e)}")
            return False

    # System Logging
    def log_system_event(self, log_level: str, log_message: str,
                        user_id: int = None, log_data: Dict = None):
        """Log system events"""
        try:
            log_entry = SystemLog(
                user_id=user_id,
                log_level=log_level,
                log_message=log_message,
                log_data=log_data,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging system event: {str(e)}")

    # Utility Methods
    def get_form_completion_status(self, user_id: int, form_id: int) -> Dict[str, Any]:
        """Get form completion status"""
        try:
            form = self.get_form_by_id(form_id)
            if not form:
                return {"error": "Form not found"}

            fields = self.get_form_fields(form_id)
            responses = self.get_user_responses(user_id, form_id)

            total_fields = len(fields)
            completed_fields = len([r for r in responses if r.is_final])

            return {
                "total_fields": total_fields,
                "completed_fields": completed_fields,
                "completion_percentage": (completed_fields / total_fields * 100) if total_fields > 0 else 0,
                "remaining_fields": total_fields - completed_fields,
                "is_complete": completed_fields == total_fields
            }
        except Exception as e:
            logger.error(f"Error getting form completion status: {str(e)}")
            return {"error": str(e)}

    def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Delete old conversation history
            self.db.query(ConversationHistory).filter(
                ConversationHistory.timestamp < cutoff_date
            ).delete()

            # Delete old system logs
            self.db.query(SystemLog).filter(
                SystemLog.created_at < cutoff_date
            ).delete()

            self.db.commit()
            logger.info(f"Cleaned up data older than {days} days")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old data: {str(e)}")

# Context manager for database operations
class DatabaseContext:
    """Context manager for database operations"""

    def __init__(self):
        self.db = None
        self.service = None

    def __enter__(self) -> DatabaseService:
        self.db = next(get_db())
        self.service = DatabaseService(self.db)
        return self.service

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
