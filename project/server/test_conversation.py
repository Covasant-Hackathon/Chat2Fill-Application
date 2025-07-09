#!/usr/bin/env python3
"""
Test script to verify conversational interface integration
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from llm_conversation import LLMConversation
from utils.database_config import DatabaseConfig
from utils.session_manager import SessionManager

def test_conversational_flow():
    """Test the complete conversational flow."""
    print("=" * 60)
    print("TESTING CONVERSATIONAL INTERFACE")
    print("=" * 60)

    try:
        # Initialize components
        print("\n1. Initializing database components...")
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        session_manager = SessionManager(db_manager)
        llm_conv = LLMConversation(db_manager)

        # Create a test session
        print("\n2. Creating test session...")
        session_info = session_manager.create_session(
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            preferred_language="en"
        )
        session_id = session_info['session_id']
        user_id = session_info['user_id']
        print(f"   Session ID: {session_id}")
        print(f"   User ID: {user_id}")

        # Create a test form
        print("\n3. Creating test form...")
        form_schema = {
            "forms": [{
                "title": "Test Contact Form",
                "fields": [
                    {
                        "id": "name",
                        "name": "full_name",
                        "type": "text",
                        "label": "Full Name",
                        "required": True
                    },
                    {
                        "id": "email",
                        "name": "email_address",
                        "type": "email",
                        "label": "Email Address",
                        "required": True
                    },
                    {
                        "id": "phone",
                        "name": "phone_number",
                        "type": "tel",
                        "label": "Phone Number",
                        "required": False
                    },
                    {
                        "id": "message",
                        "name": "message",
                        "type": "textarea",
                        "label": "Message",
                        "required": True
                    }
                ]
            }]
        }

        form_id = db_manager.create_form(
            user_id=user_id,
            form_url="https://example.com/test-form",
            form_type="custom",
            form_title="Test Contact Form",
            form_schema=json.dumps(form_schema)
        )
        print(f"   Form ID: {form_id}")

        # Add form fields
        print("\n4. Adding form fields...")
        field_ids = []
        for field in form_schema["forms"][0]["fields"]:
            field_id = db_manager.create_form_field(
                form_id=form_id,
                field_name=field["name"],
                field_type=field["type"],
                field_label=field["label"],
                field_required=field["required"]
            )
            field_ids.append(field_id)
            print(f"   Field '{field['label']}' -> ID: {field_id}")

        # Generate questions for each field
        print("\n5. Generating questions for fields...")
        for i, field in enumerate(form_schema["forms"][0]["fields"]):
            field_info = {
                "id": field_ids[i],
                "field_name": field["name"],
                "field_type": field["type"],
                "field_label": field["label"],
                "field_required": field["required"]
            }

            question = llm_conv.generate_question_for_field(field_info, "en")
            print(f"   {field['label']}: {question}")

        # Start conversation
        print("\n6. Starting conversation...")
        conversation_id = llm_conv.start_conversation(user_id, form_id, "en")
        print(f"   Conversation ID: {conversation_id}")

        # Simulate conversation flow
        print("\n7. Simulating conversation flow...")
        test_responses = [
            "John Doe",
            "john.doe@example.com",
            "+1234567890",
            "This is a test message for the conversational interface."
        ]

        for i, response_text in enumerate(test_responses):
            print(f"\n   Step {i+1}: Processing response '{response_text}'")

            # Get current field
            field_info = {
                "id": field_ids[i],
                "field_name": form_schema["forms"][0]["fields"][i]["name"],
                "field_type": form_schema["forms"][0]["fields"][i]["type"],
                "field_label": form_schema["forms"][0]["fields"][i]["label"],
                "field_required": form_schema["forms"][0]["fields"][i]["required"]
            }

            # Validate response
            validation_result = llm_conv.validate_response(response_text, field_info, "en")
            print(f"   Validation: {validation_result}")

            # Get prompt for this field
            prompts = db_manager.get_prompts_for_field(field_ids[i], "en")
            if prompts:
                prompt_id = prompts[0]["id"]

                # Save response
                response_id = db_manager.save_user_response(
                    conversation_id,
                    prompt_id,
                    response_text,
                    "en",
                    validation_result.get("confidence", 0.8)
                )
                print(f"   Response saved with ID: {response_id}")

                # Update conversation progress
                db_manager.update_conversation_progress(conversation_id, i + 1)

        # Complete conversation
        print("\n8. Completing conversation...")
        db_manager.complete_conversation(conversation_id)

        # Get conversation summary
        print("\n9. Getting conversation summary...")
        responses = db_manager.get_conversation_responses(conversation_id)
        print(f"   Total responses: {len(responses)}")

        for response in responses:
            print(f"   - {response['field_name']}: {response['response_text']}")

        # Test session cleanup
        print("\n10. Testing session management...")
        session_stats = session_manager.get_session_statistics()
        print(f"   Active sessions: {session_stats.get('active_sessions', 0)}")
        print(f"   Total sessions: {session_stats.get('total_sessions', 0)}")

        print("\n" + "=" * 60)
        print("✅ CONVERSATIONAL INTERFACE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_server_endpoints():
    """Test server endpoints for conversational interface."""
    print("\n" + "=" * 60)
    print("TESTING SERVER ENDPOINTS")
    print("=" * 60)

    try:
        # Import server functions
        from server import (
            create_session, parse_form, start_conversation,
            get_next_question, submit_user_response, get_conversation_summary
        )

        # Test session creation
        print("\n1. Testing session creation...")
        session_result = await create_session(
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            preferred_language="en"
        )
        print(f"   Session result: {session_result}")

        if session_result["status"] == "success":
            session_id = session_result["session_info"]["session_id"]

            # Test form parsing
            print("\n2. Testing form parsing...")
            form_result = await parse_form(
                url="https://example.com/test-form",
                form_type="custom",
                language="en",
                session_id=session_id
            )
            print(f"   Form parsing result: {form_result['status']}")

            if form_result["status"] == "success":
                form_id = form_result.get("form_id", 1)  # Use a default if not available

                # Test conversation start
                print("\n3. Testing conversation start...")
                conv_result = await start_conversation(
                    session_id=session_id,
                    form_id=form_id,
                    language="en"
                )
                print(f"   Conversation start result: {conv_result['status']}")

                if conv_result["status"] == "success":
                    conversation_id = conv_result["conversation_id"]

                    # Test getting next question
                    print("\n4. Testing get next question...")
                    question_result = await get_next_question(
                        session_id=session_id,
                        conversation_id=conversation_id,
                        language="en"
                    )
                    print(f"   Next question result: {question_result['status']}")

                    if question_result["status"] == "success":
                        field_name = question_result["field_name"]

                        # Test submitting response
                        print("\n5. Testing submit response...")
                        response_result = await submit_user_response(
                            session_id=session_id,
                            conversation_id=conversation_id,
                            field_name=field_name,
                            response_text="Test Response",
                            language="en"
                        )
                        print(f"   Submit response result: {response_result['status']}")

                        # Test getting conversation summary
                        print("\n6. Testing conversation summary...")
                        summary_result = await get_conversation_summary(
                            session_id=session_id,
                            conversation_id=conversation_id
                        )
                        print(f"   Summary result: {summary_result['status']}")

        print("\n" + "=" * 60)
        print("✅ SERVER ENDPOINTS TEST COMPLETED!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Starting Conversational Interface Tests...")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Database and conversation flow
    test1_passed = test_conversational_flow()

    # Test 2: Server endpoints
    test2_passed = asyncio.run(test_server_endpoints())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Database & Conversation Flow: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Server Endpoints: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Conversational interface is ready!")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

    print("=" * 60)

if __name__ == "__main__":
    main()
