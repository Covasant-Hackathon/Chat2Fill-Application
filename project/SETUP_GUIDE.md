# Chat2Fill - Conversational Interface Setup Guide

This guide will help you set up and run the complete Chat2Fill conversational interface system.

## 🎯 Overview

Chat2Fill now includes a conversational interface that allows users to:
1. Parse forms from URLs or HTML
2. Start interactive conversations with AI-generated questions
3. Fill forms through natural chat interactions
4. Get summaries of completed conversations
5. Automatically fill forms with collected responses

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Chrome browser (for form autofilling)
- Google Gemini API key

## 🚀 Quick Setup

### 1. Clone and Navigate to Project
```bash
cd Covasant_Hackathon/project
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd server
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn google-generativeai python-dotenv sqlite3 sqlalchemy playwright selenium webdriver-manager pydantic fastmcp
```

#### Setup Environment Variables
Create a `.env` file in the `server` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./database/chat2fill.db
```

#### Initialize Database
```bash
python utils/setup_database.py
```

#### Test Database Integration
```bash
python test_conversation.py
```

### 3. Frontend Setup

#### Install Node Dependencies
```bash
cd ../client
npm install
```

#### Additional Dependencies (if needed)
```bash
npm install axios react-json-view
```

### 4. Install Browser Dependencies
```bash
cd ../server
playwright install chromium
```

## 🔧 Configuration

### Database Configuration
The system uses SQLite by default. Configuration is in `utils/database_config.py`:
- Database path: `server/database/chat2fill.db`
- Session timeout: 24 hours
- Auto-backup: Every 24 hours
- Max backups: 5

### Language Support
Currently supported languages:
- English (en)
- Hindi (hi)
- Telugu (te)
- Tamil (ta)
- Bengali (bn)

## 🏃‍♂️ Running the System

### Start Backend Services

#### Terminal 1: Main FastMCP Server
```bash
cd server
python server.py
```

#### Terminal 2: Bridge Server
```bash
cd server
python bridge.py
```

### Start Frontend
#### Terminal 3: React Development Server
```bash
cd client
npm run dev
```

## 🌐 Access the Application

- **Frontend**: http://localhost:5173
- **Bridge API**: http://localhost:8000
- **FastMCP Server**: Background service

## 📱 Using the Conversational Interface

### 1. Parse a Form
1. Go to http://localhost:5173
2. Enter a form URL or HTML content
3. Select language and form type
4. Click "Parse"

### 2. Start Conversation
1. After successful parsing, click "Start Chat"
2. The system will switch to conversational mode
3. Answer questions one by one in the chat interface

### 3. Complete the Form
1. The system asks questions based on form fields
2. Answer each question in natural language
3. Get real-time validation and feedback
4. Receive a summary when completed

### 4. Auto-fill (Optional)
1. Use the collected responses to auto-fill the original form
2. System uses Playwright to automate form filling

## 🔧 API Endpoints

### Core Form Parsing
- `POST /parse_form` - Parse form from URL
- `POST /parse_html_form` - Parse form from HTML

### Conversational Interface
- `POST /start_conversation` - Start new conversation
- `POST /get_next_question` - Get next question
- `POST /submit_response` - Submit user response
- `GET /conversation_summary/{session_id}/{conversation_id}` - Get summary

### Auto-fill
- `POST /autofill_form` - Auto-fill form with responses

## 📊 Database Schema

### Key Tables
- `users` - Session management
- `forms` - Parsed form schemas
- `form_fields` - Individual field definitions
- `prompts` - AI-generated questions
- `conversations` - User interaction sessions
- `user_responses` - User answers with confidence scores
- `translations` - Multilingual content

## 🧪 Testing

### Test Database Integration
```bash
cd server
python test_conversation.py
```

### Test Server Endpoints
```bash
cd server
python tests/test_server_integration.py
```

### Quick Database Check
```bash
cd server
python tests/test_db_quick.py
```

## 🔍 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Reinitialize database
python utils/setup_database.py
```

#### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt
```

#### Frontend Not Loading
```bash
# Clear cache and reinstall
cd client
rm -rf node_modules package-lock.json
npm install
npm run dev
```

#### Bridge Server Connection Issues
```bash
# Check if ports are free
netstat -an | grep :8000
netstat -an | grep :5173

# Kill processes if needed
pkill -f "python bridge.py"
pkill -f "python server.py"
```

### Database Management

#### Access Database Admin
```bash
cd server
python database/admin.py
```

#### Manual Database Backup
```bash
cd server
python -c "from database_manager import DatabaseManager; from utils.database_config import DatabaseConfig; db = DatabaseManager(DatabaseConfig()); db.backup_database()"
```

#### Clean Old Sessions
```bash
cd server
python -c "from utils.session_manager import SessionManager; from database_manager import DatabaseManager; from utils.database_config import DatabaseConfig; sm = SessionManager(DatabaseManager(DatabaseConfig())); sm.cleanup_expired_sessions()"
```

## 📝 Environment Variables

### Required
- `GEMINI_API_KEY` - Google Gemini API key

### Optional
- `DATABASE_URL` - Database connection string
- `DEBUG` - Enable debug mode
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)
- `SESSION_TIMEOUT` - Session timeout in hours
- `MAX_BACKUPS` - Maximum database backups to keep

## 🚨 Security Considerations

1. **API Key Security**: Never commit API keys to version control
2. **Session Management**: Sessions expire after 24 hours
3. **Input Validation**: All inputs are validated before database storage
4. **SQL Injection Prevention**: Uses SQLAlchemy ORM
5. **CORS Configuration**: Properly configured for frontend access

## 🔄 Development Workflow

### Adding New Languages
1. Update `multilingual_support.py`
2. Add language code to frontend language selector
3. Update database schema if needed

### Adding New Form Types
1. Extend `form_parser.py`
2. Update form type validation in `server.py`
3. Add specific parsing logic

### Modifying Conversation Flow
1. Update `llm_conversation.py`
2. Modify conversation endpoints in `server.py`
3. Update frontend conversation component

## 📚 File Structure

```
project/
├── server/                     # Backend
│   ├── docs/                  # Documentation
│   ├── tests/                 # Test files
│   ├── utils/                 # Utility modules
│   ├── database/              # Database integration
│   ├── server.py              # Main FastMCP server
│   ├── bridge.py              # FastAPI bridge
│   ├── database_manager.py    # Database operations
│   ├── llm_conversation.py    # AI conversation logic
│   └── test_conversation.py   # Conversation tests
├── client/                    # Frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── ConversationalChat.jsx
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
└── README.md
```

## 🎉 Success Indicators

After setup, you should see:
1. ✅ Database initialized successfully
2. ✅ FastMCP server running
3. ✅ Bridge server running on port 8000
4. ✅ React app running on port 5173
5. ✅ Conversational chat interface working
6. ✅ Form parsing and conversation flow complete

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Run the test scripts
3. Check server logs for errors
4. Verify API key configuration
5. Ensure all dependencies are installed

## 🚀 Production Deployment

For production deployment:
1. Use environment variables for configuration
2. Set up proper logging
3. Configure database connection pooling
4. Set up monitoring and health checks
5. Use HTTPS for all communications
6. Implement rate limiting
7. Set up automated backups

---

**Happy Coding! 🎉**

The conversational interface is now ready for use. Users can parse forms and interact with AI-generated questions through a natural chat interface, making form filling more intuitive and user-friendly.