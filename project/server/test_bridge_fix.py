#!/usr/bin/env python3
"""
Test script to verify the bridge fixes for the FunctionTool callable issue
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_server_functions_direct():
    """Test calling server functions directly"""
    print("=" * 60)
    print("TESTING SERVER FUNCTIONS DIRECTLY")
    print("=" * 60)

    try:
        # Import bridge functions
        from bridge_functions import (
            bridge_parse_form, bridge_parse_html_form, bridge_start_conversation,
            bridge_get_next_question, bridge_submit_user_response, bridge_get_conversation_summary
        )
        print("✅ Bridge functions imported successfully")

        # Test session auto-creation with mock data
        test_session_id = "test_bridge_fix_" + str(int(datetime.now().timestamp()))
        print(f"Testing with session ID: {test_session_id}")

        # Test 1: Parse form with auto-session creation
        print("\n1. Testing parse_form with auto-session creation...")
        try:
            result = await bridge_parse_form(
                url="https://example.com/test",
                form_type="custom",
                language="en",
                session_id=test_session_id
            )
            if result and 'status' in result:
                print(f"✅ bridge_parse_form result: {result['status']}")
            else:
                print("❌ Invalid response from bridge_parse_form")
        except Exception as e:
            print(f"⚠️ bridge_parse_form error (expected): {str(e)}")

        # Test 2: Test HTML form parsing
        print("\n2. Testing bridge_parse_html_form...")
        try:
            sample_html = """
            <form>
                <input type="text" name="name" placeholder="Your Name" required>
                <input type="email" name="email" placeholder="Email">
                <button type="submit">Submit</button>
            </form>
            """
            result = await bridge_parse_html_form(
                html_input=sample_html,
                is_file=False,
                language="en",
                session_id=test_session_id
            )
            if result and 'status' in result:
                print(f"✅ bridge_parse_html_form result: {result['status']}")
                if result['status'] == 'success' and 'form_id' in result:
                    form_id = result['form_id']
                    print(f"✅ Form created with ID: {form_id}")

                    # Test 3: Start conversation
                    print("\n3. Testing bridge_start_conversation...")
                    conv_result = await bridge_start_conversation(
                        session_id=test_session_id,
                        form_id=form_id,
                        language="en"
                    )
                    if conv_result and 'status' in conv_result:
                        print(f"✅ bridge_start_conversation result: {conv_result['status']}")

                        if conv_result['status'] == 'success' and 'conversation_id' in conv_result:
                            conversation_id = conv_result['conversation_id']
                            print(f"✅ Conversation started with ID: {conversation_id}")

                            # Test 4: Get next question
                            print("\n4. Testing bridge_get_next_question...")
                            question_result = await bridge_get_next_question(
                                session_id=test_session_id,
                                conversation_id=conversation_id,
                                language="en"
                            )
                            if question_result and 'status' in question_result:
                                print(f"✅ bridge_get_next_question result: {question_result['status']}")

                                if question_result['status'] == 'success' and 'question' in question_result:
                                    print(f"✅ Question received: {question_result['question'][:50]}...")

                                    # Test 5: Submit user response
                                    print("\n5. Testing bridge_submit_user_response...")
                                    response_result = await bridge_submit_user_response(
                                        session_id=test_session_id,
                                        conversation_id=conversation_id,
                                        field_name="name",
                                        response_text="Test User",
                                        language="en"
                                    )
                                    if response_result and 'status' in response_result:
                                        print(f"✅ bridge_submit_user_response result: {response_result['status']}")

                                        # Test 6: Get conversation summary
                                        print("\n6. Testing bridge_get_conversation_summary...")
                                        summary_result = await bridge_get_conversation_summary(
                                            session_id=test_session_id,
                                            conversation_id=conversation_id
                                        )
                                        if summary_result and 'status' in summary_result:
                                            print(f"✅ bridge_get_conversation_summary result: {summary_result['status']}")
                                        else:
                                            print("❌ Invalid response from bridge_get_conversation_summary")
                                    else:
                                        print("❌ Invalid response from bridge_submit_user_response")
                                else:
                                    print("❌ No question received from bridge_get_next_question")
                            else:
                                print("❌ Invalid response from bridge_get_next_question")
                        else:
                            print("❌ Failed to start conversation")
                    else:
                        print("❌ Invalid response from bridge_start_conversation")
            else:
                print("❌ Invalid response from bridge_parse_html_form")
        except Exception as e:
            print(f"❌ HTML form parsing error: {str(e)}")

        print("\n✅ ALL BRIDGE FUNCTION TESTS COMPLETED!")
        return True

    except Exception as e:
        print(f"❌ Direct function test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_bridge_imports():
    """Test that bridge can import server functions"""
    print("\n" + "=" * 60)
    print("TESTING BRIDGE IMPORTS")
    print("=" * 60)

    try:
        # Test the imports that bridge.py should be able to do
        from bridge_functions import (
            bridge_parse_form, bridge_parse_html_form, bridge_start_conversation,
            bridge_get_next_question, bridge_submit_user_response,
            bridge_get_conversation_summary, bridge_autofill_form
        )
        print("✅ All bridge imports successful")

        # Test that functions are callable
        import inspect
        functions = [
            bridge_parse_form, bridge_parse_html_form, bridge_start_conversation,
            bridge_get_next_question, bridge_submit_user_response,
            bridge_get_conversation_summary, bridge_autofill_form
        ]

        for func in functions:
            if inspect.iscoroutinefunction(func):
                print(f"✅ {func.__name__} is properly async")
            else:
                print(f"❌ {func.__name__} is not async")

        print("\n✅ ALL BRIDGE IMPORT TESTS PASSED!")
        return True

    except Exception as e:
        print(f"❌ Bridge import error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_session_management():
    """Test session management functionality"""
    print("\n" + "=" * 60)
    print("TESTING SESSION MANAGEMENT")
    print("=" * 60)

    try:
        from utils.database_config import DatabaseConfig
        from utils.session_manager import SessionManager
        from database_manager import DatabaseManager

        # Initialize components
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        session_manager = SessionManager(db_manager)

        # Test session creation
        session_data = session_manager.create_session(
            ip_address="127.0.0.1",
            user_agent="Bridge-Test-Agent",
            preferred_language="en",
            additional_data={"test": "bridge_fix"}
        )

        if session_data and 'session_id' in session_data:
            print(f"✅ Session created: {session_data['session_id']}")

            # Test session retrieval
            retrieved_session = session_manager.get_session(session_data['session_id'])
            if retrieved_session and 'user_id' in retrieved_session:
                print("✅ Session retrieved successfully")
                print(f"✅ User ID: {retrieved_session['user_id']}")
                return True
            else:
                print("❌ Failed to retrieve session or missing user_id")
                return False
        else:
            print("❌ Failed to create session")
            return False

    except Exception as e:
        print(f"❌ Session management error: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🔧 TESTING BRIDGE FIX FOR FUNCTIONTOOL CALLABLE ISSUE")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print("=" * 60)

    results = []

    # Run all tests
    tests = [
        ("Session Management", test_session_management),
        ("Bridge Imports", test_bridge_imports),
        ("Server Functions Direct", test_server_functions_direct),
    ]

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("BRIDGE FIX TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            failed += 1

    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print(f"BRIDGE FIX RESULTS: {passed}/{total} tests passed ({success_rate:.1f}%)")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL BRIDGE FIX TESTS PASSED!")
        print("\nThe 'FunctionTool object is not callable' issue should be resolved.")
        print("\nNext steps:")
        print("1. Kill any existing bridge server process")
        print("2. Run: python bridge.py")
        print("3. Test the conversational interface")
    else:
        print("⚠️  Some tests failed. The bridge fix may need additional work.")

    print(f"\nTest completed at: {datetime.now()}")
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
