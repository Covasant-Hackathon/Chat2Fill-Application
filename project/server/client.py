import asyncio
import json
import time
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server details
SERVER_SCRIPT = "server.py"
URL_TOOL_NAME = "parse_form"
HTML_TOOL_NAME = "parse_html_form"

async def call_mcp_server(tool_name: str, params: dict, retries: int = 3) -> dict:
    """
    Send a request to the FastMCP server using the stdio transport.

    Args:
        tool_name (str): Name of the tool to call ('parse_form' or 'parse_html_form').
        params (dict): Parameters for the tool (e.g., {'url': ..., 'form_type': ...} or {'html_input': ..., 'is_file': ...}).
        retries (int): Number of retry attempts for connection failures.

    Returns:
        dict: Server response containing form schema, Gemini data, or error.
    """
    # Check if server script exists
    if not os.path.exists(SERVER_SCRIPT):
        logger.error(f"Server script {SERVER_SCRIPT} not found in the current directory.")
        return {
            "status": "error",
            "error": f"Server script {SERVER_SCRIPT} not found. Ensure it is in the correct directory."
        }

    client = None
    try:
        # Initialize FastMCP client
        from fastmcp.client import Client
        client = Client(SERVER_SCRIPT)
        logger.info(f"Connected to server via stdio transport: {client.transport}")

        # Use async context manager to connect to the server
        async with client:
            # Call the specified tool with parameters
            logger.debug(f"Calling tool {tool_name} with params: {params}")
            response = await client.call_tool(tool_name, params)
            logger.info("Received response from server")
            logger.debug(f"Raw response: {response}")

            # Handle response type
            if isinstance(response, list):
                logger.debug(f"Response is a list: {response}")
                if len(response) == 0:
                    return {
                        "status": "error",
                        "error": "Empty response list from server"
                    }
                response = response[0]  # Take the first element
                logger.info("Extracted first element from response list")

            # Handle TextContent object
            if hasattr(response, 'text'):  # Check for TextContent-like object
                logger.debug("Response is a TextContent object")
                try:
                    response_text = response.text.strip()
                    # Remove code block markers if present
                    if response_text.startswith("```json"):
                        response_text = response_text[7:].strip()
                    if response_text.endswith("```"):
                        response_text = response_text[:-3].strip()
                    response = json.loads(response_text)
                    logger.info("Parsed TextContent text to dictionary")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse TextContent text: {str(e)}")
                    return {
                        "status": "error",
                        "error": f"Failed to parse TextContent text: {str(e)}"
                    }

            # Ensure response is a dictionary
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return {
                    "status": "error",
                    "error": f"Unexpected response type: {type(response)}"
                }
            return response

    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        if attempt == retries - 1:
            return {
                "status": "error",
                "error": f"Failed to connect to server via stdio after {retries} attempts. Ensure {SERVER_SCRIPT} is accessible and running. Error: {str(e)}"
            }
        logger.info(f"Retrying ({attempt + 1}/{retries})...")
        time.sleep(1)
    finally:
        # Ensure client cleanup
        if client and hasattr(client, 'transport') and client.transport:
            try:
                client.transport.close()
                logger.debug("Closed client transport")
            except Exception as e:
                logger.warning(f"Error closing client transport: {str(e)}")

async def main():
    print("Welcome to the FastMCP Form Parser Client!")
    print("Choose an option to parse a form:")
    print("1. Parse a form from a URL (Google, Typeform, Microsoft, or custom)")
    print("2. Parse a static HTML form (paste HTML or provide file path)")
    print(f"Connecting to server via stdio: {SERVER_SCRIPT}")
    print("Type 'exit' to quit.")

    # Ensure event loop cleanup
    loop = asyncio.get_event_loop()
    try:
        while True:
            choice = input("\nEnter option (1 or 2) or 'exit' to quit: ").strip().lower()
            if choice == 'exit':
                print("Goodbye!")
                break

            if choice not in {'1', '2'}:
                print("Invalid choice. Please enter 1, 2, or 'exit'.")
                continue

            if choice == '1':
                # URL-based parsing
                url = input("\nEnter form URL: ").strip()
                if not url:
                    print("URL cannot be empty.")
                    continue

                form_type = input("Enter form type (google, typeform, microsoft, custom): ").strip().lower()
                if form_type not in {'google', 'typeform', 'microsoft', 'custom'}:
                    print("Invalid form type. Please choose one of: google, typeform, microsoft, custom")
                    continue

                logger.info(f"Processing URL request: url={url}, form_type={form_type}")
                result = await call_mcp_server(URL_TOOL_NAME, {"url": url, "form_type": form_type})
                output_file_prefix = "".join(c for c in url if c.isalnum() or c in "_-")[:50] or "form"

            else:
                # HTML-based parsing
                print("\nFor HTML Form, you can:")
                print("1. Paste HTML content directly")
                print("2. Provide a file path containing HTML")
                html_choice = input("Enter 1 or 2: ").strip()

                html_input = ""
                is_file = False
                if html_choice == '1':
                    print("Paste your HTML content (press Enter twice to finish):")
                    lines = []
                    while True:
                        line = input()
                        if line == "":
                            if lines and lines[-1] == "":
                                break
                            lines.append("")
                        else:
                            lines.append(line)
                    html_input = "\n".join(lines)
                elif html_choice == '2':
                    html_input = input("Enter the file path to the HTML file: ").strip()
                    is_file = True
                else:
                    print("Invalid choice. Please enter 1 or 2.")
                    continue

                if not html_input:
                    print("HTML input cannot be empty.")
                    continue

                logger.info(f"Processing HTML request: is_file={is_file}")
                result = await call_mcp_server(HTML_TOOL_NAME, {"html_input": html_input, "is_file": is_file})
                output_file_prefix = "html_form"

            # Process response
            print("\nResponse from server:")
            logger.debug(f"Result: {result}")

            if result.get("status") == "success":
                # Extract form schema and metadata
                form_schema = result.get("form_schema")
                gemini_message = result.get("gemini_message")
                output_file = f"{output_file_prefix}_schema.json"

                # Save form schema to JSON file
                try:
                    with open(output_file, "w", encoding='utf-8') as f:
                        json.dump(form_schema, f, indent=4, ensure_ascii=False)
                    print(f"Form schema saved: {output_file}")
                    if choice == '1':
                        print(f"Validated URL: {result.get('gemini_url')}")
                        print(f"Validated Form Type: {result.get('gemini_form_type')}")
                    if gemini_message:
                        print(f"Gemini Message: {gemini_message}")
                except Exception as e:
                    print(f"Error saving JSON file: {str(e)}")
            else:
                print(f"Error: {result.get('error')}")
                if result.get("gemini_message"):
                    print(f"Gemini Message: {result.get('gemini_message')}")
    finally:
        # Ensure event loop and transports are closed
        try:
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            logger.debug("Event loop closed")
        except Exception as e:
            logger.warning(f"Error closing event loop: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())