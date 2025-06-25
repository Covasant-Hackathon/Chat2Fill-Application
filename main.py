import os
import time
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

# ❗ Replace this with your live "viewform" URL
url = "https://docs.google.com/forms/d/1bdTG4DNTTkOl4Wx6zkvFY8AQJ8yLpdDNL2OLmBu0lm8/preview"
# url = "https://docs.google.com/forms/d/e/1FAIpQLScC_vfaATIpLhOve0YXcqEeijm8giRh7eF8GNSeG--3eCfGFQ/viewform?usp=sharing&ouid=11266094661778362633"
driver.get(url)

# Wait for form to load
try:
    wait = WebDriverWait(driver, 10)
    question_blocks = wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, 'div[role="listitem"]')
    ))

    print("\n📋 Extracted Questions + Field Types:\n")

    for idx, block in enumerate(question_blocks, 1):
        try:
            # Extract question text
            label = block.text.strip().split("\n")[0]
            input_type = "Unknown"

            # Detect input type
            if block.find_elements(By.TAG_NAME, "input"):
                input_type = "Text Input"
            if block.find_elements(By.TAG_NAME, "textarea"):
                input_type = "Paragraph Input"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="radio"]'):
                input_type = "Multiple Choice (Radio)"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="listbox"]'):
                input_type = "Dropdown"
            if block.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]'):
                input_type = "Checkbox"

            print(f"📝 Question {idx}: {label} → 🧩 Field Type: {input_type}")

        except Exception as e:
            print(f"⚠️ Question {idx}: Error detecting field type ({e})")

except Exception as e:
    print("⚠️ Could not extract questions:", e)

driver.quit()
