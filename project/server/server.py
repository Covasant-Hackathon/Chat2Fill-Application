import logging
import json
import os
import time
import threading
import asyncio
from typing import Dict, List, Any  # Added imports for type hints
from fastmcp import FastMCP
import google.generativeai as genai
from form_parser import FormParser
from llm_conversation import LLMConversation
from multilingual_support import MultilingualSupport
from form_autofiller import FormAutofiller
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
parent_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(parent_path)
logger.info("Loading environment variables")

# Directory for saving questions
QUESTIONS_DIR = "questions"
if not os.path.exists(QUESTIONS_DIR):
    os.makedirs(QUESTIONS_DIR)

# Cleanup thread for question files
def cleanup_question_files():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(QUESTIONS_DIR):
                file_path = os.path.join(QUESTIONS_DIR, filename)
                if os.path.isfile(file_path) and filename.startswith("questions_") and filename.endswith(".json"):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 24 * 3600:
                        os.remove(file_path)
                        logger.info(f"Deleted old question file: {file_path}")
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Error during question file cleanup: {str(e)}")
            time.sleep(3600)

cleanup_thread = threading.Thread(target=cleanup_question_files, daemon=True)
cleanup_thread.start()

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in .env file")
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=GEMINI_API_KEY)
logger.info("Gemini API configured")

# Initialize Gemini model
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("Gemini model initialized")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    raise

# Initialize components
try:
    llm_conv = LLMConversation()
    multilingual = MultilingualSupport()
    autofiller = FormAutofiller()
    logger.info("LLMConversation, MultilingualSupport, and FormAutofiller initialized")
except Exception as e:
    logger.error(f"Failed to initialize components: {str(e)}")
    raise

# Initialize FastMCP
try:
    mcp = FastMCP("Form Parser Server")
    logger.info("FastMCP server initialized with name: Form Parser Server")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {str(e)}")
    raise

@mcp.tool()
async def parse_form(url: str, form_type: str, language: str = "en") -> Dict[str, Any]:
    logger.info(f"Received parse_form request: url={url}, form_type={form_type}, language={language}")
    try:
        if not url or len(url) > 2000:
            logger.warning(f"Invalid URL: {url[:50]}...")
            return {
                "status": "error",
                "error": "URL is empty or exceeds maximum length of 2000 characters",
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }
        
        if form_type not in {'google', 'typeform', 'microsoft', 'custom'}:
            logger.warning(f"Invalid form type: {form_type}")
            return {
                "status": "error",
                "error": "Invalid form type. Must be one of: google, typeform, microsoft, custom",
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        prompt = f"""
        You are a web form expert. Validate the provided URL and form type.
        - Check if the URL appears to be a valid web form URL.
        - Confirm if the form type matches the expected platform.
        - If ambiguous, suggest the most likely type or default to 'custom'.
        Input: URL: {url}, Form Type: {form_type}
        Output format: {{ "url": "validated URL", "form_type": "validated form type", "is_valid": true/false, "message": "explanation" }}
        """
        gemini_response = model.generate_content(prompt)

        if not hasattr(gemini_response, 'text') or not gemini_response.text:
            logger.error("Invalid Gemini response: No text content")
            return {
                "status": "error",
                "error": "Invalid Gemini response: No text content",
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        gemini_data = gemini_response.text.strip()
        if gemini_data.startswith("```json"):
            gemini_data = gemini_data[7:].strip()
        if gemini_data.endswith("```"):
            gemini_data = gemini_data[:-3].strip()

        try:
            gemini_result = json.loads(gemini_data)
            logger.info("Gemini response parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {str(e)}")
            return {
                "status": "error",
                "error": "Failed to parse Gemini response",
                "gemini_message": gemini_data,
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        validated_url = gemini_result.get("url")
        validated_form_type = gemini_result.get("form_type")
        if not validated_url or not gemini_result.get("is_valid"):
            logger.warning(f"Invalid input from Gemini: {gemini_result.get('message')}")
            return {
                "status": "error",
                "error": gemini_result.get("message", "Invalid input from Gemini"),
                "gemini_message": gemini_result.get("message", ""),
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        parser = FormParser(use_profile=(validated_form_type == 'microsoft'), debug_mode=True)
        form_schema = await parser.parse_form_from_url(validated_url, validated_form_type)
        translated_form_schema = multilingual.translate_form_fields(form_schema, language)
        questions = llm_conv.generate_questions(form_schema, context=f"Parsing a {validated_form_type} form from {validated_url}", language=language)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        questions_file = os.path.join(QUESTIONS_DIR, f"questions_{timestamp}.json")
        try:
            with open(questions_file, "w", encoding='utf-8') as f:
                json.dump(questions, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved questions to {questions_file}")
        except Exception as e:
            logger.error(f"Failed to save questions to {questions_file}: {str(e)}")

        return {
            "status": "success",
            "form_schema": form_schema,
            "translated_form_schema": translated_form_schema,
            "gemini_url": validated_url,
            "gemini_form_type": validated_form_type,
            "gemini_message": gemini_result.get("message", ""),
            "questions": questions
        }

    except ValueError as e:
        logger.error(f"ValueError while parsing form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "gemini_message": gemini_result.get("message", "") if 'gemini_result' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error processing form at '{url}': {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "gemini_message": gemini_result.get("message", "") if 'gemini_result' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }

@mcp.tool()
async def parse_html_form(html_input: str, is_file: bool = False, language: str = "en") -> Dict[str, Any]:
    logger.info(f"Received parse_html_form request: is_file={is_file}, language={language}")
    try:
        if not html_input:
            logger.warning("Empty HTML input provided")
            return {
                "status": "error",
                "error": "HTML input cannot be empty",
                "gemini_message": "",
                "form_schema": {},
                "translated_form_schema": {},
                "questions": []
            }

        prompt = f"""
        You are a web form expert. Validate the provided HTML content for a valid form structure.
        - Check for <form> tag or form-like elements (input, select, textarea).
        - Return a message indicating validity.
        Input: HTML: {html_input[:1000]}... (truncated)
        Output format: {{ "is_valid": true/false, "message": "explanation" }}
        """
        gemini_response = model.generate_content(prompt)

        gemini_message = ""
        if hasattr(gemini_response, 'text') and gemini_response.text:
            gemini_data = gemini_response.text.strip()
            if gemini_data.startswith("```json"):
                gemini_data = gemini_data[7:].strip()
            if gemini_data.endswith("```"):
                gemini_data = gemini_data[:-3].strip()
            try:
                gemini_result = json.loads(gemini_data)
                gemini_message = gemini_result.get("message", "")
                if not gemini_result.get("is_valid"):
                    logger.warning(f"Gemini validation failed: {gemini_message}")
                    return {
                        "status": "error",
                        "error": gemini_message or "Invalid HTML form structure",
                        "gemini_message": gemini_message,
                        "form_schema": {},
                        "translated_form_schema": {},
                        "questions": []
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini response: {str(e)}")
                gemini_message = gemini_data

        parser = FormParser(debug_mode=True)
        form_schema = await parser.parse_html_content(html_input, is_file)
        translated_form_schema = multilingual.translate_form_fields(form_schema, language)
        questions = llm_conv.generate_questions(form_schema, context="Parsing a static HTML form", language=language)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        questions_file = os.path.join(QUESTIONS_DIR, f"questions_{timestamp}.json")
        try:
            with open(questions_file, "w", encoding='utf-8') as f:
                json.dump(questions, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved questions to {questions_file}")
        except Exception as e:
            logger.error(f"Failed to save questions to {questions_file}: {str(e)}")

        return {
            "status": "success",
            "form_schema": form_schema,
            "translated_form_schema": translated_form_schema,
            "gemini_message": gemini_message,
            "questions": questions
        }

    except ValueError as e:
        logger.error(f"ValueError while parsing HTML: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "gemini_message": gemini_message if 'gemini_message' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error parsing HTML: {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "gemini_message": gemini_message if 'gemini_message' in locals() else "",
            "form_schema": {},
            "translated_form_schema": {},
            "questions": []
        }

@mcp.tool()
async def autofill_form(url: str, form_schema: Dict[str, Any], responses: List[Dict[str, Any]], language: str = "en") -> Dict[str, Any]:
    """
    Autofill a web form using Playwright based on schema and responses.
    
    Args:
        url: URL of the form to autofill.
        form_schema: Parsed form schema from parse_form.
        responses: List of field responses from LLMConversation.
        language: Language for translated field labels.
    
    Returns:
        dict: Autofill status, filled fields, errors, screenshots, and logs.
    """
    logger.info(f"Received autofill_form request: url={url}, language={language}")
    try:
        if not url:
            return {"status": "error", "error": "URL is empty", "filled_fields": [], "errors": [], "screenshots": [], "log_file": ""}

        await autofiller.initialize()
        translated_schema = multilingual.translate_form_fields(form_schema, language)
        result = await autofiller.autofill_form(url, translated_schema, responses)
        return result

    except Exception as e:
        logger.error(f"Error autofilling form: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "filled_fields": [],
            "errors": [str(e)],
            "screenshots": [],
            "log_file": ""
        }
    finally:
        await autofiller.close()

if __name__ == "__main__":
    try:
        logger.info("Starting FastMCP server with stdio transport")
        mcp.run(transport="stdio")
        logger.info("FastMCP server started successfully")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise