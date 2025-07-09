# Chat2Fill - Conversational Form Parser & Autofiller

A sophisticated web application that transforms traditional forms into conversational experiences using AI. Users can parse forms from URLs or HTML, interact with AI-generated questions in a chat interface, and automatically fill forms with their responses.

## 🚀 Features

- **Form Parsing**: Parse forms from URLs or HTML content
- **AI-Powered Conversations**: Generate contextual questions for form fields
- **Multilingual Support**: Support for English, Hindi, Telugu, Tamil, and Bengali
- **Session Management**: Persistent user sessions with database storage
- **Auto-fill Capability**: Automatically fill forms with user responses
- **Database Integration**: SQLite database for storing forms, responses, and conversations
- **Real-time Chat**: Interactive chat interface for form completion

## 📁 Project Structure

```
project/
├── client/                     # React frontend
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   └── App.css            # Styling
│   ├── public/                # Static assets
│   └── package.json           # Frontend dependencies
│
├── server/                     # Python backend
│   ├── docs/                  # Documentation
│   │   ├── DATABASE_README.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   └── USAGE_GUIDE.md
│   │
│   ├── tests/                 # Test files
│   │   ├── test_database.py
│   │   ├── test_db_quick.py
│   │   ├── test_server_integration.py
│   │   └── verify_database_integration.py
│   │
│   ├── utils/                 # Utility modules
│   │   ├── database_config.py
│   │   ├── session_manager.py
│   │   └── setup_database.py
│   │
│   ├── database/              # Database integration
│   │   ├── services.py
│   │   ├── integration.py
│   │   └── admin.py
│   │
│   ├── server.py              # Main FastMCP server
│   ├── bridge.py              # FastAPI bridge server
│   ├── database_manager.py    # Database operations
│   ├── form_parser.py         # Form parsing logic
│   ├── llm_conversation.py    # AI conversation handling
│   ├── multilingual_support.py # Translation services
│   └── form_autofiller.py     # Automated form filling
│
└── README.md                  # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Chrome browser (for form autofilling)

### Backend Setup
1. Navigate to the server directory:
```bash
cd project/server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file in server directory
GEMINI_API_KEY=your_gemini_api_key_here
```

5. Initialize the database:
```bash
python utils/setup_database.py
```

### Frontend Setup
1. Navigate to the client directory:
```bash
cd project/client
```

2. Install dependencies:
```bash
npm install
```

## 🚀 Running the Application

### Start Backend Services
1. Start the main FastMCP server:
```bash
cd project/server
python server.py
```

2. Start the FastAPI bridge server:
```bash
cd project/server
python bridge.py
```

### Start Frontend
```bash
cd project/client
npm run dev
```

The application will be available at `http://localhost:5173`

## 🔧 Configuration

### Database Configuration
- Database files are stored in `server/database/`
- SQLite database with comprehensive schema
- Automatic session cleanup and data management

### Language Support
- English (en)
- Hindi (hi)
- Telugu (te)
- Tamil (ta)
- Bengali (bn)

## 📊 Database Schema

### Core Tables
- **users**: Session management and user preferences
- **forms**: Parsed form schemas and metadata
- **form_fields**: Individual field definitions
- **prompts**: AI-generated questions for fields
- **conversations**: User interaction sessions
- **user_responses**: User answers with confidence scores
- **translations**: Multilingual content storage

## 🔄 API Endpoints

### Form Parsing
- `POST /parse_form` - Parse form from URL
- `POST /parse_html_form` - Parse form from HTML content

### Conversation Management
- `POST /start_conversation` - Start new conversation session
- `POST /submit_response` - Submit user response
- `GET /get_next_question` - Get next question in conversation
- `GET /get_conversation_summary` - Get conversation summary

### Session Management
- `POST /create_session` - Create new user session
- `GET /get_session_data` - Retrieve session information

## 🧪 Testing

### Run Database Tests
```bash
cd project/server
python tests/test_database.py
```

### Run Integration Tests
```bash
cd project/server
python tests/test_server_integration.py
```

### Quick Database Check
```bash
cd project/server
python tests/test_db_quick.py
```

## 📚 Documentation

Detailed documentation is available in the `server/docs/` directory:
- **DATABASE_README.md**: Complete database documentation
- **IMPLEMENTATION_SUMMARY.md**: Technical implementation details
- **USAGE_GUIDE.md**: User and developer guide

## 🛡️ Security Features

- Session-based authentication
- Input validation and sanitization
- SQL injection prevention
- CORS configuration
- Data encryption capabilities

## 🔍 Monitoring & Logging

- Comprehensive logging system
- Database health monitoring
- Performance metrics tracking
- Error tracking and debugging

## 🚧 Development

### Adding New Languages
1. Update `multilingual_support.py`
2. Add language code to database schema
3. Update frontend language selector

### Adding New Form Types
1. Extend `form_parser.py`
2. Update form type validation
3. Add specific parsing logic

### Database Management
```bash
# Access database admin interface
python database/admin.py

# Create database backup
python utils/backup_database.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the documentation in `server/docs/`
2. Run the test suite to identify issues
3. Check the logs for error messages
4. Use the database admin interface for data inspection

## 🔮 Future Enhancements

- Real-time WebSocket support
- Advanced analytics dashboard
- Enhanced AI conversation capabilities
- Mobile app support
- Enterprise authentication integration