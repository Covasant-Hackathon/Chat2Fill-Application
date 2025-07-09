import os
import sys
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any

# Add the server directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager
from utils.database_config import DatabaseConfig
from utils.session_manager import SessionManager
from multilingual_support import MultilingualSupport
from llm_conversation import LLMConversation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseTester:
    """Test suite for database functionality."""

    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = SessionManager(self.db_manager)
        self.multilingual = MultilingualSupport(self.db_manager)
        self.llm_conv = LLMConversation(self.db_manager)

    def test_database_initialization(self):
        """Test database initialization."""
        logger.info("Testing database initialization...")

        # Check if database file exists
        db_path = self.config.get_database_path()
        if os.path.exists(db_path):
            logger.info(f"✓ Database file exists at: {db_path}")
        else:
            logger.error(f"✗ Database file not found at: {db_path}")
            return False

        # Get database info
        db_info = self.db_manager.get_database_info()
        logger.info(f"✓ Database info: {db_info}")

        return True

    def test_session_management(self):
        """Test session management functionality."""
        logger.info("Testing session management...")

        try:
            # Create a new session
            session_info = self.session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Test Agent",
                preferred_language="en"
            )

            session_id = session_info['session_id']
            logger.info(f"✓ Created session: {session_id}")

            # Get session data
            session_data = self.session_manager.get_session(session_id)
            if session_data:
                logger.info(f"✓ Retrieved session data: {session_data['user_id']}")
            else:
                logger.error("✗ Failed to retrieve session data")
                return False

            # Update session
            update_success = self.session_manager.update_session(
                session_id,
                {'preferred_language': 'hi'}
            )
            if update_success:
                logger.info("✓ Updated session successfully")
            else:
                logger.error("✗ Failed to update session")
                return False

            # Validate session
            is_valid = self.session_manager.validate_session(session_id)
            if is_valid:
                logger.info("✓ Session validation successful")
            else:
                logger.error("✗ Session validation failed")
                return False

            return True

        except Exception as e:
            logger.error(f"✗ Session management test failed: {str(e)}")
            return False

    def test_form_management(self):
        """Test form management functionality."""
        logger.info("Testing form management...")

        try:
            # Create a test session first
            session_info = self.session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Test Agent",
                preferred_language="en"
            )
            user_id = session_info['user_id']

            # Sample form schema
            form_schema = {
                "title": "Test Form",
                "description": "A test form for database testing",
                "forms": [{
                    "fields": [
                        {
                            "id": "1",
                            "name": "full_name",
                            "type": "text",
                            "label": "Full Name",
                            "required": True,
                            "placeholder": "Enter your full name"
                        },
                        {
                            "id": "2",
                            "name": "email",
                            "type": "email",
                            "label": "Email Address",
                            "required": True,
                            "placeholder": "Enter your email"
                        },
                        {
                            "id": "3",
                            "name": "country",
                            "type": "dropdown",
                            "label": "Country",
                            "required": True,
                            "options": [
                                {"text": "USA", "value": "usa"},
                                {"text": "Canada", "value": "canada"},
                                {"text": "UK", "value": "uk"}
                            ]
                        }
                    ]
                }]
            }

            # Save form to database
            form_id = self.db_manager.save_form(
                user_id=user_id,
                form_url="https://example.com/test-form",
                form_type="test",
                form_schema=form_schema,
                form_title="Test Form",
                form_description="A test form for database testing"
            )

            if form_id:
                logger.info(f"✓ Saved form with ID: {form_id}")
            else:
                logger.error("✗ Failed to save form")
                return False

            # Save form fields
            fields = form_schema['forms'][0]['fields']
            field_ids = self.db_manager.save_form_fields(form_id, fields)

            if field_ids:
                logger.info(f"✓ Saved {len(field_ids)} form fields")
            else:
                logger.error("✗ Failed to save form fields")
                return False

            # Retrieve form
            retrieved_form = self.db_manager.get_form(form_id)
            if retrieved_form:
                logger.info(f"✓ Retrieved form: {retrieved_form['form_title']}")
            else:
                logger.error("✗ Failed to retrieve form")
                return False

            # Get form fields
            form_fields = self.db_manager.get_form_fields(form_id)
            if form_fields:
                logger.info(f"✓ Retrieved {len(form_fields)} form fields")
            else:
                logger.error("✗ Failed to retrieve form fields")
                return False

            return True

        except Exception as e:
            logger.error(f"✗ Form management test failed: {str(e)}")
            return False

    def test_multilingual_support(self):
        """Test multilingual support functionality."""
        logger.info("Testing multilingual support...")

        try:
            # Test basic translation
            hindi_text = self.multilingual.translate("Full Name", "en", "hi")
            if hindi_text and hindi_text != "Full Name":
                logger.info(f"✓ Translation successful: 'Full Name' -> '{hindi_text}'")
            else:
                logger.warning("⚠ Translation may not be working properly")

            # Test form field translation
            form_schema = {
                "forms": [{
                    "fields": [
                        {
                            "id": "1",
                            "label": "Full Name",
                            "type": "text",
                            "placeholder": "Enter your name"
                        },
                        {
                            "id": "2",
                            "label": "Email",
                            "type": "email",
                            "options": [
                                {"text": "Personal"},
                                {"text": "Work"}
                            ]
                        }
                    ]
                }]
            }

            translated_schema = self.multilingual.translate_form_fields(form_schema, "hi")
            if translated_schema:
                logger.info("✓ Form field translation successful")

                # Check if translated fields exist
                first_field = translated_schema['forms'][0]['fields'][0]
                if 'translated_label' in first_field:
                    logger.info(f"✓ Translated label: {first_field['translated_label']}")
                else:
                    logger.warning("⚠ Translated label not found")
            else:
                logger.error("✗ Form field translation failed")
                return False

            return True

        except Exception as e:
            logger.error(f"✗ Multilingual support test failed: {str(e)}")
            return False

    def test_conversation_flow(self):
        """Test complete conversation flow."""
        logger.info("Testing conversation flow...")

        try:
            # Create session and form
            session_info = self.session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Test Agent",
                preferred_language="en"
            )
            user_id = session_info['user_id']

            # Sample form schema
            form_schema = {
                "title": "Registration Form",
                "forms": [{
                    "fields": [
                        {
                            "id": "1",
                            "name": "full_name",
                            "type": "text",
                            "label": "Full Name",
                            "required": True
                        },
                        {
                            "id": "2",
                            "name": "age",
                            "type": "number",
                            "label": "Age",
                            "required": True
                        }
                    ]
                }]
            }

            # Save form
            form_id = self.db_manager.save_form(
                user_id=user_id,
                form_url="https://example.com/registration",
                form_type="registration",
                form_schema=form_schema
            )

            # Save form fields
            fields = form_schema['forms'][0]['fields']
            field_ids = self.db_manager.save_form_fields(form_id, fields)

            # Generate questions
            questions = self.llm_conv.generate_questions(
                form_schema,
                context="Registration form test",
                language="en",
                form_id=form_id
            )

            if questions:
                logger.info(f"✓ Generated {len(questions)} questions")
            else:
                logger.error("✗ Failed to generate questions")
                return False

            # Create conversation
            conversation_id = self.llm_conv.start_conversation(user_id, form_id, "en")
            if conversation_id:
                logger.info(f"✓ Started conversation: {conversation_id}")
            else:
                logger.error("✗ Failed to start conversation")
                return False

            # Test response parsing (without actual prompts for simplicity)
            test_field = fields[0]  # Full name field
            response_data = self.llm_conv.parse_response(
                "John Doe",
                test_field,
                "en"
            )

            if response_data and response_data['valid']:
                logger.info("✓ Response parsing successful")
            else:
                logger.error("✗ Response parsing failed")
                return False

            return True

        except Exception as e:
            logger.error(f"✗ Conversation flow test failed: {str(e)}")
            return False

    def test_database_backup(self):
        """Test database backup functionality."""
        logger.info("Testing database backup...")

        try:
            backup_path = self.db_manager.backup_database()
            if backup_path and os.path.exists(backup_path):
                logger.info(f"✓ Database backup created: {backup_path}")
                return True
            else:
                logger.error("✗ Database backup failed")
                return False

        except Exception as e:
            logger.error(f"✗ Database backup test failed: {str(e)}")
            return False

    def test_cleanup_operations(self):
        """Test cleanup operations."""
        logger.info("Testing cleanup operations...")

        try:
            # Test session cleanup
            cleaned_count = self.session_manager.cleanup_expired_sessions()
            logger.info(f"✓ Cleaned up {cleaned_count} expired sessions")

            # Test database cleanup
            db_cleaned_count = self.db_manager.cleanup_old_sessions(days_old=30)
            logger.info(f"✓ Cleaned up {db_cleaned_count} old database sessions")

            return True

        except Exception as e:
            logger.error(f"✗ Cleanup operations test failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests."""
        logger.info("="*50)
        logger.info("STARTING DATABASE TESTS")
        logger.info("="*50)

        tests = [
            ("Database Initialization", self.test_database_initialization),
            ("Session Management", self.test_session_management),
            ("Form Management", self.test_form_management),
            ("Multilingual Support", self.test_multilingual_support),
            ("Conversation Flow", self.test_conversation_flow),
            ("Database Backup", self.test_database_backup),
            ("Cleanup Operations", self.test_cleanup_operations)
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} Test ---")
            try:
                if test_func():
                    passed += 1
                    logger.info(f"✓ {test_name} test PASSED")
                else:
                    failed += 1
                    logger.error(f"✗ {test_name} test FAILED")
            except Exception as e:
                failed += 1
                logger.error(f"✗ {test_name} test FAILED with exception: {str(e)}")

        logger.info("\n" + "="*50)
        logger.info("TEST RESULTS")
        logger.info("="*50)
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total: {passed + failed}")

        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED!")
            return True
        else:
            logger.error(f"❌ {failed} TESTS FAILED!")
            return False

def main():
    """Main function to run database tests."""
    try:
        tester = DatabaseTester()
        success = tester.run_all_tests()

        if success:
            logger.info("\n✅ Database system is working correctly!")
        else:
            logger.error("\n❌ Database system has issues that need to be addressed.")

        return success

    except Exception as e:
        logger.error(f"Failed to run tests: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
