import os
import json
import logging
from typing import List, Dict, Any, Optional
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from multilingual_support import MultilingualSupport
from database_manager import DatabaseManager
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

class LLMConversation:
    """Manages conversational prompt generation from form fields using LangChain with Ollama."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.chat_history = InMemoryChatMessageHistory()
        self.llm = self._initialize_llm()
        self.db_manager = db_manager or DatabaseManager()
        self.multilingual = MultilingualSupport(self.db_manager)
        self.prompt_templates = self._define_prompt_templates()
        self.runnable = RunnableWithMessageHistory(
            runnable=self.llm,
            get_session_history=lambda session_id: self.chat_history,
            input_messages_key="field_input",
            history_messages_key="history"
        )

    def _initialize_llm(self):
        """Initialize local Ollama model."""
        try:
            logger.info(f"Initializing Ollama model: {OLLAMA_MODEL}")
            return OllamaLLM(
                model=OLLAMA_MODEL,
                base_url="http://localhost:11434",
                temperature=0.7
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama model: {str(e)}")
            raise

    def _define_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Define prompt templates for different field types."""
        templates = {
            "text": PromptTemplate(
                input_variables=["label", "required", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}), generate a conversational question to prompt the user for input.
                Context: {context}
                Ensure the question is clear, polite, and contextually relevant. Output ONLY the question as plain text, no code or additional text.
                Example: What is your full name?
                """
            ),
            "paragraph": PromptTemplate(
                input_variables=["label", "required", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}), generate a conversational question for a longer text response.
                Context: {context}
                Encourage detailed input and keep the tone friendly. Output ONLY the question as plain text, no code or additional text.
                Example: Please describe your project in a few sentences.
                """
            ),
            "multiple_choice": PromptTemplate(
                input_variables=["label", "required", "options", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}) and options {options}, generate a conversational question for selecting one option.
                Context: {context}
                Present options clearly and ask for a single choice. Output ONLY the question as plain text, no code or additional text.
                Example: Which color do you prefer: Red, Blue, or Green?
                """
            ),
            "checkbox": PromptTemplate(
                input_variables=["label", "required", "options", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}) and options {options}, generate a conversational question for selecting multiple options.
                Context: {context}
                Indicate that multiple selections are allowed. Output ONLY the question as plain text, no code or additional text.
                Example: Which hobbies do you enjoy? You can choose multiple: Reading, Hiking, Painting.
                """
            ),
            "dropdown": PromptTemplate(
                input_variables=["label", "required", "options", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}) and options {options}, generate a conversational question for selecting one option from a dropdown.
                Context: {context}
                Present options clearly and ask for a single choice. Output ONLY the question as plain text, no code or additional text.
                Example: Which country are you from? Options: USA, Canada, UK.
                """
            ),
            "fallback": PromptTemplate(
                input_variables=["label", "required", "context"],
                template="""
                Given a form field with label "{label}" (required: {required}), generate a generic conversational question.
                Context: {context}
                Keep the question simple and relevant. Output ONLY the question as plain text, no code or additional text.
                Example: Can you provide your {label}?
                """
            )
        }
        return templates

    def generate_questions(self, form_schema: Dict[str, Any], context: str = "", language: str = "en",
                          form_id: int = None) -> List[Dict[str, str]]:
        """Generate conversational questions for each field in the form schema with database persistence."""
        questions = []
        try:
            # Translate form schema
            translated_schema = self.multilingual.translate_form_fields(form_schema, language)
            form_fields = translated_schema.get("forms", [{}])[0].get("fields", [])

            for field in form_fields:
                field_type = field.get("type", "text")
                label = field.get("translated_label", field.get("label", "Untitled Field"))
                required = str(field.get("required", False)).lower()
                options = [opt["translated_text"] for opt in field.get("translated_options", [])] if field.get("options") else []

                template = self.prompt_templates.get(field_type, self.prompt_templates["fallback"])
                chain = RunnableSequence(template | self.llm)

                try:
                    field_input = f"Field: {label}, Context: {context}"
                    question = chain.invoke({
                        "label": label,
                        "required": required,
                        "options": options,
                        "context": context
                    }).strip()

                    # Ensure question is clean
                    if question.startswith("def ") or "print(" in question:
                        question = f"Can you provide your {label}?"

                    # Translate question if needed
                    translated_question = self.multilingual.translate(question, "en", language) if language != "en" else question

                    question_data = {
                        "field_id": field.get("id"),
                        "label": field.get("label"),
                        "question": question,
                        "translated_question": translated_question,
                        "field_type": field_type,
                        "language": language,
                        "context": context
                    }

                    # Save to database if form_id is provided
                    if form_id and self.db_manager:
                        try:
                            # Get or create form field in database
                            form_fields_db = self.db_manager.get_form_fields(form_id)
                            field_db = next((f for f in form_fields_db if f['field_name'] == field.get("name", field.get("id"))), None)

                            if field_db:
                                # Save prompt to database
                                prompt_data = [{
                                    "text": question,
                                    "type": "question",
                                    "language": "en",
                                    "context": context
                                }]

                                if language != "en":
                                    prompt_data.append({
                                        "text": translated_question,
                                        "type": "question",
                                        "language": language,
                                        "context": context
                                    })

                                prompt_ids = self.db_manager.save_prompts(field_db['id'], prompt_data)
                                question_data["prompt_ids"] = prompt_ids
                                logger.info(f"Saved prompts to database for field '{label}'")
                        except Exception as e:
                            logger.error(f"Error saving prompt to database: {str(e)}")

                    questions.append(question_data)
                    logger.info(f"Generated question for field '{label}': {question}")
                    self.chat_history.add_user_message(field_input)
                    self.chat_history.add_ai_message(question)

                except Exception as e:
                    logger.error(f"Error generating question for field '{label}': {str(e)}")
                    fallback_question = f"Can you provide your {label}?"
                    translated_fallback = self.multilingual.translate(fallback_question, "en", language) if language != "en" else fallback_question

                    questions.append({
                        "field_id": field.get("id"),
                        "label": field.get("label"),
                        "question": fallback_question,
                        "translated_question": translated_fallback,
                        "field_type": field_type,
                        "language": language,
                        "context": context
                    })
                    self.chat_history.add_user_message(field_input)
                    self.chat_history.add_ai_message(fallback_question)

            return questions
        except Exception as e:
            logger.error(f"Error processing form schema: {str(e)}")
            return []

    def parse_response(self, user_response: str, field: Dict[str, Any], user_language: str = "en",
                      conversation_id: int = None, prompt_id: int = None) -> Dict[str, Any]:
        """Parse and validate user response based on field type with database persistence."""
        try:
            field_type = field.get("type", "text")
            label = field.get("translated_label", field.get("label", "Untitled Field"))
            validation = field.get("validation", {})

            # Translate user response to English for validation
            response_en = self.multilingual.translate_response(user_response, user_language, "en")
            response_data = {
                "field_id": field.get("id"),
                "value": response_en,
                "valid": True,
                "original_response": user_response,
                "response_language": user_language,
                "validation_status": "valid"
            }

            if validation.get("required") and not response_en.strip():
                response_data["valid"] = False
                response_data["validation_status"] = "invalid"
                response_data["error"] = f"{label} is required."
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message("Validation: Invalid")

                # Save to database if conversation_id and prompt_id are provided
                if conversation_id and prompt_id and self.db_manager:
                    try:
                        self.db_manager.save_user_response(
                            conversation_id, prompt_id, user_response,
                            user_language, confidence_score=0.5
                        )
                        self.db_manager.update_response_validation(
                            conversation_id, "invalid"
                        )
                    except Exception as e:
                        logger.error(f"Error saving invalid response to database: {str(e)}")

                return response_data

            if field_type in ["multiple_choice", "dropdown"]:
                options = [opt["translated_text"] for opt in field.get("translated_options", field.get("options", []))]
                if response_en not in [opt["text"] for opt in field.get("options", [])]:
                    response_data["valid"] = False
                    response_data["validation_status"] = "invalid"
                    response_data["error"] = f"Invalid option selected for {label}. Choose from: {', '.join(options)}"
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")

            elif field_type == "checkbox":
                options = [opt["translated_text"] for opt in field.get("translated_options", field.get("options", []))]
                selected = [r.strip() for r in response_en.split(",") if r.strip()]
                invalid = [s for s in selected if s not in [opt["text"] for opt in field.get("options", [])]]
                if invalid:
                    response_data["valid"] = False
                    response_data["validation_status"] = "invalid"
                    response_data["error"] = f"Invalid options for {label}: {', '.join(invalid)}"
                response_data["value"] = selected
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")

            elif field_type == "email":
                if not "@" in response_en or not "." in response_en:
                    response_data["valid"] = False
                    response_data["validation_status"] = "invalid"
                    response_data["error"] = f"Invalid email format for {label}."
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")

            # Save valid response to database
            if conversation_id and prompt_id and self.db_manager and response_data["valid"]:
                try:
                    response_id = self.db_manager.save_user_response(
                        conversation_id, prompt_id, user_response,
                        user_language, confidence_score=1.0
                    )
                    self.db_manager.update_response_validation(response_id, "valid")
                    response_data["response_id"] = response_id
                    logger.info(f"Saved valid response to database: {response_id}")
                except Exception as e:
                    logger.error(f"Error saving valid response to database: {str(e)}")

            return response_data

        except Exception as e:
            logger.error(f"Error parsing response for field '{field.get('label')}': {str(e)}")
            response_data = {
                "field_id": field.get("id"),
                "value": user_response,
                "valid": False,
                "error": f"Failed to validate response: {str(e)}",
                "original_response": user_response,
                "response_language": user_language,
                "validation_status": "error"
            }
            self.chat_history.add_user_message(f"Field: {field.get('label', 'Untitled Field')}, Response: {user_response}")
            self.chat_history.add_ai_message("Validation: Invalid")
            return response_data

    def get_context(self) -> str:
        """Retrieve current conversation context."""
        messages = self.chat_history.messages
        return "\n".join([f"{msg.__class__.__name__}: {msg.content}" for msg in messages])

    def clear_context(self):
        """Clear conversation history."""
        self.chat_history.clear()
        logger.info("Conversation context cleared")

    def start_conversation(self, user_id: int, form_id: int, language: str = "en") -> Optional[int]:
        """Start a new conversation in the database."""
        try:
            conversation_id = self.db_manager.create_conversation(user_id, form_id, language)
            logger.info(f"Started conversation: {conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return None

    def update_conversation_progress(self, conversation_id: int, current_field_index: int):
        """Update conversation progress in database."""
        try:
            self.db_manager.update_conversation_progress(conversation_id, current_field_index)
            logger.info(f"Updated conversation {conversation_id} progress to field {current_field_index}")
        except Exception as e:
            logger.error(f"Error updating conversation progress: {str(e)}")

    def complete_conversation(self, conversation_id: int):
        """Mark conversation as completed in database."""
        try:
            self.db_manager.complete_conversation(conversation_id)
            logger.info(f"Completed conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Error completing conversation: {str(e)}")

    def get_conversation_responses(self, conversation_id: int) -> List[Dict]:
        """Get all responses for a conversation from database."""
        try:
            return self.db_manager.get_conversation_responses(conversation_id)
        except Exception as e:
            logger.error(f"Error getting conversation responses: {str(e)}")
            return []

    def generate_question_for_field(self, field: Dict, language: str = "en") -> str:
        """Generate a single question for a form field."""
        try:
            field_type = field.get('field_type', 'text')
            field_label = field.get('field_label', field.get('field_name', 'Field'))
            field_required = field.get('field_required', False)
            field_options = field.get('field_options')

            # Parse options if they exist
            options_text = ""
            if field_options:
                try:
                    options = json.loads(field_options) if isinstance(field_options, str) else field_options
                    if isinstance(options, list):
                        options_text = f" Options: {', '.join([str(opt) for opt in options])}"
                except:
                    pass

            # Create context for question generation
            context = f"Generate a conversational question for form field '{field_label}' of type '{field_type}'"
            if field_required:
                context += " (required field)"
            if options_text:
                context += options_text

            prompt = f"""
            Generate a natural, conversational question for a form field with the following details:
            - Field Label: {field_label}
            - Field Type: {field_type}
            - Required: {field_required}
            {options_text}

            The question should be:
            1. Conversational and friendly
            2. Clear about what information is needed
            3. In {language} language
            4. Include options if it's a multiple choice field

            Return only the question text.
            """

            if self.model:
                response = self.model.generate_content(prompt)
                question = response.text.strip() if response.text else f"What is your {field_label}?"
            else:
                question = f"What is your {field_label}?"

            # Store in database if we have a db_manager
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.create_prompt(field['id'], question, language)

            return question

        except Exception as e:
            logger.error(f"Error generating question for field: {str(e)}")
            return f"Please provide your {field.get('field_label', 'response')}:"

    def validate_response(self, response_text: str, field: Dict, language: str = "en") -> Dict:
        """Validate a user response against a field."""
        try:
            field_type = field.get('field_type', 'text')
            field_required = field.get('field_required', False)
            field_options = field.get('field_options')

            # Basic validation
            if field_required and not response_text.strip():
                return {
                    "valid": False,
                    "error": "This field is required",
                    "confidence": 0.0
                }

            # Type-specific validation
            if field_type in ['multiple_choice', 'dropdown']:
                if field_options:
                    try:
                        options = json.loads(field_options) if isinstance(field_options, str) else field_options
                        if isinstance(options, list):
                            # Check if response matches any option
                            response_lower = response_text.lower().strip()
                            for option in options:
                                if str(option).lower() == response_lower:
                                    return {"valid": True, "confidence": 1.0}

                            # Use LLM to check for close matches
                            if self.model:
                                prompt = f"""
                                Check if the user response "{response_text}" matches any of these options: {options}
                                Consider synonyms, partial matches, and different languages.
                                Return "VALID" if it matches an option, "INVALID" if not.
                                If valid, also return which option it matches.
                                """

                                llm_response = self.model.generate_content(prompt)
                                if llm_response.text and "VALID" in llm_response.text.upper():
                                    return {"valid": True, "confidence": 0.8}
                                else:
                                    return {
                                        "valid": False,
                                        "error": f"Please choose from: {', '.join([str(opt) for opt in options])}",
                                        "confidence": 0.0
                                    }
                            else:
                                return {
                                    "valid": False,
                                    "error": f"Please choose from: {', '.join([str(opt) for opt in options])}",
                                    "confidence": 0.0
                                }
                    except:
                        pass

            # For text fields, basic validation
            if field_type == 'email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, response_text):
                    return {
                        "valid": False,
                        "error": "Please enter a valid email address",
                        "confidence": 0.0
                    }

            # If we get here, it's valid
            return {"valid": True, "confidence": 0.9}

        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            return {"valid": True, "confidence": 0.5}  # Default to valid if validation fails

# Testing Framework
def test_llm_conversation():
    """Test suite for LLMConversation class."""
    llm_conv = LLMConversation()

    # Sample form schema
    sample_schema = {
        "forms": [{
            "fields": [
                {"id": "1", "label": "Full Name", "type": "text", "required": True},
                {"id": "2", "label": "Feedback", "type": "paragraph", "required": False},
                {"id": "3", "label": "Color", "type": "multiple_choice", "required": True, "options": [
                    {"text": "Red"}, {"text": "Blue"}, {"text": "Green"}
                ]},
                {"id": "4", "label": "Hobbies", "type": "checkbox", "required": False, "options": [
                    {"text": "Reading"}, {"text": "Hiking"}
                ]},
                {"id": "5", "label": "Country", "type": "dropdown", "required": True, "options": [
                    {"text": "USA"}, {"text": "Canada"}
                ]}
            ]
        }]
    }

    def test_question_generation():
        questions = llm_conv.generate_questions(sample_schema, context="Filling out a user profile form", language="hi")
        assert len(questions) == 5, "Should generate questions for all fields"
        assert all(q["question"] for q in questions), "All questions should be non-empty"
        assert all(q["translated_question"] for q in questions), "All translated questions should be non-empty"
        assert "Full Name" in [q["label"] for q in questions], "Full Name field should be included"

    def test_response_parsing():
        field = sample_schema["forms"][0]["fields"][2]  # Color (multiple_choice)
        field["translated_label"] = "रंग"
        field["translated_options"] = [{"text": "Red", "translated_text": "लाल"}, {"text": "Blue", "translated_text": "नीला"}, {"text": "Green", "translated_text": "हरा"}]
        response = llm_conv.parse_response("लाल", field, user_language="hi")
        assert response["valid"], "Valid response should be accepted"
        assert response["value"] == "Red", "Response value should match English option"
        assert response["original_response"] == "लाल", "Original response should be preserved"

        response = llm_conv.parse_response("पीला", field, user_language="hi")
        assert not response["valid"], "Invalid response should be rejected"
        assert "Invalid option" in response["error"], "Error message should indicate invalid option"

    def test_context_management():
        llm_conv.clear_context()
        llm_conv.generate_questions(sample_schema, context="Filling out a user profile form", language="hi")
        context = llm_conv.get_context()
        assert context, "Context should not be empty after question generation"
        llm_conv.clear_context()
        assert not llm_conv.get_context(), "Context should be empty after clearing"

    test_question_generation()
    test_response_parsing()
    test_context_management()
    logger.info("All tests passed successfully")

if __name__ == "__main__":
    test_llm_conversation()
