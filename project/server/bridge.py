import logging
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastmcp.client import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI setup
app = FastAPI(title="Form Parser Bridge")

# Enable CORS for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class FormRequest(BaseModel):
    url: str
    form_type: str
    language: str = "en"
    session_id: str

class HTMLRequest(BaseModel):
    html_input: str
    is_file: bool = False
    language: str = "en"
    session_id: str

class AutofillRequest(BaseModel):
    url: str
    form_schema: dict
    responses: list
    language: str = "en"

class ConversationRequest(BaseModel):
    session_id: str
    form_id: int
    language: str = "en"

class ResponseRequest(BaseModel):
    session_id: str
    conversation_id: int
    field_name: str
    response_text: str
    language: str = "en"

class NextQuestionRequest(BaseModel):
    session_id: str
    conversation_id: int
    language: str = "en"

# Existing parse_form endpoint
@app.post("/parse_form")
async def parse_form_endpoint(request: FormRequest):
    url = request.url
    form_type = request.form_type
    language = request.language
    session_id = request.session_id
    logger.info(f"Received parse_form request: url={url}, form_type={form_type}, language={language}, session_id={session_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("parse_form", {"url": url, "form_type": form_type, "language": language, "session_id": session_id})
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            if not isinstance(response, dict):
                raise HTTPException(status_code=500, detail=f"Unexpected response type: {type(response)}")
            return response
    except Exception as e:
        logger.error(f"Error processing parse_form request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

# Existing parse_html_form endpoint
@app.post("/parse_html_form")
async def parse_html_form_endpoint(request: HTMLRequest):
    html_input = request.html_input
    is_file = request.is_file
    language = request.language
    session_id = request.session_id
    logger.info(f"Received parse_html_form request: is_file={is_file}, language={language}, session_id={session_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("parse_html_form", {"html_input": html_input, "is_file": is_file, "language": language, "session_id": session_id})
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            if not isinstance(response, dict):
                raise HTTPException(status_code=500, detail=f"Unexpected response type: {type(response)}")
            return response
    except Exception as e:
        logger.error(f"Error processing parse_html_form request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

# New autofill_form endpoint
@app.post("/autofill_form")
async def autofill_form_endpoint(request: AutofillRequest):
    """
    Receive HTTP POST request to autofill a form via FastMCP server.

    Args:
        request: AutofillRequest with url, form_schema, responses, and language.

    Returns:
        dict: Autofill status, filled fields, errors, screenshots, and logs.
    """
    url = request.url
    form_schema = request.form_schema
    responses = request.responses
    language = request.language
    logger.info(f"Received autofill_form request: url={url}, language={language}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("autofill_form", {
                "url": url,
                "form_schema": form_schema,
                "responses": responses,
                "language": language
            })
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            if not isinstance(response, dict):
                raise HTTPException(status_code=500, detail=f"Unexpected response type: {type(response)}")
            return response
    except Exception as e:
        logger.error(f"Error processing autofill_form request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

# New conversational endpoints
@app.post("/start_conversation")
async def start_conversation_endpoint(request: ConversationRequest):
    """Start a new conversational form filling session."""
    logger.info(f"Starting conversation for session: {request.session_id}, form: {request.form_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("start_conversation", {
                "session_id": request.session_id,
                "form_id": request.form_id,
                "language": request.language
            })
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            return response
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

@app.post("/get_next_question")
async def get_next_question_endpoint(request: NextQuestionRequest):
    """Get the next question in the conversation."""
    logger.info(f"Getting next question for conversation: {request.conversation_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("get_next_question", {
                "session_id": request.session_id,
                "conversation_id": request.conversation_id,
                "language": request.language
            })
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            return response
    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

@app.post("/submit_response")
async def submit_response_endpoint(request: ResponseRequest):
    """Submit a user response to a conversation."""
    logger.info(f"Submitting response for conversation: {request.conversation_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("submit_user_response", {
                "session_id": request.session_id,
                "conversation_id": request.conversation_id,
                "field_name": request.field_name,
                "response_text": request.response_text,
                "language": request.language
            })
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            return response
    except Exception as e:
        logger.error(f"Error submitting response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

@app.get("/conversation_summary/{session_id}/{conversation_id}")
async def get_conversation_summary(session_id: str, conversation_id: int):
    """Get a summary of the completed conversation."""
    logger.info(f"Getting conversation summary for: {conversation_id}")
    try:
        client = Client("server.py")
        async with client:
            response = await client.call_tool("get_conversation_summary", {
                "session_id": session_id,
                "conversation_id": conversation_id
            })
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
            if hasattr(response, 'text'):
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                response = json.loads(response_text)
            return response
    except Exception as e:
        logger.error(f"Error getting conversation summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            await client.transport.close()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI bridge server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
