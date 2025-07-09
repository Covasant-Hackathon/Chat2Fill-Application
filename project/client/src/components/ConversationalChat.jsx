import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './ConversationalChat.css';

const ConversationalChat = ({ formData, sessionId, onComplete }) => {
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState('');
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (formData && sessionId) {
      startConversation();
    }
  }, [formData, sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (inputRef.current && !isLoading && !isComplete) {
      inputRef.current.focus();
    }
  }, [isLoading, isComplete, currentQuestion]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const startConversation = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Add welcome message
      const welcomeMessage = {
        type: 'bot',
        content: `Hi! I'll help you fill out the form "${formData.form_title || 'Form'}". Let's start with some questions.`,
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);

      // Start conversation
      const response = await axios.post('http://localhost:8000/start_conversation', {
        session_id: sessionId,
        form_id: formData.form_id,
        language: formData.language || 'en'
      });

      if (response.data.status === 'success') {
        setConversationId(response.data.conversation_id);
        getNextQuestion(response.data.conversation_id);
      } else {
        throw new Error(response.data.error || 'Failed to start conversation');
      }
    } catch (error) {
      console.error('Error starting conversation:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to start conversation');
    } finally {
      setIsLoading(false);
    }
  };

  const getNextQuestion = async (convId = conversationId) => {
    try {
      setIsTyping(true);

      const response = await axios.post('http://localhost:8000/get_next_question', {
        session_id: sessionId,
        conversation_id: convId,
        language: formData.language || 'en'
      });

      if (response.data.status === 'success') {
        setCurrentQuestion(response.data);
        setProgress({
          current: response.data.current_index + 1,
          total: response.data.total_fields
        });

        // Add question to messages with typing effect
        setTimeout(() => {
          const questionMessage = {
            type: 'bot',
            content: response.data.question,
            fieldName: response.data.field_name,
            fieldType: response.data.field_type,
            fieldRequired: response.data.field_required,
            fieldOptions: response.data.field_options,
            timestamp: new Date().toISOString()
          };
          setMessages(prev => [...prev, questionMessage]);
          setIsTyping(false);
        }, 1000);
      } else if (response.data.status === 'complete') {
        handleConversationComplete();
      } else {
        throw new Error(response.data.error || 'Failed to get next question');
      }
    } catch (error) {
      console.error('Error getting next question:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to get next question');
      setIsTyping(false);
    }
  };

  const submitResponse = async () => {
    if (!currentInput.trim() || !currentQuestion) return;

    const userMessage = {
      type: 'user',
      content: currentInput,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentInput('');

    try {
      const response = await axios.post('http://localhost:8000/submit_response', {
        session_id: sessionId,
        conversation_id: conversationId,
        field_name: currentQuestion.field_name,
        response_text: currentInput,
        language: formData.language || 'en'
      });

      if (response.data.status === 'success') {
        // Add confirmation message
        const confirmMessage = {
          type: 'bot',
          content: 'Got it! ✓',
          timestamp: new Date().toISOString(),
          isConfirmation: true
        };
        setMessages(prev => [...prev, confirmMessage]);

        // Get next question
        setTimeout(() => {
          getNextQuestion();
        }, 500);
      } else if (response.data.status === 'complete') {
        handleConversationComplete();
      } else {
        throw new Error(response.data.error || 'Failed to submit response');
      }
    } catch (error) {
      console.error('Error submitting response:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to submit response');

      // Add error message
      const errorMessage = {
        type: 'bot',
        content: 'Sorry, there was an error with your response. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConversationComplete = async () => {
    try {
      setIsComplete(true);

      const completionMessage = {
        type: 'bot',
        content: 'Great! You\'ve completed all the questions. Let me prepare a summary for you...',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, completionMessage]);

      // Get conversation summary
      const summaryResponse = await axios.get(
        `http://localhost:8000/conversation_summary/${sessionId}/${conversationId}`
      );

      if (summaryResponse.data.status === 'success') {
        const summary = summaryResponse.data;

        const summaryMessage = {
          type: 'bot',
          content: 'Here\'s a summary of your responses:',
          timestamp: new Date().toISOString(),
          summary: summary
        };
        setMessages(prev => [...prev, summaryMessage]);

        // Call onComplete callback
        if (onComplete) {
          onComplete(summary);
        }
      }
    } catch (error) {
      console.error('Error getting conversation summary:', error);
      const errorMessage = {
        type: 'bot',
        content: 'Form completed successfully! However, there was an error generating the summary.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitResponse();
    }
  };

  const renderMessage = (message, index) => {
    const isBot = message.type === 'bot';

    return (
      <div key={index} className={`message ${isBot ? 'bot-message' : 'user-message'}`}>
        <div className="message-content">
          {message.isConfirmation ? (
            <span className="confirmation-message">{message.content}</span>
          ) : message.isError ? (
            <span className="error-message">{message.content}</span>
          ) : message.summary ? (
            <div className="summary-container">
              <div className="summary-header">{message.content}</div>
              <div className="summary-content">
                <h4>Form: {message.summary.form_title}</h4>
                <div className="responses-list">
                  {message.summary.responses.map((response, idx) => (
                    <div key={idx} className="response-item">
                      <strong>{response.field_label || response.field_name}:</strong>
                      <span>{response.answer}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <span>{message.content}</span>
          )}

          {isBot && message.fieldOptions && (
            <div className="field-options">
              <small>Options: {message.fieldOptions}</small>
            </div>
          )}
        </div>
        <div className="message-timestamp">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    );
  };

  const renderTypingIndicator = () => (
    <div className="message bot-message typing-indicator">
      <div className="message-content">
        <div className="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="conversational-chat">
      <div className="chat-header">
        <h3>Chat2Fill Assistant</h3>
        {progress.total > 0 && (
          <div className="progress-indicator">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${(progress.current / progress.total) * 100}%` }}
              ></div>
            </div>
            <span className="progress-text">
              {progress.current} of {progress.total} questions
            </span>
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => renderMessage(message, index))}
        {isTyping && renderTypingIndicator()}
        <div ref={chatEndRef} />
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      <div className="chat-input-container">
        <div className="chat-input">
          <textarea
            ref={inputRef}
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              isComplete
                ? "Conversation completed!"
                : isLoading
                  ? "Please wait..."
                  : "Type your answer..."
            }
            disabled={isLoading || isComplete}
            rows="2"
          />
          <button
            onClick={submitResponse}
            disabled={!currentInput.trim() || isLoading || isComplete}
            className="send-button"
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </div>

        {currentQuestion && (
          <div className="input-hints">
            <small>
              {currentQuestion.field_required && <span className="required">* Required</span>}
              {currentQuestion.field_type && (
                <span className="field-type">Type: {currentQuestion.field_type}</span>
              )}
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationalChat;
