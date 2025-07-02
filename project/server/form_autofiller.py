import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CHROME_USER_DATA_DIR = os.environ.get("CHROME_USER_DATA_DIR", "")

# Directories for screenshots and logs
SCREENSHOT_DIR = "screenshots"
LOG_DIR = "autofill_logs"
for directory in [SCREENSHOT_DIR, LOG_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

class FormAutofiller:
    """Automates form filling using Playwright with persistent Chrome session."""

    def __init__(self, user_data_dir: str = CHROME_USER_DATA_DIR, headless: bool = False):
        self.user_data_dir = user_data_dir or self._get_default_user_data_dir()
        self.headless = headless
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright: Optional[Playwright] = None

    def _get_default_user_data_dir(self) -> str:
        """Get default Chrome user data directory based on OS."""
        system = os.name
        if system == "nt":  # Windows
            return os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
        elif system == "posix":  # macOS or Linux
            if os.uname().sysname == "Darwin":  # macOS
                return os.path.expanduser("~/Library/Application Support/Google/Chrome")
            else:  # Linux
                return os.path.expanduser("~/.config/google-chrome")
        raise ValueError("Unsupported operating system")

    async def initialize(self):
        """Initialize Playwright and browser context."""
        try:
            logger.info(f"Initializing Playwright with user data dir: {self.user_data_dir}")
            self.playwright = await async_playwright().start()
            if not os.path.exists(self.user_data_dir):
                raise ValueError(f"Chrome user data directory not found: {self.user_data_dir}")

            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=Path(self.user_data_dir),
                headless=self.headless,
                args=["--disable-extensions", "--no-sandbox"],
                viewport={"width": 1280, "height": 720}
            )
            self.page = await self.context.new_page()
            logger.info("Playwright initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {str(e)}")
            raise

    async def close(self):
        """Close Playwright context and browser."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Playwright context closed")
        except Exception as e:
            logger.error(f"Error closing Playwright: {str(e)}")

    async def autofill_form(self, url: str, form_schema: Dict[str, Any], responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Autofill a form at the given URL using the schema and response data."""
        result = {
            "status": "success",
            "filled_fields": [],
            "errors": [],
            "screenshots": [],
            "log_file": ""
        }
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            logger.info(f"Navigated to {url}")

            await self._wait_for_form()

            field_mappings = self._map_responses_to_fields(form_schema, responses)
            await self._fill_form_fields(field_mappings, result)
            await self._submit_form(result)

            screenshot_path = await self._capture_screenshot("final")
            result["screenshots"].append(screenshot_path)
            result["log_file"] = self._save_logs(result)

            return result

        except Exception as e:
            logger.error(f"Error autofilling form: {str(e)}")
            screenshot_path = await self._capture_screenshot("error")
            result["status"] = "error"
            result["errors"].append(str(e))
            result["screenshots"].append(screenshot_path)
            result["log_file"] = self._save_logs(result)
            return result

    def _map_responses_to_fields(self, form_schema: Dict[str, Any], responses: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Map conversation responses to form fields."""
        mappings = {}
        try:
            fields = form_schema.get("forms", [{}])[0].get("fields", [])
            response_dict = {r["field_id"]: r for r in responses if r.get("valid")}

            for field in fields:
                field_id = field.get("id")
                if field_id in response_dict:
                    response = response_dict[field_id]
                    mappings[field_id] = {
                        "field": field,
                        "value": response["value"],
                        "selector": self._get_field_selector(field)
                    }
                    logger.info(f"Mapped field {field.get('label')} to value {response['value']}")
                else:
                    logger.warning(f"No response found for field {field.get('label')}")
                    mappings[field_id] = {
                        "field": field,
                        "value": None,
                        "selector": self._get_field_selector(field)
                    }
            return mappings
        except Exception as e:
            logger.error(f"Error mapping responses: {str(e)}")
            return mappings

    def _get_field_selector(self, field: Dict[str, Any]) -> str:
        """Generate CSS selector for a field based on attributes."""
        field_id = field.get("id")
        name = field.get("name")
        label = field.get("label")
        field_type = field.get("type")

        if field_type in ["multiple_choice", "dropdown"]:
            return f"div[role='radiogroup'][aria-labelledby*='{field_id}'], div[role='listbox'][aria-labelledby*='{field_id}'], select[name='{name}']"
        if field_id:
            return f"#{field_id}"
        elif name:
            return f"[name='{name}']"
        elif label:
            return f"label:contains('{label}') + input, label:contains('{label}') input, input[aria-label*='{label}']"
        elif field_type in ["select", "textarea"]:
            return field_type
        return f"input[type='{field_type}']"

    async def _wait_for_form(self):
        """Wait for form elements to load, handling dynamic content."""
        try:
            await self.page.wait_for_selector("form, input, select, textarea, div[role='radiogroup']", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=20000)
            logger.info("Form elements loaded")
        except Exception as e:
            logger.warning(f"Form wait timeout: {str(e)}. Proceeding with available elements.")

    async def _fill_form_fields(self, mappings: Dict[str, Dict[str, Any]], result: Dict[str, Any]):
        """Fill form fields and handle multi-page forms."""
        current_page = 0
        while True:
            try:
                for field_id, mapping in mappings.items():
                    field = mapping["field"]
                    value = mapping["value"]
                    selector = mapping["selector"]

                    if value is None:
                        result["errors"].append(f"No value for field {field.get('label')}")
                        continue

                    try:
                        if field["type"] in ["text", "email", "number", "tel", "url", "password"]:
                            await self._fill_text_field(selector, value)
                        elif field["type"] == "textarea":
                            await self._fill_textarea(selector, value)
                        elif field["type"] == "select" or field["type"] == "dropdown":
                            await self._fill_select(selector, value, field.get("options", []))
                        elif field["type"] == "radio" or field["type"] == "multiple_choice":
                            await self._fill_multiple_choice(selector, value, field.get("options", []))
                        elif field["type"] == "checkbox":
                            await self._fill_checkbox(selector, value, field.get("options", []))
                        else:
                            result["errors"].append(f"Unsupported field type {field['type']} for {field.get('label')}")
                            continue

                        result["filled_fields"].append(field.get("label"))
                        logger.info(f"Filled field {field.get('label')} with value {value}")

                    except Exception as e:
                        logger.error(f"Error filling field {field.get('label')}: {str(e)}")
                        result["errors"].append(f"Failed to fill {field.get('label')}: {str(e)}")
                        screenshot_path = await self._capture_screenshot(f"field_error_{field_id}")
                        result["screenshots"].append(screenshot_path)

                next_button = await self._find_next_button()
                if not next_button:
                    break

                await next_button.click()
                current_page += 1
                logger.info(f"Navigated to form page {current_page}")
                await self._wait_for_form()
                await self._capture_screenshot(f"page_{current_page}")

            except Exception as e:
                logger.error(f"Error processing form page {current_page}: {str(e)}")
                result["errors"].append(f"Page {current_page} error: {str(e)}")
                break

    async def _fill_text_field(self, selector: str, value: str):
        """Fill a text-based input field."""
        await self.page.fill(selector, value)
        await self.page.wait_for_timeout(500)

    async def _fill_textarea(self, selector: str, value: str):
        """Fill a textarea field."""
        await self.page.fill(selector, value)
        await self.page.wait_for_timeout(500)

    async def _fill_select(self, selector: str, value: str, options: List[Dict[str, Any]]):
        """Fill a select/dropdown field."""
        for opt in options:
            if opt["text"] == value or opt["value"] == value:
                await self.page.select_option(selector, value=opt["value"])
                break
        await self.page.wait_for_timeout(500)

    async def _fill_multiple_choice(self, selector: str, value: str, options: List[Dict[str, Any]]):
        """Fill a multiple-choice (radio) field."""
        for opt in options:
            if opt["text"] == value or opt["value"] == value:
                radio_selector = f"{selector} div[role='radio'][data-value='{opt['value']}']"
                await self.page.click(radio_selector)
                break
        await self.page.wait_for_timeout(500)

    async def _fill_checkbox(self, selector: str, value: List[str], options: List[Dict[str, Any]]):
        """Fill a checkbox field with multiple selections."""
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",")]
        for opt in options:
            if opt["text"] in value or opt["value"] in value:
                checkbox_selector = f"{selector} div[role='checkbox'][data-value='{opt['value']}']"
                await self.page.check(checkbox_selector)
        await self.page.wait_for_timeout(500)

    async def _find_next_button(self) -> Optional[Any]:
        """Find the next or continue button for multi-page forms."""
        selectors = [
            "button:contains('Next')",
            "button:contains('Continue')",
            "input[type='submit'][value*='Next']",
            "button[aria-label*='Next']",
            "button[data-qa*='next']"
        ]
        for selector in selectors:
            try:
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    return button
            except:
                continue
        return None

    async def _submit_form(self, result: Dict[str, Any]):
        """Attempt to submit the form."""
        try:
            submit_button = await self.page.query_selector("input[type='submit'], button[type='submit'], button:contains('Submit')")
            if submit_button and await submit_button.is_visible():
                await submit_button.click()
                await self.page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("Form submitted successfully")
            else:
                logger.warning("No submit button found")
                result["errors"].append("No submit button found")
        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            result["errors"].append(f"Submit error: {str(e)}")

    async def _capture_screenshot(self, prefix: str) -> str:
        """Capture a screenshot for verification."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOT_DIR, f"{prefix}_{timestamp}.png")
            await self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return ""

    def _save_logs(self, result: Dict[str, Any]) -> str:
        """Save autofill logs to a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(LOG_DIR, f"autofill_{timestamp}.json")
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Logs saved: {log_file}")
            return log_file
        except Exception as e:
            logger.error(f"Error saving logs: {str(e)}")
            return ""

    async def verify_form(self, expected_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Verify filled form fields match expected values."""
        verification = {"status": "success", "mismatches": []}
        try:
            for field_id, mapping in expected_fields.items():
                field = mapping["field"]
                expected_value = mapping["value"]
                selector = mapping["selector"]

                try:
                    element = await self.page.query_selector(selector)
                    if not element:
                        verification["mismatches"].append(f"Field {field.get('label')} not found")
                        continue

                    actual_value = await element.input_value() if field["type"] not in ["select", "multiple_choice"] else await element.evaluate("el => el.getAttribute('data-value') || el.value")
                    if field["type"] == "checkbox":
                        actual_value = await element.evaluate("el => Array.from(document.querySelectorAll(`${selector}:checked`)).map(e => e.value)")
                        expected_value = expected_value if isinstance(expected_value, list) else [expected_value]

                    if actual_value != expected_value:
                        verification["mismatches"].append(f"Field {field.get('label')}: expected {expected_value}, got {actual_value}")
                except Exception as e:
                    verification["mismatches"].append(f"Verification error for {field.get('label')}: {str(e)}")

            if verification["mismatches"]:
                verification["status"] = "error"
            return verification
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            verification["status"] = "error"
            verification["mismatches"].append(f"General verification error: {str(e)}")
            return verification

# Testing Framework
async def test_form_autofiller():
    """Test suite for FormAutofiller."""
    autofiller = FormAutofiller(headless=True)
    await autofiller.initialize()

    sample_schema = {
        "forms": [{
            "fields": [
                {"id": "1", "label": "Full Name", "type": "text", "name": "full_name", "required": True},
                {"id": "2", "label": "Current Year", "type": "multiple_choice", "name": "current_year", "options": [
                    {"value": "1st Year", "text": "1st Year"},
                    {"value": "2nd Year", "text": "2nd Year"}
                ]}
            ]
        }]
    }
    sample_responses = [
        {"field_id": "1", "value": "John Doe", "valid": True},
        {"field_id": "2", "value": "1st Year", "valid": True}
    ]

    test_url = "https://docs.google.com/forms/d/e/1FAIpQLSeVEFaHd9zv0OTj_uqHcNHyTfVMQwDgCIu1IOedyhVYu63qIw/viewform"

    try:
        result = await autofiller.autofill_form(test_url, sample_schema, sample_responses)
        assert result["status"] == "success", f"Autofill failed: {result['errors']}"
        assert len(result["filled_fields"]) == 2, "Not all fields filled"
        assert result["screenshots"], "No screenshots captured"

        mappings = autofiller._map_responses_to_fields(sample_schema, sample_responses)
        verification = await autofiller.verify_form(mappings)
        assert verification["status"] == "success", f"Verification failed: {verification['mismatches']}"

        logger.info("All autofill tests passed")
    finally:
        await autofiller.close()

if __name__ == "__main__":
    asyncio.run(test_form_autofiller())