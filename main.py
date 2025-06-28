import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup Chrome driver
chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
service = Service(chromedriver_path)

options = Options()
# options.add_argument("--headless")  # Uncomment if you want to run in background
driver = webdriver.Chrome(service=service, options=options)

# ❗ Replace with your live "viewform" URL
# url = "https://docs.google.com/forms/d/1bdTG4DNTTkOl4Wx6zkvFY8AQJ8yLpdDNL2OLmBu0lm8/preview"
url = "https://docs.google.com/forms/d/e/1FAIpQLScC_vfaATIpLhOve0YXcqEeijm8giRh7eF8GNSeG--3eCfGFQ/viewform?usp=sharing"
driver.get(url)

# Prepare list to store extracted fields
fields_schema = []

try:
    wait = WebDriverWait(driver, 10)
    question_blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="listitem"]')))
    
    # Get form title if available
    form_title = "Untitled Form"
    try:
        form_title_elem = driver.find_element(By.CSS_SELECTOR, 'div[jsname="r4nke"]')  # Title container
        if form_title_elem:
            form_title = form_title_elem.text.strip()
    except:
        pass

    print("\n📋 Extracted Questions + Field Types:\n")

    for idx, block in enumerate(question_blocks, 1):
        try:
            label = block.text.strip().split("\n")[0]
            if not label:
                label = f"Untitled Question {idx}"

            input_type = "unknown"
            field_type = "text"
            is_required = False

            # Detect field type
            if block.find_elements(By.TAG_NAME, "input"):
                input_type = "Text Input"
                field_type = "text"
            if block.find_elements(By.TAG_NAME, "textarea"):
                input_type = "Paragraph Input"
                field_type = "paragraph"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="radio"]'):
                input_type = "Multiple Choice (Radio)"
                field_type = "multiple_choice"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]'):
                input_type = "Checkbox"
                field_type = "checkbox"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="listbox"]'):
                input_type = "Dropdown"
                field_type = "dropdown"

            # Detect if required
            try:
                block.find_element(By.CSS_SELECTOR, 'span[aria-label="Required question"]')
                is_required = True
            except:
                is_required = False

            print(f"📝 Question {idx}: {label} → 🧩 Field Type: {input_type}")

            field = {
                "id": idx,
                "label": label,
                "type": field_type,
                "required": is_required
            }

            # Extract options if applicable
            if field_type in ["multiple_choice", "dropdown", "checkbox"]:
                option_elements = block.find_elements(By.CSS_SELECTOR, '[role="presentation"]')
                options = [opt.text.strip() for opt in option_elements if opt.text.strip()]
                if options:
                    field["options"] = list(set(options))  # remove duplicates

            fields_schema.append(field)

        except Exception as e:
            print(f"⚠️ Question {idx}: Error: {e}")

except Exception as e:
    print("⚠️ Could not extract questions:", e)

driver.quit()

# Final schema
form_schema = {
    "form_title": form_title,
    "fields": fields_schema
}

# Save to file
with open("form_schema.json", "w", encoding='utf-8') as f:
    json.dump(form_schema, f, indent=4, ensure_ascii=False)

print("\n✅ JSON schema saved to form_schema.json")
