import os
import json
import logging
import sys
import platform
import time
import threading
import asyncio
from uuid import uuid4
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page
from pathlib import Path
from dotenv import load_dotenv
import re
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CHROME_USER_DATA_DIR = os.environ.get("CHROME_USER_DATA_DIR", "")

# Directory for debug files
DEBUG_DIR = "debug_html"
if not os.path.exists(DEBUG_DIR):
    os.makedirs(DEBUG_DIR)

def cleanup_debug_files():
    """Run in a background thread to delete debug HTML files older than 24 hours."""
    while True:
        try:
            now = time.time()
            for filename in os.listdir(DEBUG_DIR):
                file_path = os.path.join(DEBUG_DIR, filename)
                if os.path.isfile(file_path) and filename.startswith("debug_") and filename.endswith(".html"):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 24 * 3600:
                        os.remove(file_path)
                        logger.info(f"Deleted old debug file: {file_path}")
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Error during debug file cleanup: {str(e)}")
            time.sleep(3600)

cleanup_thread = threading.Thread(target=cleanup_debug_files, daemon=True)
cleanup_thread.start()

def get_default_chrome_paths() -> tuple[str, str]:
    """Detect default Chrome user data directory based on the operating system."""
    system = platform.system()
    username = os.getlogin() if system != "Darwin" else os.path.expanduser("~").split("/")[-1]

    profile_path = ""
    if system == "Windows":
        profile_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
    elif system == "Darwin":
        profile_path = f"/Users/{username}/Library/Application Support/Google/Chrome"
    elif system == "Linux":
        profile_path = f"/home/{username}/.config/google-chrome"

    return profile_path, "Default"

def load_config() -> tuple[str, str]:
    """Load Chrome profile settings from config.json or use defaults."""
    config_file = "config.json"
    default_path, default_name = get_default_chrome_paths()

    env_profile_path = CHROME_USER_DATA_DIR
    if env_profile_path and os.path.exists(env_profile_path):
        logger.info(f"Using CHROME_USER_DATA_DIR from .env: {env_profile_path}")
        return env_profile_path, "Default"

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get("chrome_profile_path", default_path)
                name = config.get("chrome_profile_name", default_name)
                if os.path.exists(path):
                    logger.info(f"Using profile path from config.json: {path}")
                    return path, name
                logger.warning(f"Invalid profile path in config.json: {path}. Using defaults.")
        except Exception as e:
            logger.warning(f"Error reading config.json: {str(e)}. Using defaults.")

    logger.info(f"Using default profile path: {default_path}")
    return default_path, default_name

class FormParser:
    """A parser for extracting form structure using Playwright."""

    def __init__(self, use_profile: bool = False, debug_mode: bool = False):
        self.supported_input_types = {
            'text', 'number', 'email', 'date', 'tel', 'url', 'password',
            'radio', 'checkbox', 'select', 'textarea', 'file'
        }
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.debug_mode = debug_mode
        self.chrome_profile_path, self.chrome_profile_name = load_config() if use_profile else ("", "Default")
        if use_profile and not os.path.exists(self.chrome_profile_path):
            logger.warning(f"Chrome profile path {self.chrome_profile_path} not found. Falling back to no profile.")
            self.chrome_profile_path = ""

    def save_debug_html(self, html_content: str, filename: str = "debug.html"):
        """Save the page HTML for debugging."""
        if self.debug_mode:
            file_path = os.path.join(DEBUG_DIR, filename)
            try:
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"Debug HTML saved to {file_path}")
            except Exception as e:
                logger.error(f"Error saving debug HTML to {file_path}: {str(e)}")

    async def initialize(self):
        """Initialize Playwright and browser context."""
        try:
            logger.info(f"Initializing Playwright with profile: {self.chrome_profile_path or 'no profile'}")
            self.playwright = await async_playwright().start()
            if self.chrome_profile_path:
                try:
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=Path(self.chrome_profile_path),
                        headless=False,
                        args=["--disable-extensions", "--no-sandbox"],
                        viewport={"width": 1280, "height": 720}
                    )
                    logger.info(f"Using persistent context with profile: {self.chrome_profile_path}")
                except Exception as e:
                    logger.warning(f"Failed to use profile {self.chrome_profile_path}: {str(e)}. Falling back to new context.")
                    browser = await self.playwright.chromium.launch(headless=False)
                    self.context = await browser.new_context(viewport={"width": 1280, "height": 720})
            else:
                browser = await self.playwright.chromium.launch(headless=False)
                self.context = await browser.new_context(viewport={"width": 1280, "height": 720})
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

    async def parse_html_content(self, html_input: str, is_file: bool = False) -> Dict[str, Any]:
        """Parse static HTML content from a string or file."""
        try:
            html_content = ""
            if is_file:
                if not os.path.exists(html_input):
                    raise ValueError(f"HTML file {html_input} does not exist")
                with open(html_input, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            else:
                html_content = html_input.strip()
                if not html_content:
                    raise ValueError("HTML content cannot be empty")

            result = self.parse_html(html_content)
            self.save_debug_html(html_content, f"debug_html_{str(uuid4())[:8]}.html")
            return result
        except Exception as e:
            logger.error(f"Error parsing HTML content: {str(e)}")
            raise ValueError(f"Failed to parse HTML content: {str(e)}")

    async def parse_form_from_url(self, url: str, form_type: str) -> Dict[str, Any]:
        """Parse a form from a URL using Playwright."""
        try:
            await self.initialize()
            # Try static fetching for custom forms
            if form_type == 'custom':
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    html_content = response.text
                    soup = self._create_soup(html_content)
                    if soup.find('form'):
                        return self.parse_html(html_content)
                except requests.RequestException as e:
                    logger.info(f"Static fetch failed for custom form: {e}. Falling back to Playwright.")

            # Navigate to URL
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if "login" in self.page.url.lower() and form_type == "microsoft":
                raise ValueError("Authentication required. Ensure you're logged into Microsoft in Chrome or provide a public form URL.")

            # Wait for form elements with increased timeout
            await self.page.wait_for_selector("form, input, select, textarea, div[role='radiogroup']", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=20000)

            html_content = await self.page.content()
            self.save_debug_html(html_content, f"debug_{form_type}_{str(uuid4())[:8]}.html")

            # Delegate to appropriate parser
            if form_type == 'google':
                return await self.parse_google_form(url)
            elif form_type == 'typeform':
                return await self.parse_typeform(url)
            elif form_type == 'microsoft':
                return await self.parse_microsoft_form(url)
            elif form_type == 'custom':
                return await self.parse_custom_form(url)
            else:
                raise ValueError("Invalid form type")

        except Exception as e:
            logger.error(f"Error parsing form from URL {url}: {str(e)}")
            raise ValueError(f"Failed to parse form: {str(e)}")
        finally:
            await self.close()

    def _create_soup(self, html_content: str) -> BeautifulSoup:
        """Create a BeautifulSoup object with lxml parser or fallback."""
        try:
            return BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            logger.warning(f"Failed to use lxml parser: {str(e)}. Falling back to html.parser.")
            return BeautifulSoup(html_content, 'html.parser')

    async def parse_google_form(self, url: str) -> Dict[str, Any]:
        try:
            # Scroll to load all questions
            for _ in range(5):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

            # Get form title
            form_title = "Untitled Google Form"
            try:
                title_elem = await self.page.query_selector('div[jsname="r4nke"]')
                if title_elem:
                    form_title = await title_elem.inner_text()
                    form_title = form_title.strip()
            except:
                pass

            # Get question blocks
            question_blocks = await self.page.query_selector_all('div[role="listitem"]')
            logger.info(f"Found {len(question_blocks)} question blocks")

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label_elem = await block.query_selector('span.M7eMe')
                    label = (await label_elem.inner_text()).strip().split("\n")[0] or f"Untitled Question {idx}" if label_elem else f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    # Improved field type detection
                    if await block.query_selector('div[role="radiogroup"]'):
                        field_type = "multiple_choice"  # Prioritize radiogroup for Google Forms dropdowns
                    elif await block.query_selector('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="date"]'):
                        field_type = "text"
                    elif await block.query_selector("textarea"):
                        field_type = "paragraph"
                    elif await block.query_selector('input[type="checkbox"], div[role="checkbox"]'):
                        field_type = "checkbox"
                    elif await block.query_selector('select, div[role="listbox"], div[data-type="dropdown"]'):
                        field_type = "dropdown"

                    # Check if required
                    try:
                        if await block.query_selector('span[aria-label="Required question"], span:contains("*"), div[aria-required="true"]'):
                            is_required = True
                    except:
                        is_required = False

                    field = {
                        "id": str(uuid4()),
                        "name": label.lower().replace(" ", "_").replace("/", "_").replace(".", ""),
                        "type": field_type,
                        "label": label,
                        "required": is_required,
                        "validation": {"required": is_required} if is_required else {}
                    }

                    # Enhanced option extraction
                    if field_type in ["multiple_choice", "dropdown", "checkbox"]:
                        option_selectors = [
                            'div[role="radio"]',  # Primary for radiogroup-based dropdowns
                            'div[role="option"]',
                            'div.ss-choice-item',
                            'select option',
                            'label span.aDTYNe',
                            'div.nWQGrd span.aDTYNe',  # Specific to Google Forms options
                            'div[role="presentation"] div:not(:has(span:contains("*")))'
                        ]
                        options = []
                        for selector in option_selectors:
                            try:
                                option_elements = await block.query_selector_all(selector)
                                for opt in option_elements:
                                    opt_text = (await opt.inner_text()).strip()
                                    opt_value = await opt.evaluate('(el) => el.getAttribute("data-value")') or opt_text
                                    if opt_text and opt_text != label and opt_text not in options and opt_text != "Other:" and opt_value != "__other_option__":
                                        options.append(opt_value)
                                if options:
                                    break
                            except Exception as e:
                                logger.debug(f"Option selector {selector} failed for {label}: {e}")
                                continue
                        if options:
                            field["options"] = [
                                {"value": opt, "text": opt, "selected": False, "disabled": False}
                                for opt in sorted(set(options))
                            ]
                            logger.info(f"Question {idx} ({label}): Found {len(options)} options: {options}")
                        else:
                            logger.warning(f"Question {idx} ({label}): No options found for {field_type}")

                        # Handle "Other" option
                        if await block.query_selector('div[role="radio"][data-value="__other_option__"]'):
                            field["options"].append({
                                "value": "Other",
                                "text": "Other",
                                "selected": False,
                                "disabled": False
                            })
                            logger.info(f"Question {idx} ({label}): Added 'Other' option")

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Google Form Question {idx} ({label}): Error: {e}")

            return {
                "forms": [{
                    "id": str(uuid4()),
                    "name": form_title.lower().replace(" ", "_"),
                    "action": url,
                    "method": "POST",
                    "fieldsets": [],
                    "fields": fields_schema
                }]
            }

        except Exception as e:
            logger.error(f"Error parsing Google Form: {str(e)}")
            raise ValueError(f"Failed to parse Google Form: {str(e)}")

    async def parse_typeform(self, url: str) -> Dict[str, Any]:
        try:
            question_blocks = await self.page.query_selector_all('[data-qa="question"]')
            form_title = "Untitled Typeform"
            try:
                title_elem = await self.page.query_selector('h1')
                if title_elem:
                    form_title = (await title_elem.inner_text()).strip()
            except:
                pass

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label = (await block.inner_text()).strip().split("\n")[0] or f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    if await block.query_selector("input"):
                        field_type = "text"
                    elif await block.query_selector("textarea"):
                        field_type = "paragraph"
                    elif await block.query_selector('input[type="radio"], div[role="radio"]'):
                        field_type = "multiple_choice"
                    elif await block.query_selector('input[type="checkbox"], div[role="checkbox"]'):
                        field_type = "checkbox"
                    elif await block.query_selector("select, div[role='listbox']"):
                        field_type = "dropdown"

                    try:
                        if await block.query_selector('[aria-required="true"]') or "*" in (await block.inner_text()):
                            is_required = True
                    except:
                        is_required = False

                    field = {
                        "id": str(uuid4()),
                        "name": label.lower().replace(" ", "_"),
                        "type": field_type,
                        "label": label,
                        "required": is_required,
                        "validation": {"required": is_required} if is_required else {}
                    }

                    if field_type in ["multiple_choice", "dropdown", "checkbox"]:
                        option_elements = await block.query_selector_all('label, option, div[role="radio"], div[role="option"]')
                        options = [await opt.inner_text() for opt in option_elements if (await opt.inner_text()).strip()]
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in sorted(set(options))]

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Typeform Question {idx}: Error: {e}")

            return {
                "forms": [{
                    "id": str(uuid4()),
                    "name": form_title.lower().replace(" ", "_"),
                    "action": url,
                    "method": "POST",
                    "fieldsets": [],
                    "fields": fields_schema
                }]
            }

        except Exception as e:
            logger.error(f"Error parsing Typeform: {str(e)}")
            raise ValueError(f"Failed to parse Typeform: {str(e)}")

    async def parse_microsoft_form(self, url: str) -> Dict[str, Any]:
        try:
            question_blocks = await self.page.query_selector_all('div[data-automation-id="questionItem"]')
            form_title = "Untitled Microsoft Form"
            try:
                title_elem = await self.page.query_selector('div[data-automation-id="formTitle"]')
                if title_elem:
                    form_title = (await title_elem.inner_text()).strip()
            except:
                pass

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label = (await block.inner_text()).strip().split("\n")[0] or f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    if await block.query_selector("input"):
                        field_type = "text"
                    elif await block.query_selector("textarea"):
                        field_type = "paragraph"
                    elif await block.query_selector('input[type="radio"], div[role="radio"]'):
                        field_type = "multiple_choice"
                    elif await block.query_selector('input[type="checkbox"], div[role="checkbox"]'):
                        field_type = "checkbox"
                    elif await block.query_selector("select, div[role='listbox']"):
                        field_type = "dropdown"

                    try:
                        if await block.query_selector('[aria-required="true"]') or "*" in (await block.inner_text()):
                            is_required = True
                    except:
                        is_required = False

                    field = {
                        "id": str(uuid4()),
                        "name": label.lower().replace(" ", "_"),
                        "type": field_type,
                        "label": label,
                        "required": is_required,
                        "validation": {"required": is_required} if is_required else {}
                    }

                    if field_type in ["multiple_choice", "dropdown", "checkbox"]:
                        option_elements = await block.query_selector_all('label, option, div[role="radio"], div[role="option"]')
                        options = [await opt.inner_text() for opt in option_elements if (await opt.inner_text()).strip()]
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in sorted(set(options))]

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Microsoft Form Question {idx}: Error: {e}")

            return {
                "forms": [{
                    "id": str(uuid4()),
                    "name": form_title.lower().replace(" ", "_"),
                    "action": url,
                    "method": "POST",
                    "fieldsets": [],
                    "fields": fields_schema
                }]
            }

        except Exception as e:
            logger.error(f"Error parsing Microsoft Form: {str(e)}")
            raise ValueError(f"Failed to parse Microsoft Form: {str(e)}")

    async def parse_custom_form(self, url: str) -> Dict[str, Any]:
        try:
            iframes = await self.page.query_selector_all("iframe")
            html_content = None
            form_found = False

            for iframe in iframes:
                try:
                    frame = iframe.content_frame()
                    if frame and await frame.query_selector("form"):
                        html_content = await frame.content()
                        form_found = True
                        break
                except Exception as e:
                    logger.debug(f"Iframe parsing error: {e}")

            if not form_found:
                html_content = await self.page.content()

            soup = self._create_soup(html_content)
            form_elements = soup.find_all('form')

            if form_elements:
                return self.parse_html(html_content)

            logger.warning("No <form> tags found. Attempting heuristic parsing...")
            fields_schema = []
            inputs = soup.find_all(['input', 'select', 'textarea'])
            for idx, input_elem in enumerate(inputs, 1):
                try:
                    field_data = self._parse_field(input_elem)
                    if field_data:
                        fields_schema.append(field_data)
                except Exception as e:
                    logger.warning(f"Custom Form Field {idx}: Error: {e}")

            form_title = soup.find('title').text.strip() if soup.find('title') else "Untitled Custom Form"
            self.save_debug_html(html_content, f"debug_custom_{str(uuid4())[:8]}.html")
            return {
                "forms": [{
                    "id": str(uuid4()),
                    "name": form_title.lower().replace(" ", "_"),
                    "action": url,
                    "method": "POST",
                    "fieldsets": [],
                    "fields": fields_schema
                }]
            }

        except Exception as e:
            logger.error(f"Error parsing custom form: {str(e)}")
            raise ValueError(f"Failed to parse custom form: {str(e)}")

    def parse_html(self, html_content: str) -> Dict[str, Any]:
        try:
            soup = self._create_soup(html_content)
            forms = soup.find_all('form')
            if not forms:
                logger.warning("No forms found in the provided HTML")
                return {"forms": []}

            result = {
                "forms": [self._parse_form(form) for form in forms]
            }
            return result
        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
            raise ValueError(f"Failed to parse HTML: {str(e)}")

    def _parse_form(self, form: BeautifulSoup) -> Dict[str, Any]:
        form_id = form.get('id', str(uuid4()))
        form_name = form.get('name', '')
        action = form.get('action', '')
        method = form.get('method', 'GET').upper()

        fieldsets = self._parse_fieldsets(form)
        fields = self._parse_fields(form, exclude_fieldsets=True)

        return {
            "id": form_id,
            "name": form_name,
            "action": action,
            "method": method,
            "fieldsets": fieldsets,
            "fields": fields
        }

    def _parse_fieldsets(self, parent: BeautifulSoup) -> List[Dict[str, Any]]:
        fieldsets = []
        for fieldset in parent.find_all('fieldset', recursive=False):
            fieldset_id = fieldset.get('id', str(uuid4()))
            legend = fieldset.find('legend')
            fields = self._parse_fields(fieldset)
            nested_fieldsets = self._parse_fieldsets(fieldset)

            fieldsets.append({
                "id": fieldset_id,
                "legend": legend.get_text(strip=True) if legend else '',
                "fields": fields,
                "fieldsets": nested_fieldsets
            })
        return fieldsets

    def _parse_fields(self, parent: BeautifulSoup, exclude_fieldsets: bool = False) -> List[Dict[str, Any]]:
        fields = []
        for input_elem in parent.find_all(['input', 'select', 'textarea'], recursive=not exclude_fieldsets):
            field_data = self._parse_field(input_elem)
            if field_data:
                fields.append(field_data)
        return fields

    def _parse_field(self, element: BeautifulSoup) -> Optional[Dict[str, Any]]:
        tag_name = element.name.lower()
        field_type = element.get('type', tag_name).lower()

        if field_type not in self.supported_input_types and tag_name not in {'select', 'textarea'}:
            logger.debug(f"Unsupported field type: {field_type}")
            return None

        field_data = {
            "id": element.get('id', str(uuid4())),
            "name": element.get('name', ''),
            "type": field_type,
            "required": element.get('required') is not None,
            "disabled": element.get('disabled') is not None,
            "label": self._find_label(element),
            "validation": self._extract_validation(element)
        }

        if tag_name == 'select':
            field_data['options'] = self._parse_select_options(element)
            field_data['multiple'] = element.get('multiple') is not None
        elif field_type in {'radio', 'checkbox'}:
            field_data['value'] = element.get('value', '')
        elif tag_name == 'textarea':
            field_data['rows'] = element.get('rows')
            field_data['cols'] = element.get('cols')
        else:
            field_data.update({
                'value': element.get('value', ''),
                'placeholder': element.get('placeholder', ''),
                'pattern': element.get('pattern', '')
            })

        return field_data

    def _find_label(self, element: BeautifulSoup) -> str:
        if element.get('id'):
            label = element.find_parent('form').find('label', {'for': element.get('id')}) if element.find_parent('form') else None
            if label:
                return label.get_text(strip=True)
        parent_label = element.find_parent('label')
        if parent_label:
            return parent_label.get_text(strip=True)
        if element.get('aria-label'):
            return element.get('aria-label')
        return f"Untitled Field {str(uuid4())[:8]}"

    def _parse_select_options(self, select: BeautifulSoup) -> List[Dict[str, Any]]:
        options = []
        for option in select.find_all('option'):
            options.append({
                'value': option.get('value', option.get_text(strip=True)),
                'text': option.get_text(strip=True),
                'selected': option.get('selected') is not None,
                'disabled': option.get('disabled') is not None
            })
        return options

    def _extract_validation(self, element: BeautifulSoup) -> Dict[str, Any]:
        validation = {}
        if element.get('required') is not None:
            validation['required'] = True
        if element.get('pattern'):
            validation['pattern'] = element.get('pattern')
        if element.get('min'):
            validation['min'] = element.get('min')
        if element.get('max'):
            validation['max'] = element.get('max')
        if element.get('minlength'):
            validation['minlength'] = element.get('minlength')
        if element.get('maxlength'):
            validation['maxlength'] = element.get('maxlength')
        return validation

    def to_json(self, data: Dict[str, Any], pretty: bool = True) -> str:
        """Convert parsed form data to JSON string."""
        try:
            if pretty:
                return json.dumps(data, indent=2, ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error converting to JSON: {str(e)}")
            raise ValueError(f"Failed to convert data to JSON: {str(e)}")

    async def run_interactive(self):
        """Run the parser interactively for testing."""
        print("\n=== Form Parser ===")
        print("Select the type of form to parse:")
        print("1. HTML Form (paste HTML or provide file path)")
        print("2. Google Form (provide URL)")
        print("3. Typeform (provide URL)")
        print("4. Microsoft Form (provide URL)")
        print("5. Custom Web Form (provide URL)")
        debug_mode = input("\nEnable debug mode? [y/N]: ").strip().lower() == 'y'

        while True:
            try:
                choice = input("\nEnter the number (1-5) or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    print("Exiting...")
                    break

                if not choice.isdigit() or int(choice) not in range(1, 6):
                    print("Invalid choice. Please enter a number between 1 and 5, or 'q' to quit.")
                    continue

                choice = int(choice)
                form_types = {2: 'google', 3: 'typeform', 4: 'microsoft', 5: 'custom'}
                output_file = f"parsed_{['html', 'google', 'typeform', 'microsoft', 'custom'][choice-1]}_form.json"

                parser = FormParser(use_profile=(choice == 4), debug_mode=debug_mode)
                if choice == 4 and parser.chrome_profile_path:
                    print(f"\nUsing Chrome profile: {parser.chrome_profile_path}\\{parser.chrome_profile_name}")
                    print("Ensure you are logged into your Microsoft account in Chrome.")

                if choice == 1:
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

                    result = await parser.parse_html_content(html_input, is_file)

                else:
                    url = input(f"\nEnter the {['HTML', 'Google Form', 'Typeform', 'Microsoft Form', 'Custom Web Form'][choice-1]} URL: ").strip()
                    if not url:
                        print("URL cannot be empty.")
                        continue
                    result = await parser.parse_form_from_url(url, form_types[choice])

                print("\n=== Parsed Form Schema ===")
                json_output = parser.to_json(result)
                print(json_output)

                with open(output_file, "w", encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"\nSchema saved to {output_file}")

            except ValueError as e:
                print(f"Error: {str(e)}")
                if debug_mode:
                    print(f"Check debug HTML file (e.g., debug_html_*.html) for the page structure.")
                print("Please try again.")
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                if debug_mode:
                    print(f"Check debug HTML file (e.g., debug_html_*.html) for the page structure.")
                print("Please try again.")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(FormParser().run_interactive())
