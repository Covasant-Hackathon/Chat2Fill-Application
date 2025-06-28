# Running the Chat2Fill Application (Local Development)

This document provides step-by-step instructions to set up and run the Chat2Fill application locally, consisting of a React client and a FastAPI server. The client is located in the `project/client` directory, and the server is in the `project/server` directory. The server runs on `http://localhost:8000`, and the client communicates with it locally.

## Prerequisites

### System Requirements
- **Node.js**: Version 16 or higher (for running the React client).
- **Python**: Version 3.8 or higher (for running the FastAPI server).
- **ChromeDriver**: Required for the server if it uses web scraping (ensure `chromedriver.exe` is in the project root or configured correctly).
- **Git**: For version control (optional).

### Dependencies
#### Client Dependencies
- Node.js packages (specified in `project/client/package.json`):
  - `axios`: For making HTTP requests to the server.
  - `react-json-view`: For displaying JSON data in the UI.
  - Other dependencies (e.g., React, Vite) as specified in `package.json`.

#### Server Dependencies
- Python packages (install via `pip` in the virtual environment):
  - `fastapi`: For the API server.
  - `uvicorn`: For running the FastAPI server.
  - `fastmcp`: For server-client communication.
  - `google-generativeai`: For Gemini API integration.
  - `python-dotenv`: For loading environment variables.
  - Other dependencies as required by `server.py` and `form_parser.py`.

### Environment Setup
- **Virtual Environment**: A Python virtual environment (`myenv`) is located in the project root (`C:\Users\athar\Desktop\Project-Covasant_Hackathon\Covasant_Hackathon`) or `project/server` directory.
- **Environment Variables**: A `.env` file in `project/server` should contain the `GEMINI_API_KEY` for the Gemini API.

## Setup Instructions

### 1. Clone the Repository (if applicable)
If you haven't already cloned the repository, do so:
```bash
git clone <repository-url>
cd Covasant_Hackathon
```

### 2. Set Up the Client
The React client is located in the `project/client` directory.

1. **Navigate to the Client Directory**:
   ```bash
   cd project/client
   ```

2. **Install Dependencies**:
   Install the required Node.js packages using npm:
   ```bash
   npm install
   ```
   This installs `axios`, `react-json-view`, and other dependencies listed in `package.json`.

### 3. Set Up the Server
The FastAPI server is located in the `project/server` directory.

1. **Navigate to the Server Directory**:
   ```bash
   cd project/server
   ```

2. **Activate the Virtual Environment**:
   Activate the `myenv` virtual environment:
   - On Windows (if `myenv` is in the project root):
     ```bash
     ..\myenv\Scripts\activate
     ```
     or, if `myenv` is in `project/server`:
     ```bash
     .\myenv\Scripts\activate
     ```
   - On macOS/Linux (if `myenv` is in the project root):
     ```bash
     ../myenv/bin/activate
     ```
     or
     ```bash
     ./myenv/bin/activate
     ```

3. **Install Server Dependencies**:
   Install the required Python packages within the virtual environment:
   ```bash
   pip install fastapi uvicorn fastmcp google-generativeai python-dotenv
   ```
   If a `requirements.txt` file exists in `project/server`, you can install all dependencies with:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set Up ChromeDriver**:
   Ensure `chromedriver.exe` (located in the project root) is accessible and compatible with your Chrome browser version. If needed, update ChromeDriver:
   - Download the latest version from [ChromeDriver downloads](https://chromedriver.chromium.org/downloads).
   - Place it in the project root or update the path in `form_parser.py` (if specified).

### 4. Running the Application

#### Terminal 1: Run the FastAPI Server
1. **Ensure Virtual Environment is Active**:
   If not already active, activate `myenv` as described above.

2. **Run the FastAPI Server**:
   ```bash
   python bridge.py
   ```
   This starts the FastAPI server on `http://localhost:8000`. You should see logs indicating the server is running. Test the server by visiting `http://localhost:8000/docs` in a browser to access the Swagger UI.

#### Terminal 2: Run the React Client
1. **Navigate to the Client Directory**:
   If not already there:
   ```bash
   cd project/client
   ```

2. **Run the Development Server**:
   ```bash
   npm run dev
   ```
   This starts the React app, typically on `http://localhost:5173` (check the terminal output for the exact port).

3. **Access the Application**:
   Open a browser and navigate to `http://localhost:5173` (or the port shown by `npm run dev`). The Chat2Fill interface should load, allowing you to parse forms via URL or HTML.

### 5. Expected Output
- **Client**: The React app at `http://localhost:5173` displays the Chat2Fill interface with a form to parse URLs or HTML content. The table should show fields like:
  | Label                              | Name                              | Type           | Required | Options |
  |------------------------------------|-----------------------------------|----------------|----------|---------|
  | Name / Company Name                | name_/_company_name              | Text           | No       | N/A     |
  | Email                              | email                            | Text           | No       | N/A     |
  | Address / Located At               | address_/_located_at             | Paragraph Text | No       | N/A     |
  | Phone Number (with Country Code)   | phone_number_(with_country_code) | Text           | No       | N/A     |
  | Which Job are you Looking for?     | which_job_are_you_looking_for?   | Paragraph Text | No       | N/A     |
  | Are you a:                         | are_you_a:                       | Dropdown       | No       | [e.g., Job Seeker, Employer] |
- **Server**: The FastAPI server runs on `http://localhost:8000` and responds to `/parse_form` and `/parse_html_form` requests.
