import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";
import JSONViewer from "react-json-view";

const App = () => {
  const [formType, setFormType] = useState("google");
  const [url, setUrl] = useState("");
  const [htmlInput, setHtmlInput] = useState("");
  const [isFile, setIsFile] = useState(false);
  const [language, setLanguage] = useState("en");
  const [chatHistory, setChatHistory] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("url");
  const [viewMode, setViewMode] = useState("table");
  const [responses, setResponses] = useState({});
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const chatEndRef = useRef(null);
  const profileRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const downloadJsonFile = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const query = {
      type: "url",
      url,
      formType,
      language,
      timestamp: new Date().toISOString(),
    };
    setChatHistory([...chatHistory, { query, response: null }]);

    try {
      const response = await axios.post("http://localhost:8000/parse_form", {
        url,
        form_type: formType,
        language,
      });
      console.log("Server response:", response.data);
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = response.data;
        return updated;
      });
      if (response.data.status === "success" && response.data.form_schema) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        downloadJsonFile(response.data, `form_response_${timestamp}.json`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to parse form");
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = {
          status: "error",
          error: err.response?.data?.detail || "Failed to parse form",
        };
        return updated;
      });
    } finally {
      setLoading(false);
      setUrl("");
    }
  };

  const handleHtmlSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const query = {
      type: "html",
      htmlInput,
      isFile,
      language,
      timestamp: new Date().toISOString(),
    };
    setChatHistory([...chatHistory, { query, response: null }]);

    try {
      const response = await axios.post(
        "http://localhost:8000/parse_html_form",
        {
          html_input: htmlInput,
          is_file: isFile,
          language,
        }
      );
      console.log("Server response:", response.data);
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = response.data;
        return updated;
      });
      if (response.data.status === "success" && response.data.form_schema) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        downloadJsonFile(response.data, `form_response_${timestamp}.json`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to parse HTML form");
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = {
          status: "error",
          error: err.response?.data?.detail || "Failed to parse HTML form",
        };
        return updated;
      });
    } finally {
      setLoading(false);
      setHtmlInput("");
    }
  };

  const handleAutofill = async (chatIndex) => {
    const chat = chatHistory[chatIndex];
    if (!chat.response || chat.response.status !== "success") {
      setError("Cannot autofill: Invalid or missing form schema");
      return;
    }

    setLoading(true);
    setError("");
    const { url, language } = chat.query;
    const { form_schema, questions } = chat.response;
    const responseList = questions.map((q) => ({
      field_id: q.field_id,
      value: responses[q.field_id] || "",
      valid: !!responses[q.field_id],
    }));

    try {
      const response = await axios.post("http://localhost:8000/autofill_form", {
        url,
        form_schema,
        responses: responseList,
        language,
      });
      console.log("Autofill response:", response.data);
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[chatIndex].autofill_response = response.data;
        return updated;
      });
      if (response.data.status === "success") {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        downloadJsonFile(response.data, `autofill_response_${timestamp}.json`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to autofill form");
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[chatIndex].autofill_response = {
          status: "error",
          error: err.response?.data?.detail || "Failed to autofill form",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResponseChange = (fieldId, value) => {
    setResponses((prev) => ({ ...prev, [fieldId]: value }));
  };

  const clearChat = () => {
    setChatHistory([]);
    setError("");
    setResponses({});
  };

  const toggleProfileDropdown = () => {
    setIsProfileOpen(!isProfileOpen);
  };

  const handleProfileAction = (action) => {
    if (action === "logout") {
      alert("Logging out..."); // Placeholder for logout logic
    } else if (action === "profile") {
      alert("Navigating to profile..."); // Placeholder for profile logic
    }
    setIsProfileOpen(false);
  };

  const flattenSchema = (schema) => {
    const fields = [];
    if (!schema || typeof schema !== "object") {
      console.warn("Invalid schema: Schema is not an object");
      return fields;
    }

    const formFields = schema.forms?.[0]?.fields;
    if (!formFields || !Array.isArray(formFields)) {
      console.warn("No fields found in schema:", schema);
      return fields;
    }

    formFields.forEach((field, index) => {
      if (!field || typeof field !== "object") {
        console.warn(`Invalid field at index ${index}:`, field);
        return;
      }

      const label =
        field.translated_label || field.label || field.name || "Unnamed";
      const name = field.name || field.id || `Field${index + 1}`;
      let fieldType = field.type || "Unknown";

      if (fieldType === "text") {
        fieldType = "Text";
      } else if (fieldType === "paragraph") {
        fieldType = "Paragraph Text";
      } else if (fieldType === "multiple_choice") {
        fieldType = "Multiple Choice";
      } else if (fieldType === "dropdown") {
        fieldType = "Dropdown";
      } else {
        fieldType = fieldType.charAt(0).toUpperCase() + fieldType.slice(1);
      }

      const required = field.required ? "Yes" : "No";
      const options = field.translated_options
        ? field.translated_options
            .map((opt) => opt.translated_text || opt.text)
            .join(", ")
        : field.options
        ? field.options.map((opt) => opt.text).join(", ")
        : "N/A";

      fields.push({ label, name, fieldType, required, options });
    });

    return fields;
  };

  const renderQuery = (query) => {
    if (query.type === "url") {
      return (
        <div className="query-content">
          <p>
            <strong>URL:</strong> {query.url}
          </p>
          <p>
            <strong>Form Type:</strong> {query.formType}
          </p>
          <p>
            <strong>Language:</strong> {query.language}
          </p>
        </div>
      );
    }
    return (
      <div className="query-content">
        <p>
          <strong>{query.isFile ? "File Path" : "HTML Content"}:</strong>{" "}
          {query.htmlInput.substring(0, 100)}
          {query.htmlInput.length > 100 ? "..." : ""}
        </p>
        <p>
          <strong>Is File:</strong> {query.isFile ? "Yes" : "No"}
        </p>
        <p>
          <strong>Language:</strong> {query.language}
        </p>
      </div>
    );
  };

  const renderResponse = (response, index) => {
    if (!response) return <p className="loading">Processing...</p>;
    if (response.status === "error") {
      return (
        <div className="response error">
          <h4>Error</h4>
          <p>{response.error}</p>
          {response.gemini_message && (
            <p>
              <strong>Gemini Message:</strong> {response.gemini_message}
            </p>
          )}
        </div>
      );
    }

    const fields = flattenSchema(
      response.translated_form_schema || response.form_schema
    );

    return (
      <div className="response success">
        <h4>Success</h4>
        <div className="view-tabs">
          <button
            className={viewMode === "table" ? "active" : ""}
            onClick={() => setViewMode("table")}
          >
            Table View
          </button>
          <button
            className={viewMode === "json" ? "active" : ""}
            onClick={() => setViewMode("json")}
          >
            JSON View
          </button>
        </div>
        {viewMode === "table" ? (
          <div className="table-container">
            {fields.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Required</th>
                    <th>Options</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((field, idx) => (
                    <tr key={idx}>
                      <td>{field.label}</td>
                      <td>{field.name}</td>
                      <td>{field.fieldType}</td>
                      <td>{field.required}</td>
                      <td>{field.options}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>
                No fields found in schema. Please check the server response.
              </p>
            )}
          </div>
        ) : (
          <div className="json-viewer">
            <JSONViewer
              src={response.translated_form_schema || response.form_schema}
              theme="monokai"
              collapsed={1}
              displayObjectSize={false}
              displayDataTypes={false}
            />
          </div>
        )}
        {response.questions && response.questions.length > 0 && (
          <div className="questions-container">
            <h4>Generated Questions</h4>
            <ul>
              {response.questions.map((q, idx) => {
                const field = response.form_schema.forms[0].fields.find(
                  (f) => f.id === q.field_id
                );
                return (
                  <li key={idx}>
                    <strong>{q.label}:</strong>{" "}
                    {q.translated_question || q.question}
                    {field &&
                    (field.type === "multiple_choice" ||
                      field.type === "dropdown") ? (
                      <select
                        value={responses[q.field_id] || ""}
                        onChange={(e) =>
                          handleResponseChange(q.field_id, e.target.value)
                        }
                      >
                        <option value="">Select an option</option>
                        {field.options.map((opt, optIdx) => (
                          <option key={optIdx} value={opt.value}>
                            {opt.text}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={responses[q.field_id] || ""}
                        onChange={(e) =>
                          handleResponseChange(q.field_id, e.target.value)
                        }
                        placeholder="Enter response"
                      />
                    )}
                  </li>
                );
              })}
            </ul>
            <button
              className="cyberpunk-btn"
              onClick={() => handleAutofill(index)}
              disabled={loading}
            >
              {loading ? "Autofilling..." : "Autofill Form"}
            </button>
          </div>
        )}
        {response.gemini_url && (
          <p>
            <strong>Validated URL:</strong> {response.gemini_url}
          </p>
        )}
        {response.gemini_form_type && (
          <p>
            <strong>Form Type:</strong> {response.gemini_form_type}
          </p>
        )}
        {response.gemini_message && (
          <p>
            <strong>Gemini Message:</strong> {response.gemini_message}
          </p>
        )}
        {chatHistory[index].autofill_response && (
          <div className="autofill-response">
            <h4>Autofill Result</h4>
            {chatHistory[index].autofill_response.status === "success" ? (
              <>
                <p>
                  <strong>Filled Fields:</strong>{" "}
                  {chatHistory[index].autofill_response.filled_fields.join(
                    ", "
                  )}
                </p>
                {chatHistory[index].autofill_response.screenshots.length >
                  0 && (
                  <p>
                    <strong>Screenshots:</strong>{" "}
                    {chatHistory[index].autofill_response.screenshots.join(
                      ", "
                    )}
                  </p>
                )}
                {chatHistory[index].autofill_response.log_file && (
                  <p>
                    <strong>Log File:</strong>{" "}
                    {chatHistory[index].autofill_response.log_file}
                  </p>
                )}
              </>
            ) : (
              <p>
                <strong>Error:</strong>{" "}
                {chatHistory[index].autofill_response.error}
              </p>
            )}
            {chatHistory[index].autofill_response.errors.length > 0 && (
              <p>
                <strong>Errors:</strong>{" "}
                {chatHistory[index].autofill_response.errors.join(", ")}
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app-container">
      <header>
        <div className="header-content">
          <h1 className="logo">Chat2Fill</h1>
          <nav>
            <a
              href="#home"
              className={mode === "url" ? "active" : ""}
              onClick={() => setMode("url")}
            >
              Home
            </a>
            <a
              href="#parse"
              className={mode === "html" ? "active" : ""}
              onClick={() => setMode("html")}
            >
              Parse HTML
            </a>
            <a href="#history">Autofill History</a>
          </nav>
          <div className="profile-container" ref={profileRef}>
            <div className="profile-icon" onClick={toggleProfileDropdown}>
              <svg viewBox="0 0 24 24" fill="var(--text-primary)">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
              </svg>
            </div>
            {isProfileOpen && (
              <div className="profile-dropdown">
                <button onClick={() => handleProfileAction("profile")}>
                  Profile
                </button>
                <button onClick={() => handleProfileAction("logout")}>
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main>
        <div className="chat-container">
          <div className="chat-history">
            {chatHistory.map((chat, index) => (
              <div key={index} className="chat-message">
                <div className="query">
                  <p className="timestamp">
                    {new Date(chat.query.timestamp).toLocaleString()}
                  </p>
                  {renderQuery(chat.query)}
                </div>
                {renderResponse(chat.response, index)}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="input-section">
            <div className="tabs">
              <button
                className={mode === "url" ? "active" : ""}
                onClick={() => setMode("url")}
              >
                URL Form
              </button>
              <button
                className={mode === "html" ? "active" : ""}
                onClick={() => setMode("html")}
              >
                HTML Form
              </button>
              <button className="clear-btn cyberpunk-btn" onClick={clearChat}>
                Clear Chat
              </button>
            </div>

            <div className="form-group">
              <label>
                Language:
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="te">Telugu</option>
                  <option value="ta">Tamil</option>
                  <option value="bn">Bengali</option>
                </select>
              </label>
            </div>

            {mode === "url" ? (
              <form onSubmit={handleUrlSubmit} className="input-form">
                <div className="form-group">
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Enter form URL"
                    required
                  />
                </div>
                <div className="form-group">
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                  >
                    <option value="google">Google</option>
                    <option value="typeform">Typeform</option>
                    <option value="microsoft">Microsoft</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="cyberpunk-btn"
                  disabled={loading}
                >
                  {loading ? "Parsing..." : "Parse"}
                </button>
              </form>
            ) : (
              <form onSubmit={handleHtmlSubmit} className="input-form">
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={isFile}
                      onChange={(e) => setIsFile(e.target.checked)}
                    />
                    File Path
                  </label>
                </div>
                <div className="form-group">
                  <textarea
                    value={htmlInput}
                    onChange={(e) => setHtmlInput(e.target.value)}
                    placeholder={
                      isFile ? "Enter file path" : "Paste HTML content"
                    }
                    rows={4}
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="cyberpunk-btn"
                  disabled={loading}
                >
                  {loading ? "Parsing..." : "Parse"}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

      <footer>
        <div className="footer-content">
          <p>&copy; 2025 Chat2Fill. All rights reserved.</p>
          <p>Developed by Atharv, Juhi, Kunal - Team</p>
          <p>
            Contact:{" "}
            <a href="mailto:support@chat2fill.com">support@chat2fill.com</a>
          </p>
          <p>
            Follow us:
            <a
              href="https://x.com/chat2fill"
              target="_blank"
              rel="noopener noreferrer"
            >
              X
            </a>{" "}
            |
            <a
              href="https://linkedin.com/company/chat2fill"
              target="_blank"
              rel="noopener noreferrer"
            >
              LinkedIn
            </a>
          </p>
        </div>
      </footer>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default App;
