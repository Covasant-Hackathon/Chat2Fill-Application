# 18-Day Hackathon Daily Prompts
## Copy-Paste Ready Task Prompts for Form-to-Conversational Bot

---

## **DAY 1: Project Setup & Environment**

```
I'm building a Form-to-Conversational Bot for a hackathon. Help me set up the complete development environment.

Requirements:
- FastAPI backend with Python 3.9+
- PostgreSQL database with SQLAlchemy
- Docker setup for development
- Basic project structure with proper folders
- Git repository initialization
- Environment configuration files

Please provide:
1. Complete folder structure
2. requirements.txt with all necessary packages
3. Docker Compose file for development
4. Basic FastAPI app setup with health check endpoint
5. Database connection setup
6. Environment variables configuration
7. .gitignore file

Make it production-ready but suitable for rapid development.
```

---

## **DAY 2: HTML Form Parser**

```
I need to build an HTML form parser that can extract form structure and metadata from HTML content.

Requirements:
- Parse HTML content using BeautifulSoup4
- Extract all form fields with their properties (name, type, required, options, etc.)
- Handle different input types: text, number, email, date, select, radio, checkbox, textarea
- Extract labels and validation rules
- Support nested fieldsets and complex form structures
- Return structured data format (JSON/dict)

Input: HTML string or file
Output: Structured form metadata with fields, validation rules, and hierarchy

Please provide:
1. Complete form parser class
2. Data structures for form representation
3. Helper functions for different field types
4. Error handling for malformed HTML
5. Test cases with sample HTML forms
6. Documentation for the parser API
```

---

## **DAY 3: Database Schema & Models**

```
Design and implement database schema for the Form-to-Conversational Bot system.

Requirements:
- SQLAlchemy models for PostgreSQL
- Tables needed:
  * Forms (store parsed form metadata)
  * Conversations (user sessions and chat history)
  * Form Submissions (completed form data)
  * User Sessions (temporary conversation state)
- Proper relationships between tables
- Database migrations using Alembic
- CRUD operations for all models

Please provide:
1. Complete SQLAlchemy model definitions
2. Database schema diagram/description
3. Alembic migration files
4. CRUD operation functions
5. Database connection and session management
6. Sample data insertion scripts for testing
7. Database queries for common operations
```

---

## **DAY 4: Basic API Structure**

```
Create a comprehensive REST API structure for the Form-to-Conversational Bot using FastAPI.

Required Endpoints:
- POST /forms/upload (upload HTML file)
- POST /forms/url (submit form URL)
- GET /forms/{form_id} (get form details)
- POST /conversations/start (start new conversation)
- POST /conversations/{conv_id}/message (send message)
- GET /conversations/{conv_id}/history (get chat history)
- POST /forms/{form_id}/submit (final form submission)

Please provide:
1. Complete FastAPI route definitions
2. Pydantic models for request/response validation
3. Error handling middleware
4. Request validation and sanitization
5. Response formatting standards
6. API documentation setup
7. Basic authentication structure
8. Testing endpoints with sample requests
```

---

## **DAY 5: LLM Integration**

```
Integrate LLM capabilities using LangChain for generating conversational prompts from form fields.

Requirements:
- LangChain setup with OpenAI GPT or local LLaMA model
- Prompt templates for different field types
- Dynamic question generation based on form metadata
- Context management for ongoing conversations
- Fallback responses for unclear inputs

Please provide:
1. LangChain agent setup and configuration
2. Prompt templates for each form field type
3. Question generation functions
4. Context management system
5. Response parsing and validation
6. Error handling for LLM failures
7. Local model fallback options
8. Testing framework for LLM responses
```

---

## **DAY 6: Conversational Agent Logic**

```
Build the core conversational agent that manages form-filling conversations with users.

Requirements:
- State machine for conversation flow
- Field-by-field questioning logic
- Input validation and error handling
- Context awareness (remember previous answers)
- Smart follow-up questions
- Conversation completion detection
- Support for going back to previous questions

Please provide:
1. Conversation state management class
2. State machine implementation
3. Question sequencing logic
4. Input processing and validation
5. Context retention system
6. Error recovery mechanisms
7. Conversation flow control
8. Testing scenarios for different conversation paths
```

---

## **DAY 7: Input Validation & Processing**

```
Implement comprehensive input validation and processing for different form field types.

Requirements:
- Type-specific validation (email, phone, date, number ranges)
- Fuzzy matching for categorical inputs (select options)
- Data cleaning and normalization
- Custom validation rules based on form constraints
- Error messages that guide users to correct inputs
- Support for partial/incomplete inputs

Please provide:
1. Validation functions for each input type
2. Fuzzy matching algorithms for select options
3. Data cleaning and normalization utilities
4. Custom validation rule engine
5. User-friendly error message generation
6. Input suggestion system
7. Validation testing framework
8. Edge case handling
```

---

## **DAY 8: Translation Integration**

```
Integrate multilingual support using IndicTrans2 for Indian languages.

Requirements:
- IndicTrans2 model setup and integration
- Language detection for user inputs
- Bidirectional translation (user language ↔ form language)
- Language preference management
- Translation quality validation
- Support for at least Hindi, Telugu, Tamil, Bengali + English

Please provide:
1. IndicTrans2 setup and configuration
2. Language detection implementation
3. Translation pipeline functions
4. Language preference management
5. Translation caching for performance
6. Quality validation mechanisms
7. Fallback to English for unsupported languages
8. Testing with multilingual inputs
```

---

## **DAY 9: Form Auto-filling System**

```
Build browser automation system for auto-filling forms using Playwright.

Requirements:
- Playwright setup for headless browser automation
- Form field mapping (conversation data → HTML form fields)
- Dynamic form handling (JavaScript-heavy forms)
- Multiple page/wizard form support
- Screenshot capture for verification
- Error handling for missing/changed form elements

Please provide:
1. Playwright browser automation setup
2. Form field mapping and population functions
3. Dynamic content waiting strategies
4. Multi-page form navigation
5. Element location and interaction methods
6. Screenshot and verification utilities
7. Error handling and recovery mechanisms
8. Testing with various form types
```

---

## **DAY 10: Form Submission Logic**

```
Implement automated form submission with user confirmation workflow.

Requirements:
- Form submission automation using Playwright
- Pre-submission validation and preview
- User confirmation system
- Submission status tracking
- Response handling and error detection
- Retry mechanisms for failed submissions
- Submission receipt/confirmation capture

Please provide:
1. Form submission automation functions
2. Pre-submission validation system
3. User confirmation workflow
4. Submission tracking and logging
5. Error detection and handling
6. Retry logic for failures
7. Success confirmation capture
8. Integration with conversation system
```

---

## **DAY 11: React Frontend Setup**

```
Set up a complete React frontend with TypeScript for the Form-to-Conversational Bot.

Requirements:
- React 18+ with TypeScript
- Modern UI framework (Tailwind CSS or Material-UI)
- Routing setup with React Router
- API integration utilities (Axios/Fetch)
- State management (Context API or Redux)
- Component structure for scalability

Please provide:
1. Complete React project setup with TypeScript
2. Folder structure and component organization
3. Routing configuration
4. API service layer setup
5. Global state management setup
6. UI component library integration
7. Development and build scripts
8. Basic layout and navigation components
```

---

## **DAY 12: Frontend Core Features**

```
Build the main frontend features for form upload and chat interface.

Requirements:
- Form upload interface (URL input + file upload)
- Real-time chat interface with message history
- Form preview/display component
- Language selection dropdown
- Loading states and error handling
- Responsive design for mobile/desktop

Please provide:
1. Form upload component with drag-and-drop
2. Chat interface with message bubbles
3. Real-time message updates (WebSocket or polling)
4. Form preview component
5. Language selector component
6. Loading spinners and error boundaries
7. Responsive layout components
8. Integration with backend APIs
```

---

## **DAY 13: Frontend Polish & UX**

```
Enhance the frontend with better UX, animations, and user experience improvements.

Requirements:
- Smooth animations and transitions
- Better error handling and user feedback
- Conversation history management
- Form completion progress indicators
- Dark/light theme support
- Accessibility improvements (ARIA labels, keyboard navigation)

Please provide:
1. CSS animations and transitions
2. Enhanced error handling and toast notifications
3. Conversation history UI improvements
4. Progress indicators and status displays
5. Theme switching functionality
6. Accessibility enhancements
7. Performance optimizations
8. Mobile-first responsive design improvements
```

---

## **DAY 14: End-to-End Integration**

```
Connect all system components and test the complete user journey.

Requirements:
- Full integration testing of all components
- End-to-end user flow testing
- Performance optimization and bottleneck identification
- Error handling across system boundaries
- Logging and monitoring setup
- Data flow validation

Please provide:
1. Integration testing suite
2. End-to-end test scenarios
3. Performance profiling and optimization
4. Cross-component error handling
5. Comprehensive logging setup
6. Data flow validation tools
7. System health monitoring
8. Load testing framework
```

---

## **DAY 15: Testing & Bug Fixes**

```
Implement comprehensive testing and fix discovered issues.

Requirements:
- Unit tests for critical functions
- Integration tests for API endpoints
- Frontend component testing
- Edge case testing with various form types
- Performance testing and optimization
- Security testing and validation

Please provide:
1. Complete unit test suite (pytest for backend)
2. API integration tests
3. Frontend component tests (Jest/React Testing Library)
4. Edge case test scenarios
5. Performance benchmarking tests
6. Security vulnerability assessment
7. Bug tracking and fix documentation
8. Test coverage reporting
```

---

## **DAY 16: API Documentation & Security**

```
Complete API documentation and implement security measures.

Requirements:
- Comprehensive API documentation with examples
- Input sanitization and validation
- Rate limiting implementation
- Authentication and authorization
- CORS configuration
- Error handling standardization
- API versioning strategy

Please provide:
1. Complete API documentation (OpenAPI/Swagger)
2. Input sanitization functions
3. Rate limiting middleware
4. Authentication system implementation
5. CORS configuration
6. Standardized error response format
7. API versioning setup
8. Security best practices implementation
```

---

## **DAY 17: Deployment Preparation**

```
Prepare the application for production deployment on Google Cloud Platform.

Requirements:
- Production Docker configuration
- Environment variable management
- GCP deployment setup (Cloud Run or Compute Engine)
- Database setup on GCP (Cloud SQL)
- SSL/HTTPS configuration
- Monitoring and logging setup

Please provide:
1. Production Dockerfile and docker-compose
2. Environment configuration for GCP
3. GCP deployment scripts and configuration
4. Cloud SQL setup and connection
5. SSL certificate configuration
6. Cloud monitoring and logging setup
7. Deployment pipeline documentation
8. Staging environment configuration
```

---

## **DAY 18: Demo & Documentation**

```
Create the final demo video and complete project documentation.

Requirements:
- Comprehensive demo video showing all features
- Architecture design document
- User guide and installation instructions
- API documentation
- Presentation slides for the hackathon
- Project README with setup instructions

Please provide:
1. Demo video script and key demonstration points
2. Architecture design document template
3. User guide and tutorial documentation
4. Complete API reference documentation
5. Presentation slides outline
6. Project README with setup instructions
7. Deployment guide
8. Future enhancement roadmap
```

---

## **General Daily Prompt Template**

```
For any specific day, use this template:

I'm working on Day [X] of my Form-to-Conversational Bot hackathon project. 

Current Status:
- [List what you've completed so far]
- [Any issues you're facing]
- [Current codebase structure]

Today's Goals:
- [Copy the specific day's requirements from above]

Please help me:
1. [Specific technical implementation]
2. [Code examples and best practices]
3. [Testing approaches]
4. [Integration with existing components]
5. [Error handling and edge cases]

Constraints:
- Must work with existing tech stack: [FastAPI, React, PostgreSQL, etc.]
- Timeline: Must be completed in one day
- Focus on MVP functionality over perfect code
```