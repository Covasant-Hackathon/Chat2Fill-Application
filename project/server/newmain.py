import json
import logging
import sys
import time
from uuid import uuid4
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FormParser:
    """A parser for extracting form structure from HTML, Google Forms, Typeform, Microsoft Forms, and custom web forms."""
    
    def __init__(self):
        self.supported_input_types = {
            'text', 'number', 'email', 'date', 'tel', 'url', 'password',
            'radio', 'checkbox', 'select', 'textarea', 'file'
        }
        self.driver = None

    def parse_form_from_url(self, url: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Parse a form from a URL, detecting the form type and delegating to the appropriate parser.
        
        Args:
            url: URL of the form
            max_retries: Number of retry attempts for transient errors
            
        Returns:
            Dictionary containing parsed form metadata
            
        Raises:
            ValueError: If parsing fails after retries
        """
        for attempt in range(max_retries + 1):
            try:
                # Initialize Selenium driver
                service = Service(ChromeDriverManager().install())
                options = Options()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                # options.add_argument("--headless")  # Uncomment for headless mode
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.get(url)
                time.sleep(2)  # Wait for page to stabilize

                # Detect form type based on URL
                if "google.com/forms" in url.lower():
                    return self.parse_google_form(url)
                elif "typeform.com" in url.lower():
                    return self.parse_typeform(url)
                elif "forms.office.com" in url.lower() or "forms.microsoft.com" in url.lower() or "forms.cloud.microsoft" in url.lower():
                    return self.parse_microsoft_form(url)
                else:
                    return self.parse_custom_form(url)

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for URL {url}: {str(e)}")
                if attempt == max_retries:
                    logger.error(f"Error parsing form from URL {url}: {str(e)}")
                    raise ValueError(f"Failed to parse form: {str(e)}")
                time.sleep(1)  # Wait before retrying
            
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None

    def parse_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse static HTML content and extract form metadata.
        
        Args:
            html_content: HTML string containing one or more forms
            
        Returns:
            Dictionary containing parsed form metadata
        """
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

    def parse_google_form(self, url: str) -> Dict[str, Any]:
        """
        Parse a Google Form from a URL.
        
        Args:
            url: Google Form URL
            
        Returns:
            Dictionary containing parsed form metadata
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            question_blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="listitem"]')))
            
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

                    if block.find_elements(By.TAG_NAME, "input"):
                        field_type = "text"
                    elif block.find_elements(By.TAG_NAME, "textarea"):
                        field_type = "paragraph"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="radio"]'):
                        field_type = "multiple_choice"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]'):
                        field_type = "checkbox"
                    elif block.find_elements(By.CSS_SELECTOR, 'div[role="listbox"]'):
                        field_type = "dropdown"

                    try:
                        block.find_element(By.CSS_SELECTOR, 'span[aria-label="Required question"]')
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
                        option_elements = block.find_elements(By.CSS_SELECTOR, '[role="presentation"]')
                        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]
                        if options:
                            field["options"] = [{"value": opt, "text": opt, "selected": False, "disabled": False} for opt in set(options)]

                    fields_schema.append(field)

                except Exception as e:
                    logger.warning(f"Google Form Question {idx}: Error: {e}")

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

    def parse_typeform(self, url: str) -> Dict[str, Any]:
        """
        Parse a Typeform from a URL.
        
        Args:
            url: Typeform URL
            
        Returns:
            Dictionary containing parsed form metadata
        """
        try:
            wait = WebDriverWait(self.driver, 15)
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

    def parse_microsoft_form(self, url: str) -> Dict[str, Any]:
        """
        Parse a Microsoft Form from a URL.
        
        Args:
            url: Microsoft Form URL
            
        Returns:
            Dictionary containing parsed form metadata
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            # Check for login page
            try:
                login_elem = wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
                logger.warning("Login prompt detected. Form may require authentication.")
                return {"forms": []}  # Skip if login is required
            except:
                pass

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

    def parse_custom_form(self, url: str) -> Dict[str, Any]:
        """
        Parse a custom web form from a URL, handling iframes and <form> tags.
        
        Args:
            url: URL of the custom web form
            
        Returns:
            Dictionary containing parsed form metadata
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # Check for iframes
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

            # If no form found in iframes, use main page
            if not form_found:
                html_content = self.driver.page_source

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            form_elements = soup.find_all('form')

            if form_elements:
                return self.parse_html(html_content)

            # Fallback: Heuristic parsing for form-like structures
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

    def _parse_form(self, form: BeautifulSoup) -> Dict[str, Any]:
        """Parse a single HTML form element."""
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
        """Parse all fieldsets within a parent element."""
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
        """Parse all form fields within a parent element."""
        fields = []
        for input_elem in parent.find_all(['input', 'select', 'textarea'], recursive=not exclude_fieldsets):
            field_data = self._parse_field(input_elem)
            if field_data:
                fields.append(field_data)
        return fields

    def _parse_field(self, element: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse a single form field."""
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
        """Find the label associated with a form field."""
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

    def _extract_validation(self, element: BeautifulSoup) -> Dict[str, Any]:
        """Extract validation rules for a field."""
        validation = {}
        if element.get('minlength'):
            validation['minlength'] = int(element.get('minlength'))
        if element.get('maxlength'):
            validation['maxlength'] = int(element.get('maxlength'))
        if element.get('min'):
            validation['min'] = float(element.get('min')) if element.get('type') in {'number', 'range'} else element.get('min')
        if element.get('max'):
            validation['max'] = float(element.get('max')) if element.get('type') in {'number', 'range'} else element.get('max')
        if element.get('pattern'):
            validation['pattern'] = element.get('pattern')
        if element.get('required'):
            validation['required'] = True
        return validation

    def _parse_select_options(self, select: BeautifulSoup) -> List[Dict[str, str]]:
        """Parse options for a select element."""
        options = []
        for option in select.find_all('option'):
            options.append({
                'value': option.get('value', option.get_text(strip=True)),
                'text': option.get_text(strip=True),
                'selected': option.get('selected') is not None,
                'disabled': option.get('disabled') is not None
            })
        return options

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

def run_tests():
    """Run test cases for FormParser."""
    parser = FormParser()

    # Test Case 1: Simple HTML form
    simple_form = """
    <form id="simple-form" action="/submit" method="POST">
        <label for="username">Username</label>
        <input type="text" id="username" name="username" required>
        <input type="submit" value="Submit">
    </form>
    """

    # Test Case 2: Scholarship HTML Form
    scholarship_form = """
    <form id="scholarshipForm">
        <label for="name">Full Name:</label>
        <input type="text" id="name" name="fullname" required>
        <label for="dob">Date of Birth:</label>
        <input type="date" id="dob" name="dob" required>
        <label for="category">Caste Category:</label>
        <select id="category" name="category">
            <option value="gen">General</option>
            <option value="obc">OBC</option>
            <option value="sc">SC</option>
            <option value="st">ST</option>
        </select>
        <label for="income">Annual Family Income (in ₹):</label>
        <input type="number" id="income" name="income">
        <button type="submit">Submit Application</button>
    </form>
    """

    # Test Case 3: Google Form
    google_form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfy84bLTrN9-na_IseUdwJm-R7DroXBDWopNwKEG1Lj6lq1Fw/viewform"

    # Test Case 4: Typeform (Placeholder URL - replace with real Typeform URL)
    typeform_url = "https://form.typeform.com/to/placeholder"  # Replace with valid Typeform URL

    # Test Case 5: Microsoft Form
    microsoft_form_url = "https://forms.cloud.microsoft/r/qqPu4N8rqB?origin=lprLink"

    # Test Case 6: Custom Web Form
    custom_form_url = "https://www.w3.org/WAI/tutorials/forms/simple-form/"  # Simple contact form

    # Run tests
    try:
        sys.stdout.reconfigure(encoding='utf-8')

        print("Test 1: Simple HTML Form")
        result1 = parser.parse_html(simple_form)
        print(parser.to_json(result1))
        with open("simple_form_schema.json", "w", encoding='utf-8') as f:
            json.dump(result1, f, indent=4, ensure_ascii=False)

        print("\nTest 2: Scholarship HTML Form")
        result2 = parser.parse_html(scholarship_form)
        print(parser.to_json(result2))
        with open("scholarship_form_schema.json", "w", encoding='utf-8') as f:
            json.dump(result2, f, indent=4, ensure_ascii=False)

        print("\nTest 3: Google Form")
        result3 = parser.parse_form_from_url(google_form_url)
        print(parser.to_json(result3))
        with open("google_form_schema.json", "w", encoding='utf-8') as f:
            json.dump(result3, f, indent=4, ensure_ascii=False)

        # print("\nTest 4: Typeform")
        # result4 = parser.parse_form_from_url(typeform_url)
        # print(parser.to_json(result4))
        # with open("typeform_schema.json", "w", encoding='utf-8') as f:
        #     json.dump(result4, f, indent=4, ensure_ascii=False)

        print("\nTest 5: Microsoft Form")
        result5 = parser.parse_form_from_url(microsoft_form_url)
        print(parser.to_json(result5))
        with open("microsoft_form_schema.json", "w", encoding='utf-8') as f:
            json.dump(result5, f, indent=4, ensure_ascii=False)

        print("\nTest 6: Custom Web Form")
        result6 = parser.parse_form_from_url(custom_form_url)
        print(parser.to_json(result6))
        with open("custom_form_schema.json", "w", encoding='utf-8') as f:
            json.dump(result6, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    run_tests()