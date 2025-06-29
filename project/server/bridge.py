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

# Request models for FastAPI
class FormRequest(BaseModel):
    url: str
    form_type: str

class HTMLRequest(BaseModel):
    html_input: str
    is_file: bool = False

@app.post("/parse_form")
async def parse_form_endpoint(request: FormRequest):
    """
    Receive HTTP POST request from React app to parse a form from a URL via FastMCP server.
    
    Args:
        request: FormRequest with url and form_type.
    
    Returns:
        dict: Parsed form schema, Gemini validation, questions, or error message.
    """
    url = request.url
    form_type = request.form_type
    logger.info(f"Received parse_form request: url={url}, form_type={form_type}")
    try:
        # Initialize FastMCP client to communicate with server.py
        client = Client("server.py")
        logger.info("Connected to FastMCP server via stdio")

        # Call the parse_form tool
        async with client:
            logger.debug(f"Calling tool parse_form with url: {url}, form_type: {form_type}")
            response = await client.call_tool("parse_form", {"url": url, "form_type": form_type})
            logger.info("Received response from server")

            # Handle response
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
                logger.info("Extracted first element from response list")

            # Handle TextContent-like object
            if hasattr(response, 'text'):
                try:
                    response_text = response.text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:].strip()
                    if response_text.endswith("```"):
                        response_text = response_text[:-3].strip()
                    response = json.loads(response_text)
                    logger.info("Parsed TextContent text to dictionary")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse TextContent text: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to parse response: {str(e)}")

            # Ensure response is a dictionary
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                raise HTTPException(status_code=500, detail=f"Unexpected response type: {type(response)}")

            return response
    except Exception as e:
        logger.error(f"Error processing parse_form request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        # Ensure client cleanup
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            try:
                await client.transport.close()
                logger.debug("Closed client transport")
            except Exception as e:
                logger.warning(f"Error closing client transport: {str(e)}")

@app.post("/parse_html_form")
async def parse_html_form_endpoint(request: HTMLRequest):
    """
    Receive HTTP POST request from React app to parse a static HTML form via FastMCP server.
    
    Args:
        request: HTMLRequest with html_input and is_file.
    
    Returns:
        dict: Parsed form schema, Gemini validation, questions, or error message.
    """
    html_input = request.html_input
    is_file = request.is_file
    logger.info(f"Received parse_html_form request: is_file={is_file}")
    try:
        # Initialize FastMCP client to communicate with server.py
        client = Client("server.py")
        logger.info("Connected to FastMCP server via stdio")

        # Call the parse_html_form tool
        async with client:
            logger.debug(f"Calling tool parse_html_form with html_input: {html_input[:50]}..., is_file: {is_file}")
            response = await client.call_tool("parse_html_form", {"html_input": html_input, "is_file": is_file})
            logger.info("Received response from server")

            # Handle response
            if isinstance(response, list):
                if len(response) == 0:
                    raise ValueError("Empty response list from server")
                response = response[0]
                logger.info("Extracted first element from response list")

            # Handle TextContent-like object
            if hasattr(response, 'text'):
                try:
                    response_text = response.text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:].strip()
                    if response_text.endswith("```"):
                        response_text = response_text[:-3].strip()
                    response = json.loads(response_text)
                    logger.info("Parsed TextContent text to dictionary")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse TextContent text: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to parse response: {str(e)}")

            # Ensure response is a dictionary
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                raise HTTPException(status_code=500, detail=f"Unexpected response type: {type(response)}")

            return response
    except Exception as e:
        logger.error(f"Error processing parse_html_form request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        # Ensure client cleanup
        if 'client' in locals() and hasattr(client, 'transport') and client.transport:
            try:
                await client.transport.close()
                logger.debug("Closed client transport")
            except Exception as e:
                logger.warning(f"Error closing client transport: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI bridge server")
    uvicorn.run(app, host="0.0.0.0", port=8000)