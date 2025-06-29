import logging
import json
import os
import time
import threading
from fastmcp import FastMCP
import google.generativeai as genai
from form_parser import FormParser
from llm_conversation import LLMConversation
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file in the parent directory
parent_path = os.path.join(os.path.dirname(__file__),'.env')
load_dotenv(parent_path)
logger.info("Loading environment variables")

# Directory for saving questions
QUESTIONS_DIR = "questions"
if not os.path.exists(QUESTIONS_DIR):
    os.makedirs(QUESTIONS_DIR)

# Cleanup thread for question files
def cleanup_question_files():
    """Run in a background thread to delete question JSON files older than 24 hours."""
    while True:
        try:
            now = time.time()
            for filename in os.listdir(QUESTIONS_DIR):
                file_path = os.path.join(QUESTIONS_DIR, filename)
                if os.path.isfile(file_path) and filename.startswith("questions_") and filename.endswith(".json"):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 24 * 3600:  # 24 hours in seconds
                        os.remove(file_path)
                        logger.info(f"Deleted old question file: {file_path}")
            time.sleep(3600)  # Check every hour
        except Exception as e:
            logger.error(f"Error during question file cleanup: {str(e)}")
            time.sleep(3600)

# Start cleanup thread
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

# Initialize LLMConversation
try:
    llm_conv = LLMConversation()
    logger.info("LLMConversation initialized")
except Exception as e:
    logger.error(f"Failed to initialize LLMConversation: {str(e)}")
    raise

# Initialize FastMCP
try:
    mcp = FastMCP("Form Parser Server")
    logger.info("FastMCP server initialized with name: Form Parser Server")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {str(e)}")
    raise

# Define MCP tool for URL-based form parsing
@mcp.tool()
def parse_form(url: str, form_type: str) -> dict:
    """
    Parse a web form from a given URL and return its schema after validating with Gemini.
    
    Args:
        url (str): URL of the form to parse.
        form_type (str): Type of form ('google', 'typeform', 'microsoft', 'custom').
    
    Returns:
        dict: Parsed form schema, status, Gemini validation message, or error message, and conversational questions.
    """
    logger.info(f"Received parse_form request: url={url}, form_type={form_type}")
    try:
        # Validate inputs
        if not url or len(url) > 2000:
            logger.warning(f"Invalid URL: {url[:50]}...")
            return {
                "status": "error",
                "error": "URL is empty or exceeds maximum length of 2000 characters",
                "gemini_message": "",
                "form_schema": {},
                "questions": []
            }
        
        if form_type not in {'google', 'typeform', 'microsoft', 'custom'}:
            logger.warning(f"Invalid form type: {form_type}")
            return {
                "status": "error",
                "error": "Invalid form type. Must be one of: google, typeform, microsoft, custom",
                "gemini_message": "",
                "form_schema": {},
                "questions": []
            }

        # Use Gemini to validate the URL and form type
        prompt = f"""
        You are a web form expert. Validate the provided URL and form type.
        - Check if the URL appears to be a valid web form URL (e.g., starts with http:// or https://, points to a plausible domain).
        - Confirm if the form type matches the expected platform based on the URL or description.
        - For form_type, ensure it is one of: google, typeform, microsoft, custom.
        - If the form type is ambiguous, suggest the most likely type or default to 'custom'.
        Input: URL: {url}, Form Type: {form_type}
        Output format: {{ "url": "validated URL", "form_type": "validated form type", "is_valid": true/false, "message": "explanation" }}
        """
        logger.debug("Sending prompt to Gemini")
        gemini_response = model.generate_content(prompt)

        # Check Gemini response
        if not hasattr(gemini_response, 'text') or not gemini_response.text:
            logger.error("Invalid Gemini response: No text content")
            return {
                "status": "error",
                "error": "Invalid Gemini response: No text content",
                "gemini_message": "",
                "form_schema": {},
                "questions": []
            }

        # Extract and clean text
        gemini_data = gemini_response.text.strip()
        if gemini_data.startswith("```json"):
            gemini_data = gemini_data[7:].strip()
        if gemini_data.endswith("```"):
            gemini_data = gemini_data[:-3].strip()
        logger.debug(f"Cleaned Gemini response: {gemini_data}")

        # Parse Gemini response
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
                "questions": []
            }

        # Extract validated URL and form type
        validated_url = gemini_result.get("url")
        validated_form_type = gemini_result.get("form_type")
        if not validated_url or not gemini_result.get("is_valid"):
            logger.warning(f"Invalid input from Gemini: {gemini_result.get('message')}")
            return {
                "status": "error",
                "error": gemini_result.get("message", "Invalid input from Gemini"),
                "gemini_message": gemini_result.get("message", ""),
                "form_schema": {},
                "questions": []
            }

        # Initialize parser
        parser = FormParser(use_profile=(validated_form_type == 'microsoft'), debug_mode=True)
        logger.info(f"Initialized FormParser with use_profile={validated_form_type == 'microsoft'}, debug_mode=True")

        # Parse the form
        logger.info(f"Parsing form at URL: {validated_url}")
        form_schema = parser.parse_form_from_url(validated_url, validated_form_type)
        logger.info("Form parsed successfully")

        # Generate conversational questions
        questions = llm_conv.generate_questions(form_schema, context=f"Parsing a {validated_form_type} form from {validated_url}")

        # Save questions to a file
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
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error processing form at '{url}': {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "gemini_message": gemini_result.get("message", "") if 'gemini_result' in locals() else "",
            "form_schema": {},
            "questions": []
        }

# Define MCP tool for HTML content parsing
@mcp.tool()
def parse_html_form(html_input: str, is_file: bool = False) -> dict:
    """
    Parse a static HTML form from a string or file and return its schema.
    
    Args:
        html_input (str): HTML string or file path to HTML content.
        is_file (bool): If True, treat html_input as a file path; otherwise, treat as HTML string.
    
    Returns:
        dict: Parsed form schema, status, optional Gemini validation message, and conversational questions.
    """
    logger.info(f"Received parse_html_form request: is_file={is_file}")
    try:
        # Validate input
        if not html_input:
            logger.warning("Empty HTML input provided")
            return {
                "status": "error",
                "error": "HTML input cannot be empty",
                "gemini_message": "",
                "form_schema": {},
                "questions": []
            }

        # Optional Gemini validation for HTML content
        prompt = f"""
        You are a web form expert. Validate the provided HTML content to ensure it contains a valid form structure.
        - Check if the HTML includes at least one <form> tag with inputs (e.g., <input>, <select>, <textarea>).
        - If no <form> tag is found, check for form-like structures (e.g., <input> or <select> elements).
        - Return a message indicating whether the HTML is likely a valid form.
        Input: HTML: {html_input[:1000]}... (truncated for brevity)
        Output format: {{ "is_valid": true/false, "message": "explanation" }}
        """
        logger.debug("Sending HTML validation prompt to Gemini")
        gemini_response = model.generate_content(prompt)

        # Process Gemini response
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
                        "questions": []
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini response for HTML validation: {str(e)}")
                gemini_message = gemini_data

        # Initialize parser
        parser = FormParser(debug_mode=True)
        logger.info("Initialized FormParser for HTML parsing")

        # Parse the HTML content
        logger.info("Parsing HTML content")
        form_schema = parser.parse_html_content(html_input, is_file)
        logger.info("HTML parsed successfully")

        # Generate conversational questions
        questions = llm_conv.generate_questions(form_schema, context="Parsing a static HTML form")

        # Save questions to a file
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
            "questions": []
        }
    except Exception as e:
        logger.error(f"Server error parsing HTML: {str(e)}")
        return {
            "status": "error",
            "error": f"Server error: {str(e)}",
            "gemini_message": gemini_message if 'gemini_message' in locals() else "",
            "form_schema": {},
            "questions": []
        }

# Run the server
if __name__ == "__main__":
    try:
        logger.info("Starting FastMCP server with stdio transport")
        mcp.run(transport="stdio")
        logger.info("FastMCP server started successfully")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise