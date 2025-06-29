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
  const [mode, setMode] = useState("url"); // 'url' or 'html'
  const [viewMode, setViewMode] = useState("table"); // 'table' or 'json'
  const chatEndRef = useRef(null);

  // Scroll to bottom of chat on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Function to download JSON file
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
      // Download JSON file automatically
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
      // Download JSON file automatically
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

  const clearChat = () => {
    setChatHistory([]);
    setError("");
  };

  // Flatten form schema for table display
  const flattenSchema = (schema) => {
    const fields = [];
    console.log("Schema received:", schema);

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

      fields.push({
        label,
        name,
        fieldType,
        required,
        options,
      });
    });

    console.log("Processed fields:", fields);
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

  const renderResponse = (response) => {
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
                  {fields.map((field, index) => (
                    <tr key={index}>
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
              {response.questions.map((q, index) => (
                <li key={index}>
                  <strong>{q.label}:</strong>{" "}
                  {q.translated_question || q.question}
                </li>
              ))}
            </ul>
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
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Chat2Fill</h1>
        <p>Developed by Atharv, Juhi, Kunal - Team</p>
      </header>

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
              {renderResponse(chat.response)}
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
            <button className="clear-btn" onClick={clearChat}>
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
              <button type="submit" disabled={loading}>
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
              <button type="submit" disabled={loading}>
                {loading ? "Parsing..." : "Parse"}
              </button>
            </form>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default App;
