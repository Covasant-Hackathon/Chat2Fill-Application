import sys
import os
import json

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.admin import DatabaseAdmin
from database.config import check_database_health
from database.integration import form_db_integration

def test_database_quick():
    """Quick database test"""
    print("=" * 50)
    print("QUICK DATABASE TEST")
    print("=" * 50)

    # Test database health
    print("\n1. Testing Database Health...")
    health = check_database_health()
    print(f"Status: {health['status']}")
    print(f"Message: {health['message']}")

    # Test admin functionality
    print("\n2. Testing Database Admin...")
    admin = DatabaseAdmin()
    stats = admin.get_database_stats()

    if 'error' not in stats:
        print("Database Stats:")
        print(f"  Users: {stats['users']}")
        print(f"  Active Users: {stats['active_users']}")
        print(f"  Forms: {stats['forms']}")
        print(f"  Form Fields: {stats['form_fields']}")
        print(f"  Prompts: {stats['prompts']}")
        print(f"  User Responses: {stats['user_responses']}")
        print(f"  Conversation Messages: {stats['conversation_messages']}")
        print(f"  Database Size: {stats['database_size']} bytes")
    else:
        print(f"Error: {stats['error']}")

    # Test integration
    print("\n3. Testing Integration Layer...")
    try:
        # Create a test form
        form_schema = {
            "title": "Quick Test Form",
            "description": "Testing database integration",
            "fields": [
                {
                    "name": "test_field",
                    "type": "text",
                    "label": "Test Field",
                    "required": True,
                    "order": 1
                }
            ]
        }

        user_id, form_id = form_db_integration.store_parsed_form(
            session_id="quick-test-session",
            url="https://example.com/quick-test",
            form_type="custom",
            form_schema=form_schema,
            language="en"
        )

        print(f"Created form: user_id={user_id}, form_id={form_id}")

        # Get session data
        session_data = form_db_integration.get_user_session_data("quick-test-session")
        if 'error' not in session_data:
            print(f"Session data retrieved successfully:")
            print(f"  Forms: {len(session_data['forms'])}")
            print(f"  Responses: {len(session_data['responses'])}")
        else:
            print(f"Error retrieving session data: {session_data['error']}")

    except Exception as e:
        print(f"Integration test failed: {str(e)}")

    print("\n" + "=" * 50)
    print("DATABASE TEST COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    test_database_quick()
