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

    def __init__(self):
        self.chat_history = InMemoryChatMessageHistory()
        self.llm = self._initialize_llm()
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

    def generate_questions(self, form_schema: Dict[str, Any], context: str = "") -> List[Dict[str, str]]:
        """Generate conversational questions for each field in the form schema."""
        questions = []
        try:
            form_fields = form_schema.get("forms", [{}])[0].get("fields", [])
            for field in form_fields:
                field_type = field.get("type", "text")
                label = field.get("label", "Untitled Field")
                required = str(field.get("required", False)).lower()
                options = [opt["text"] for opt in field.get("options", [])] if field.get("options") else []

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
                    # Ensure question is clean (remove any code-like content)
                    if question.startswith("def ") or "print(" in question:
                        question = f"Can you provide your {label}?"
                    questions.append({
                        "field_id": field.get("id"),
                        "label": label,
                        "question": question
                    })
                    logger.info(f"Generated question for field '{label}': {question}")
                    # Update conversation history
                    self.chat_history.add_user_message(field_input)
                    self.chat_history.add_ai_message(question)
                except Exception as e:
                    logger.error(f"Error generating question for field '{label}': {str(e)}")
                    fallback_question = f"Can you provide your {label}?"
                    questions.append({
                        "field_id": field.get("id"),
                        "label": label,
                        "question": fallback_question
                    })
                    # Save fallback question to history
                    self.chat_history.add_user_message(field_input)
                    self.chat_history.add_ai_message(fallback_question)

            return questions
        except Exception as e:
            logger.error(f"Error processing form schema: {str(e)}")
            return []

    def parse_response(self, user_response: str, field: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate user response based on field type."""
        try:
            field_type = field.get("type", "text")
            label = field.get("label", "Untitled Field")
            validation = field.get("validation", {})
            response_data = {"field_id": field.get("id"), "value": user_response, "valid": True}

            if validation.get("required") and not user_response.strip():
                response_data["valid"] = False
                response_data["error"] = f"{label} is required."
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message("Validation: Invalid")
                return response_data

            if field_type in ["multiple_choice", "dropdown"]:
                options = [opt["text"] for opt in field.get("options", [])]
                if user_response not in options:
                    response_data["valid"] = False
                    response_data["error"] = f"Invalid option selected for {label}. Choose from: {', '.join(options)}"
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")
            elif field_type == "checkbox":
                options = [opt["text"] for opt in field.get("options", [])]
                selected = [r.strip() for r in user_response.split(",") if r.strip()]
                invalid = [s for s in selected if s not in options]
                if invalid:
                    response_data["valid"] = False
                    response_data["error"] = f"Invalid options for {label}: {', '.join(invalid)}"
                response_data["value"] = selected
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")
            elif field_type == "email":
                if not "@" in user_response or not "." in user_response:
                    response_data["valid"] = False
                    response_data["error"] = f"Invalid email format for {label}."
                self.chat_history.add_user_message(f"Field: {label}, Response: {user_response}")
                self.chat_history.add_ai_message(f"Validation: {'Valid' if response_data['valid'] else 'Invalid'}")

            return response_data
        except Exception as e:
            logger.error(f"Error parsing response for field '{field.get('label')}': {str(e)}")
            response_data = {
                "field_id": field.get("id"),
                "value": user_response,
                "valid": False,
                "error": f"Failed to validate response: {str(e)}"
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

# Testing Framework
def test_llm_conversation():
    """Test suite for LLMConversation class."""
    llm_conv = LLMConversation()  # Use local Ollama model

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
        questions = llm_conv.generate_questions(sample_schema, context="Filling out a user profile form")
        assert len(questions) == 5, "Should generate questions for all fields"
        assert all(q["question"] for q in questions), "All questions should be non-empty"
        assert "Full Name" in [q["label"] for q in questions], "Full Name field should be included"

    def test_response_parsing():
        field = sample_schema["forms"][0]["fields"][2]  # Color (multiple_choice)
        response = llm_conv.parse_response("Red", field)
        assert response["valid"], "Valid response should be accepted"
        assert response["value"] == "Red", "Response value should match input"

        response = llm_conv.parse_response("Yellow", field)
        assert not response["valid"], "Invalid response should be rejected"
        assert "Invalid option" in response["error"], "Error message should indicate invalid option"

    def test_context_management():
        llm_conv.clear_context()
        llm_conv.generate_questions(sample_schema, context="Filling out a user profile form")
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