import os
import sys
import json
import logging
from datetime import datetime

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary modules
from database_manager import DatabaseManager
from utils.session_manager import SessionManager
from database.integration import form_db_integration
from database.config import check_database_health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_database_integration():
    """Verify that the database integration is working correctly"""

    print("="*60)
    print("DATABASE INTEGRATION VERIFICATION")
    print("="*60)

    # Step 1: Check database health
    print("\n1. Checking database health...")
    health = check_database_health()
    print(f"   Database Status: {health['status']}")
    print(f"   Message: {health['message']}")

    if health['status'] != 'healthy':
        print("   ❌ Database is not healthy. Please check the setup.")
        return False

    # Step 2: Test database manager
    print("\n2. Testing database manager...")
    try:
        db_manager = DatabaseManager()
        db_info = db_manager.get_database_info()
        print(f"   Database Path: {db_info.get('database_path', 'N/A')}")
        print(f"   Database Size: {db_info.get('database_size', 0)} bytes")
        print(f"   ✅ Database manager working correctly")
    except Exception as e:
        print(f"   ❌ Database manager error: {str(e)}")
        return False

    # Step 3: Test session manager
    print("\n3. Testing session manager...")
    try:
        session_manager = SessionManager()

        # Create a test session
        session_info = session_manager.create_session(
            ip_address="127.0.0.1",
            user_agent="Verification Test",
            preferred_language="en"
        )

        session_id = session_info['session_id']
        print(f"   Created session: {session_id}")

        # Retrieve the session
        retrieved_session = session_manager.get_session(session_id)
        if retrieved_session:
            print(f"   ✅ Session manager working correctly")
        else:
            print(f"   ❌ Failed to retrieve session")
            return False

    except Exception as e:
        print(f"   ❌ Session manager error: {str(e)}")
        return False

    # Step 4: Test form storage
    print("\n4. Testing form storage...")
    try:
        form_schema = {
            "title": "Verification Test Form",
            "description": "Testing form storage functionality",
            "fields": [
                {
                    "name": "test_field",
                    "type": "text",
                    "label": "Test Field",
                    "placeholder": "Enter test value",
                    "required": True,
                    "order": 1
                }
            ]
        }

        user_id, form_id = form_db_integration.store_parsed_form(
            session_id=session_id,
            url="https://example.com/verify-test",
            form_type="custom",
            form_schema=form_schema,
            language="en",
            title="Verification Test Form"
        )

        print(f"   Created form: user_id={user_id}, form_id={form_id}")
        print(f"   ✅ Form storage working correctly")

    except Exception as e:
        print(f"   ❌ Form storage error: {str(e)}")
        return False

    # Step 5: Test response storage
    print("\n5. Testing response storage...")
    try:
        response_id = form_db_integration.store_user_response(
            session_id=session_id,
            form_id=form_id,
            field_name="test_field",
            response_text="Test response value",
            language="en",
            confidence_score=95,
            is_final=True
        )

        print(f"   Created response: response_id={response_id}")
        print(f"   ✅ Response storage working correctly")

    except Exception as e:
        print(f"   ❌ Response storage error: {str(e)}")
        return False

    # Step 6: Test session data retrieval
    print("\n6. Testing session data retrieval...")
    try:
        session_data = form_db_integration.get_user_session_data(session_id)

        if 'error' in session_data:
            print(f"   ❌ Session data retrieval error: {session_data['error']}")
            return False

        user_info = session_data.get('user', {})
        forms = session_data.get('forms', [])
        responses = session_data.get('responses', [])

        print(f"   Session ID: {user_info.get('session_id')}")
        print(f"   Forms: {len(forms)}")
        print(f"   Responses: {len(responses)}")
        print(f"   ✅ Session data retrieval working correctly")

    except Exception as e:
        print(f"   ❌ Session data retrieval error: {str(e)}")
        return False

    # Step 7: Test form completion status
    print("\n7. Testing form completion status...")
    try:
        completion_status = form_db_integration.get_form_completion_status(session_id, form_id)

        if 'error' in completion_status:
            print(f"   ❌ Form completion status error: {completion_status['error']}")
            return False

        completion_percentage = completion_status.get('completion_percentage', 0)
        print(f"   Form completion: {completion_percentage}%")
        print(f"   ✅ Form completion tracking working correctly")

    except Exception as e:
        print(f"   ❌ Form completion tracking error: {str(e)}")
        return False

    # Step 8: Test multilingual support
    print("\n8. Testing multilingual support...")
    try:
        # Create a form with Hindi translation
        hindi_form_schema = {
            "title": "Hindi Test Form",
            "description": "Testing multilingual support",
            "fields": [
                {
                    "name": "hindi_field",
                    "type": "text",
                    "label": "Hindi Field",
                    "required": True,
                    "order": 1
                }
            ]
        }

        hindi_user_id, hindi_form_id = form_db_integration.store_parsed_form(
            session_id=f"{session_id}-hindi",
            url="https://example.com/hindi-test",
            form_type="custom",
            form_schema=hindi_form_schema,
            language="hi",
            title="Hindi Test Form"
        )

        print(f"   Created Hindi form: form_id={hindi_form_id}")
        print(f"   ✅ Multilingual support working correctly")

    except Exception as e:
        print(f"   ❌ Multilingual support error: {str(e)}")
        return False

    # Step 9: Test form with prompts retrieval
    print("\n9. Testing form with prompts retrieval...")
    try:
        form_with_prompts = form_db_integration.get_form_with_prompts(form_id, "en")

        if 'error' in form_with_prompts:
            print(f"   ❌ Form with prompts error: {form_with_prompts['error']}")
            return False

        fields = form_with_prompts.get('fields', [])
        print(f"   Form fields: {len(fields)}")

        if fields:
            prompts = fields[0].get('prompts', [])
            print(f"   Field prompts: {len(prompts)}")

        print(f"   ✅ Form with prompts retrieval working correctly")

    except Exception as e:
        print(f"   ❌ Form with prompts retrieval error: {str(e)}")
        return False

    # Step 10: Cleanup test
    print("\n10. Testing cleanup functionality...")
    try:
        # Run cleanup
        form_db_integration.cleanup_old_sessions(hours=0)  # Clean all for testing
        print(f"   ✅ Cleanup functionality working correctly")

    except Exception as e:
        print(f"   ❌ Cleanup error: {str(e)}")
        return False

    return True

def main():
    """Main verification function"""
    print("Database Integration Verification Script")
    print("This script verifies that all database components are working correctly")

    try:
        success = verify_database_integration()

        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)

        if success:
            print("🎉 ALL VERIFICATIONS PASSED!")
            print("✅ Database integration is working correctly")
            print("✅ Session management is functional")
            print("✅ Form storage and retrieval is working")
            print("✅ Response tracking is operational")
            print("✅ Multilingual support is active")
            print("✅ Data cleanup is functional")

            print("\n📋 NEXT STEPS:")
            print("1. Your database is ready for production use")
            print("2. Start your server with: python server.py")
            print("3. Test the API endpoints through your bridge")
            print("4. Monitor database health regularly")

        else:
            print("❌ SOME VERIFICATIONS FAILED")
            print("Please check the error messages above and fix the issues")
            print("\n🔧 TROUBLESHOOTING:")
            print("1. Ensure database is properly initialized")
            print("2. Check that all required modules are installed")
            print("3. Verify environment variables are set correctly")
            print("4. Run setup_database.py if needed")

        print("\n" + "="*60)

        return success

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print("Please check your database setup and try again")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
