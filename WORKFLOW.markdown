# Form-to-Conversational ChatBot Workflow

This document outlines the sequential development workflow for the Form-to-Conversational ChatBot project. Each task is assigned to a team member, ensuring focused and streamlined progress.

## Task Queue

1. **Form HTML Parsing**  
   **Assignee**: Atharv  
   **Description**: Extract form fields, types, and constraints from HTML using BeautifulSoup or Selenium.  
   **Tools**: BeautifulSoup, Selenium  

2. **JSON Schema Generation**  
   **Assignee**: Kunal  
   **Description**: Convert extracted form fields into a structured JSON schema for further processing.  
   **Tools**: Python, JSON  

3. **Prompt Generator**  
   **Assignee**: Juhi  
   **Description**: Generate natural, conversational questions from form fields using LangChain.  
   **Tools**: LangChain  

4. **Conversational Agent**  
   **Assignee**: Atharv  
   **Description**: Develop a LangChain/LangGraph-based agent to collect user inputs step-by-step in a conversational manner.  
   **Tools**: LangChain, LangGraph  

5. **Input Validation & Fallback**  
   **Assignee**: Kunal  
   **Description**: Implement checks for input formats, required fields, and fallback mechanisms for invalid inputs.  
   **Tools**: Python  

6. **Multilingual Translation**  
   **Assignee**: Juhi  
   **Description**: Translate questions into multiple languages using IndicTrans2/Bhashini and reverse-translate user answers.  
   **Tools**: IndicTrans2, Bhashini  

7. **Selenium Form Autofill**  
   **Assignee**: Atharv  
   **Description**: Use collected user answers to automatically fill and submit the original form via Selenium.  
   **Tools**: Selenium  

8. **React Frontend UI**  
   **Assignee**: Kunal  
   **Description**: Build a user-friendly React interface for chat, form URL/file input, and language selection.  
   **Tools**: React, Tailwind CSS  

9. **FastAPI Backend & API**  
   **Assignee**: Juhi  
   **Description**: Create FastAPI endpoints `/generate-chatbot` and `/submit-form` for core functionality.  
   **Tools**: FastAPI, Python  

10. **Voice Input/Output (STT/TTS)**  
    **Assignee**: Atharv  
    **Description**: Integrate Web Speech API to enable voice-based interaction for input and output.  
    **Tools**: Web Speech API  

11. **Form Summary Before Submit**  
    **Assignee**: Kunal  
    **Description**: Display a preview of all user answers for review before final form submission.  
    **Tools**: React, Python  

12. **Analytics Dashboard**  
    **Assignee**: Juhi  
    **Description**: Develop a dashboard to track completion rates, language usage, and user drop-offs.  
    **Tools**: React, FastAPI  

13. **Demo Video Recording**  
    **Assignee**: Atharv  
    **Description**: Record a comprehensive video demonstrating the chatbot workflow from form input to submission.  
    **Tools**: Screen recording software  

14. **Documentation + Pitch Deck**  
    **Assignee**: Kunal  
    **Description**: Write a detailed README and create a pitch deck for the project presentation.  
    **Tools**: Markdown, PowerPoint/Google Slides  

## Notes
- Update everything on github.