import json
import logging
import sys
import os
import platform
import time
import requests
from uuid import uuid4
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_default_chrome_paths() -> tuple[str, str, str]:
    """
    Detect default Chrome profile and binary paths based on the operating system.
    
    Returns:
        Tuple of (chrome_profile_path, chrome_profile_name, chrome_binary_path)
    """
    system = platform.system()
    username = os.getlogin() if system != "Darwin" else os.path.expanduser("~").split("/")[-1]
    
    profile_path = ""
    profile_name = "Default"
    binary_path = ""
    
    if system == "Windows":
        profile_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
        binary_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif system == "Darwin":  # macOS
        profile_path = f"/Users/{username}/Library/Application Support/Google/Chrome"
        binary_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        profile_path = f"/home/{username}/.config/google-chrome"
        binary_path = "/usr/bin/google-chrome"
    
    return profile_path, profile_name, binary_path

def load_config() -> tuple[str, str, str]:
    """
    Load Chrome profile and binary settings from config.json if available.
    
    Returns:
        Tuple of (chrome_profile_path, chrome_profile_name, chrome_binary_path)
    """
    config_file = "config.json"
    default_path, default_name, default_binary = get_default_chrome_paths()
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get("chrome_profile_path", default_path)
                name = config.get("chrome_profile_name", default_name)
                binary = config.get("chrome_binary_path", default_binary)
                if os.path.exists(path) and os.path.exists(binary):
                    return path, name, binary
                logger.warning(f"Invalid paths in config.json: profile={path}, binary={binary}. Using defaults.")
        except Exception as e:
            logger.warning(f"Error reading config.json: {str(e)}. Using defaults.")
    
    return default_path, default_name, default_binary

class FormParser:
    """A parser for extracting form structure from HTML, Google Forms, Typeform, Microsoft Forms, and custom web forms."""
    
    def __init__(self, use_profile: bool = False, debug_mode: bool = False):
        self.supported_input_types = {
            'text', 'number', 'email', 'date', 'tel', 'url', 'password',
            'radio', 'checkbox', 'select', 'textarea', 'file'
        }
        self.driver = None
        self.debug_mode = debug_mode
        self.chrome_profile_path, self.chrome_profile_name, self.chrome_binary_path = load_config()
        if use_profile and not os.path.exists(self.chrome_profile_path):
            logger.warning(f"Chrome profile path {self.chrome_profile_path} not found.")
            self.chrome_profile_path = ""
            self.chrome_profile_name = ""
        if not os.path.exists(self.chrome_binary_path):
            logger.warning(f"Chrome binary path {self.chrome_binary_path} not found. Selenium may fail.")
            self.chrome_binary_path = ""

    def save_debug_html(self, html_content: str, filename: str = "debug.html"):
        """Save the page HTML for debugging."""
        if self.debug_mode:
            with open(filename, "w", encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Debug HTML saved to {filename}")

    def parse_html_content(self, html_input: str, is_file: bool = False) -> Dict[str, Any]:
        """
        Parse static HTML content from a string or file.
        
        Args:
            html_input: HTML string or file path to HTML content
            is_file: If True, treat html_input as a file path; otherwise, treat as HTML string
            
        Returns:
            Dictionary containing parsed form metadata
            
        Raises:
            ValueError: If parsing fails or file is invalid
        """
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

    def parse_form_from_url(self, url: str, form_type: str) -> Dict[str, Any]:
        """
        Parse a form from a URL, delegating to the appropriate parser based on form type.
        
        Args:
            url: URL of the form
            form_type: Type of form ('google', 'typeform', 'microsoft', 'custom')
            
        Returns:
            Dictionary containing parsed form metadata
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            # Try static fetching for custom forms
            if form_type == 'custom':
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    html_content = response.text
                    soup = BeautifulSoup(html_content, 'lxml')
                    if soup.find('form'):
                        return self.parse_html(html_content)
                except requests.RequestException as e:
                    logger.info(f"Static fetch failed for custom form: {e}. Falling back to Selenium.")

            # Initialize Selenium driver
            service = Service(ChromeDriverManager().install())
            options = Options()
            options.add_argument("--disable-extensions")
            if self.chrome_binary_path:
                options.binary_location = self.chrome_binary_path
            if self.chrome_profile_path and form_type == "microsoft":
                options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
                options.add_argument(f"--profile-directory={self.chrome_profile_name}")
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info(f"Initialized WebDriver with binary: {self.chrome_binary_path}")
            self.driver.get(url)

            # Check for authentication redirect
            if "login" in self.driver.current_url.lower() and form_type == "microsoft":
                raise ValueError("Authentication required. Ensure you're logged into Microsoft in Chrome or provide a public form URL.")

            # Save debug HTML
            self.save_debug_html(self.driver.page_source, f"debug_{form_type}.html")

            # Delegate to appropriate parser
            if form_type == 'google':
                return self.parse_google_form(url)
            elif form_type == 'typeform':
                return self.parse_typeform(url)
            elif form_type == 'microsoft':
                return self.parse_microsoft_form(url)
            elif form_type == 'custom':
                return self.parse_custom_form(url)
            else:
                raise ValueError("Invalid form type")

        except TimeoutException as e:
            logger.error(f"Timeout while loading form at {url}: {str(e)}")
            raise ValueError(f"Failed to load form elements. The page may be slow or inaccessible.")
        except Exception as e:
            logger.error(f"Error parsing form from URL {url}: {str(e)}")
            raise ValueError(f"Failed to parse form: {str(e)}")
        
        finally:
            if self.driver:
                self.driver.quit()

    def parse_google_form(self, url: str) -> Dict[str, Any]:
        try:
            wait = WebDriverWait(self.driver, 30)
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            question_blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="listitem"]')))
            logger.info(f"Found {len(question_blocks)} question blocks")

            form_title = "Untitled Google Form"
            try:
                form_title_elem = self.driver.find_element(By.CSS_SELECTOR, 'div[jsname="r4nke"]')
                if form_title_elem:
                    form_title = form_title_elem.text.strip()
            except:
                pass

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label = block.text.strip().split("\n")[0] or f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    if block.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="email"], input[type="tel"], input[type="number"]'):
                        field_type = "text"
                    elif block.find_elements(By.TAG_NAME, "textarea"):
                        field_type = "paragraph"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="radio"], input[type="radio"]'):
                        field_type = "multiple_choice"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"], input[type="checkbox"]'):
                        field_type = "checkbox"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="listbox"], select'):
                        field_type = "dropdown"

                    try:
                        block.find_element(By.CSS_SELECTOR, 'span[aria-label="Required question"], span:contains("*")')
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
                        option_selectors = [
                            'div[role="presentation"] span',
                            'div[role="radio"] span',
                            'div[role="option"] span',
                            'label span',
                            'div.jNTOo span'
                        ]
                        options = []
                        for selector in option_selectors:
                            try:
                                option_elements = block.find_elements(By.CSS_SELECTOR, selector)
                                options = [opt.text.strip() for opt in option_elements if opt.text.strip() and opt.text.strip() != label]
                                if options:
                                    break
                            except:
                                continue
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in set(options)]
                            logger.info(f"Question {idx}: Found {len(options)} options: {options}")
                        else:
                            logger.warning(f"Question {idx}: No options found for {field_type}")

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Google Form Question {idx}: Error: {e}")

            self.save_debug_html(self.driver.page_source, f"debug_google_form_{str(uuid4())[:8]}.html")
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

        except TimeoutException as e:
            logger.error(f"Timeout while parsing Google Form: {str(e)}")
            raise ValueError("Failed to load Google Form elements. Ensure the URL is valid and accessible. Debug HTML saved.")
        except Exception as e:
            logger.error(f"Error parsing Google Form: {str(e)}")
            raise ValueError(f"Failed to parse Google Form: {str(e)}")

    def parse_typeform(self, url: str) -> Dict[str, Any]:
        try:
            wait = WebDriverWait(self.driver, 30)
            question_blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-qa="question"]')))
            
            form_title = "Untitled Typeform"
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, 'h1')
                if title_elem:
                    form_title = title_elem.text.strip()
            except:
                pass

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label = block.text.strip().split("\n")[0] or f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    if block.find_elements(By.TAG_NAME, "input"):
                        field_type = "text"
                    elif block.find_elements(By.TAG_NAME, "textarea"):
                        field_type = "paragraph"
                    elif block.find_elements(By.CSS_SELECTOR, 'input[type="radio"]'):
                        field_type = "multiple_choice"
                    elif block.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
                        field_type = "checkbox"
                    elif block.find_elements(By.TAG_NAME, "select"):
                        field_type = "dropdown"

                    try:
                        if block.find_element(By.CSS_SELECTOR, '[aria-required="true"]') or "*" in block.text:
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
                        option_elements = block.find_elements(By.CSS_SELECTOR, 'label, option')
                        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in set(options)]

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Typeform Question {idx}: Error: {e}")

            self.save_debug_html(self.driver.page_source, f"debug_typeform_{str(uuid4())[:8]}.html")
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

        except TimeoutException as e:
            logger.error(f"Timeout while parsing Typeform: {str(e)}")
            raise ValueError("Failed to load Typeform elements. Ensure the URL is valid and accessible. Debug HTML saved.")
        except Exception as e:
            logger.error(f"Error parsing Typeform: {str(e)}")
            raise ValueError(f"Failed to parse Typeform: {str(e)}")

    def parse_microsoft_form(self, url: str) -> Dict[str, Any]:
        try:
            wait = WebDriverWait(self.driver, 30)
            question_blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-automation-id="questionItem"]')))
            
            form_title = "Untitled Microsoft Form"
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, 'div[data-automation-id="formTitle"]')
                if title_elem:
                    form_title = title_elem.text.strip()
            except:
                pass

            fields_schema = []
            for idx, block in enumerate(question_blocks, 1):
                try:
                    label = block.text.strip().split("\n")[0] or f"Untitled Question {idx}"
                    field_type = "text"
                    is_required = False

                    if block.find_elements(By.TAG_NAME, "input"):
                        field_type = "text"
                    elif block.find_elements(By.TAG_NAME, "textarea"):
                        field_type = "paragraph"
                    elif block.find_elements(By.CSS_SELECTOR, 'input[type="radio"]'):
                        field_type = "multiple_choice"
                    elif block.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
                        field_type = "checkbox"
                    elif block.find_elements(By.TAG_NAME, "select"):
                        field_type = "dropdown"

                    try:
                        if block.find_element(By.CSS_SELECTOR, '[aria-required="true"]') or "*" in block.text:
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
                        option_elements = block.find_elements(By.CSS_SELECTOR, 'label, option')
                        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in set(options)]

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Microsoft Form Question {idx}: Error: {e}")

            self.save_debug_html(self.driver.page_source, f"debug_microsoft_{str(uuid4())[:8]}.html")
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

        except TimeoutException as e:
            logger.error(f"Timeout while parsing Microsoft Form: {str(e)}")
            raise ValueError("Failed to load Microsoft Form elements. Ensure you're logged in or use a public form URL. Debug HTML saved.")
        except Exception as e:
            logger.error(f"Error parsing Microsoft Form: {str(e)}")
            raise ValueError(f"Failed to parse Microsoft Form: {str(e)}")

    def parse_custom_form(self, url: str) -> Dict[str, Any]:
        try:
            wait = WebDriverWait(self.driver, 30)
            
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            html_content = None
            form_found = False

            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    if self.driver.find_elements(By.TAG_NAME, "form"):
                        html_content = self.driver.page_source
                        form_found = True
                        break
                    self.driver.switch_to.default_content()
                except Exception as e:
                    logger.debug(f"Iframe parsing error: {e}")
                    self.driver.switch_to.default_content()

            if not form_found:
                html_content = self.driver.page_source

            soup = BeautifulSoup(html_content, 'lxml')
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

        except TimeoutException as e:
            logger.error(f"Timeout while parsing custom form: {str(e)}")
            raise ValueError("Failed to load custom form elements. Ensure the URL is valid and accessible. Debug HTML saved.")
        except Exception as e:
            logger.error(f"Error parsing custom form: {str(e)}")
            raise ValueError(f"Failed to parse custom form: {str(e)}")

    def parse_html(self, html_content: str) -> Dict[str, Any]:
        try:
            soup = BeautifulSoup(html_content, 'lxml')
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

    def _parse_select_options(self, select: BeautifulSoup) -> List[Dict[str, str]]:
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
        """
        Convert parsed form data to JSON string with proper UTF-8 encoding.
        
        Args:
            data: Parsed form data dictionary
            pretty: If True, format JSON with indentation
            
        Returns:
            JSON string representation of the form data
        """
        try:
            if pretty:
                return json.dumps(data, indent=2, ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error converting to JSON: {str(e)}")
            raise ValueError(f"Failed to convert data to JSON: {str(e)}")

    def run_interactive(self):
        """Run the parser interactively for testing HTML or URL-based form parsing."""
        print("\n=== Form Parser ===")
        print("Select the type of form to parse:")
        print("1. HTML Form (paste HTML or provide file path)")
        print("2. Google Form (provide URL)")
        print("3. Typeform (provide URL)")
        print("4. Microsoft Form (provide URL)")
        print("5. Custom Web Form (provide URL)")
        debug_mode = input("\nEnable debug mode (saves HTML for troubleshooting)? [y/N]: ").strip().lower() == 'y'

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

                # Initialize parser
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

                    result = parser.parse_html_content(html_input, is_file)

                else:
                    url = input(f"\nEnter the {['HTML', 'Google Form', 'Typeform', 'Microsoft Form', 'Custom Web Form'][choice-1]} URL: ").strip()
                    if not url:
                        print("URL cannot be empty.")
                        continue
                    result = parser.parse_form_from_url(url, form_types[choice])

                # Output results
                print("\n=== Parsed Form Schema ===")
                json_output = parser.to_json(result)
                print(json_output)

                # Save to file
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
    FormParser().run_interactive()