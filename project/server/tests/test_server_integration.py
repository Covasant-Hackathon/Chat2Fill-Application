import asyncio
import json
import sys
import os
import logging
from typing import Dict, Any
from datetime import datetime

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the server components directly
from database_manager import DatabaseManager
from utils.session_manager import SessionManager
from utils.database_config import DatabaseConfig
from database.services import DatabaseContext
from database.integration import form_db_integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerIntegrationTester:
    """Test server integration with database and session management"""

    def __init__(self):
        self.test_results = []
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        self.db_config = DatabaseConfig()

    def log_test_result(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)

        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")

    def test_database_manager(self):
        """Test database manager initialization"""
        try:
            # Test database manager
            db_info = self.db_manager.get_database_info()

            self.log_test_result(
                "Database Manager",
                'error' not in db_info,
                f"Database manager initialized: {db_info.get('database_path', 'N/A')}"
            )

            return 'error' not in db_info
        except Exception as e:
            self.log_test_result("Database Manager", False, f"Exception: {str(e)}")
            return False

    def test_session_manager(self):
        """Test session manager functionality"""
        try:
            # Create a session
            session_info = self.session_manager.create_session(
                ip_address="127.0.0.1",
                user_agent="Test Agent",
                preferred_language="en"
            )

            session_id = session_info.get('session_id')

            self.log_test_result(
                "Session Creation",
                session_id is not None,
                f"Created session: {session_id}"
            )

            # Retrieve session
            retrieved_session = self.session_manager.get_session(session_id)

            self.log_test_result(
                "Session Retrieval",
                retrieved_session is not None,
                f"Retrieved session: {retrieved_session.get('session_id', 'N/A')}"
            )

            return session_id is not None and retrieved_session is not None

        except Exception as e:
            self.log_test_result("Session Manager", False, f"Exception: {str(e)}")
            return False

    def test_database_integration(self):
        """Test database integration layer"""
        try:
            # Test form storage
            form_schema = {
                "title": "Integration Test Form",
                "description": "Testing database integration",
                "fields": [
                    {
                        "name": "name",
                        "type": "text",
                        "label": "Full Name",
                        "required": True,
                        "order": 1
                    },
                    {
                        "name": "email",
                        "type": "email",
                        "label": "Email",
                        "required": True,
                        "order": 2
                    }
                ]
            }

            user_id, form_id = form_db_integration.store_parsed_form(
                session_id="integration-test-session",
                url="https://example.com/test",
                form_type="custom",
                form_schema=form_schema,
                language="en"
            )

            self.log_test_result(
                "Form Storage",
                user_id is not None and form_id is not None,
                f"Stored form: user_id={user_id}, form_id={form_id}"
            )

            # Test response storage
            response_id = form_db_integration.store_user_response(
                session_id="integration-test-session",
                form_id=form_id,
                field_name="name",
                response_text="John Doe",
                language="en"
            )

            self.log_test_result(
                "Response Storage",
                response_id is not None,
                f"Stored response: response_id={response_id}"
            )

            # Test session data retrieval
            session_data = form_db_integration.get_user_session_data("integration-test-session")

            self.log_test_result(
                "Session Data Retrieval",
                'error' not in session_data,
                f"Retrieved session data: {len(session_data.get('forms', []))} forms"
            )

            return True

        except Exception as e:
            self.log_test_result("Database Integration", False, f"Exception: {str(e)}")
            return False

    def test_multilingual_support(self):
        """Test multilingual functionality"""
        try:
            languages = ["en", "hi", "te"]
            results = []

            for lang in languages:
                # Create a form in different languages
                form_schema = {
                    "title": f"Test Form - {lang}",
                    "description": f"Test form in {lang}",
                    "fields": [
                        {
                            "name": "name",
                            "type": "text",
                            "label": "Name",
                            "required": True,
                            "order": 1
                        }
                    ]
                }

                user_id, form_id = form_db_integration.store_parsed_form(
                    session_id=f"multilingual-test-{lang}",
                    url=f"https://example.com/form-{lang}",
                    form_type="custom",
                    form_schema=form_schema,
                    language=lang
                )

                success = user_id is not None and form_id is not None
                results.append(success)

                self.log_test_result(
                    f"Multilingual Form ({lang})",
                    success,
                    f"Created form in {lang}: form_id={form_id}"
                )

            return all(results)

        except Exception as e:
            self.log_test_result("Multilingual Support", False, f"Exception: {str(e)}")
            return False

    def test_conversation_history(self):
        """Test conversation history functionality"""
        try:
            session_id = "conversation-test-session"

            # Add conversation messages
            messages = [
                {"type": "system", "content": "Welcome to the form assistant!", "language": "en"},
                {"type": "ai", "content": "What is your name?", "language": "en"},
                {"type": "human", "content": "John Doe", "language": "en"},
                {"type": "ai", "content": "Thank you! What is your email?", "language": "en"},
                {"type": "human", "content": "john@example.com", "language": "en"}
            ]

            success_count = 0
            for msg in messages:
                success = form_db_integration.add_conversation_message(
                    session_id=session_id,
                    message_type=msg["type"],
                    message_content=msg["content"],
                    language=msg["language"]
                )
                if success:
                    success_count += 1

            self.log_test_result(
                "Conversation Messages",
                success_count == len(messages),
                f"Added {success_count}/{len(messages)} conversation messages"
            )

            # Retrieve conversation history
            history = form_db_integration.get_conversation_history(session_id)

            self.log_test_result(
                "Conversation History",
                len(history) == len(messages),
                f"Retrieved {len(history)} conversation messages"
            )

            return success_count == len(messages) and len(history) == len(messages)

        except Exception as e:
            self.log_test_result("Conversation History", False, f"Exception: {str(e)}")
            return False

    def test_form_completion_tracking(self):
        """Test form completion tracking"""
        try:
            session_id = "completion-test-session"

            # Create a form
            form_schema = {
                "title": "Completion Test Form",
                "fields": [
                    {"name": "field1", "type": "text", "label": "Field 1", "required": True},
                    {"name": "field2", "type": "text", "label": "Field 2", "required": True},
                    {"name": "field3", "type": "text", "label": "Field 3", "required": True}
                ]
            }

            user_id, form_id = form_db_integration.store_parsed_form(
                session_id=session_id,
                url="https://example.com/completion-test",
                form_type="custom",
                form_schema=form_schema,
                language="en"
            )

            # Submit partial responses
            form_db_integration.store_user_response(
                session_id=session_id,
                form_id=form_id,
                field_name="field1",
                response_text="Response 1",
                language="en",
                is_final=True
            )

            form_db_integration.store_user_response(
                session_id=session_id,
                form_id=form_id,
                field_name="field2",
                response_text="Response 2",
                language="en",
                is_final=True
            )

            # Check completion status
            completion_status = form_db_integration.get_form_completion_status(session_id, form_id)

            expected_completion = 66.67  # 2 out of 3 fields completed
            actual_completion = completion_status.get('completion_percentage', 0)

            self.log_test_result(
                "Form Completion Tracking",
                abs(actual_completion - expected_completion) < 1,
                f"Completion: {actual_completion}% (expected ~{expected_completion}%)"
            )

            return abs(actual_completion - expected_completion) < 1

        except Exception as e:
            self.log_test_result("Form Completion Tracking", False, f"Exception: {str(e)}")
            return False

    def test_data_cleanup(self):
        """Test data cleanup functionality"""
        try:
            # Test session cleanup
            initial_stats = self.session_manager.get_session_statistics()

            # Cleanup expired sessions
            cleaned_count = self.session_manager.cleanup_expired_sessions()

            self.log_test_result(
                "Session Cleanup",
                cleaned_count >= 0,
                f"Cleaned {cleaned_count} expired sessions"
            )

            # Test database cleanup
            form_db_integration.cleanup_old_sessions(hours=0)  # Clean all for testing

            self.log_test_result(
                "Database Cleanup",
                True,
                "Database cleanup completed"
            )

            return True

        except Exception as e:
            self.log_test_result("Data Cleanup", False, f"Exception: {str(e)}")
            return False

    def test_error_handling(self):
        """Test error handling scenarios"""
        try:
            test_results = []

            # Test invalid session retrieval
            invalid_session = self.session_manager.get_session("invalid-session-id")
            test_results.append(invalid_session is None)

            # Test nonexistent form retrieval
            nonexistent_form = form_db_integration.get_form_with_prompts(99999)
            test_results.append('error' in nonexistent_form)

            # Test invalid user session data
            invalid_user_data = form_db_integration.get_user_session_data("nonexistent-session")
            test_results.append('error' in invalid_user_data)

            self.log_test_result(
                "Error Handling",
                all(test_results),
                f"Handled {sum(test_results)}/{len(test_results)} error scenarios correctly"
            )

            return all(test_results)

        except Exception as e:
            self.log_test_result("Error Handling", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*80)
        print("SERVER INTEGRATION TESTS")
        print("="*80)

        tests = [
            ("Database Manager", self.test_database_manager),
            ("Session Manager", self.test_session_manager),
            ("Database Integration", self.test_database_integration),
            ("Multilingual Support", self.test_multilingual_support),
            ("Conversation History", self.test_conversation_history),
            ("Form Completion Tracking", self.test_form_completion_tracking),
            ("Data Cleanup", self.test_data_cleanup),
            ("Error Handling", self.test_error_handling)
        ]

        for test_name, test_func in tests:
            print(f"\n--- Running {test_name} ---")
            try:
                test_func()
            except Exception as e:
                self.log_test_result(test_name, False, f"Test failed with exception: {str(e)}")

        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ✗ {result['test_name']}: {result['message']}")

        print("\nALL TESTS:")
        for result in self.test_results:
            status = "✓ PASS" if result["success"] else "✗ FAIL"
            print(f"  {status} - {result['test_name']}: {result['message']}")

        # Save results to file
        self.save_test_results()

        print("\n" + "="*80)
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Server integration is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the output above.")
        print("="*80)

    def save_test_results(self):
        """Save test results to file"""
        try:
            results_file = "server_integration_test_results.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            print(f"\nTest results saved to: {results_file}")
        except Exception as e:
            print(f"Failed to save test results: {str(e)}")

if __name__ == "__main__":
    try:
        print("Server Integration Testing Script")
        print("=" * 40)

        # Initialize tester
        tester = ServerIntegrationTester()

        # Run all tests
        tester.run_all_tests()

    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
    except Exception as e:
        print(f"Fatal error in server integration testing: {str(e)}")
        sys.exit(1)
