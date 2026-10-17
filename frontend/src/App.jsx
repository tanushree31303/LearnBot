import { useState } from "react";
import { uploadDocument, askQuestion } from "./api.js";
import "./App.css";

function App() {
  // List of documents uploaded during this session.
  const [documents, setDocuments] = useState([]);
  // Id of the document the user is currently asking questions about.
  const [activeDocumentId, setActiveDocumentId] = useState("");

  // Upload state: "" | "uploading" | "success" | "error"
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Chat history for the active document.
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  const activeDocument = documents.find((doc) => doc.id === activeDocumentId);

  // -------------------------------------------------------------------------
  // Upload handling
  // -------------------------------------------------------------------------

  async function handleFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadStatus("error");
      setUploadMessage("Please select a PDF file.");
      return;
    }

    setUploadStatus("uploading");
    setUploadMessage(`Processing "${file.name}"...`);

    try {
      const result = await uploadDocument(file);
      const newDocument = { id: result.document_id, filename: result.filename };
      setDocuments((previous) => [...previous, newDocument]);
      setActiveDocumentId(result.document_id);
      setMessages([]);
      setUploadStatus("success");
      setUploadMessage(
        `"${result.filename}" is ready (${result.pages} pages, ${result.chunks} chunks). You can now ask questions.`
      );
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage(error.message);
    }
  }

  function handleFileInputChange(event) {
    const file = event.target.files[0];
    handleFile(file);
    // Allow re-selecting the same file later.
    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    handleFile(file);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  // -------------------------------------------------------------------------
  // Document selection
  // -------------------------------------------------------------------------

  function handleSelectDocument(documentId) {
    if (documentId === activeDocumentId) return;
    setActiveDocumentId(documentId);
    // Start a fresh conversation for the newly selected document.
    setMessages([]);
  }

  // -------------------------------------------------------------------------
  // Asking questions
  // -------------------------------------------------------------------------

  async function handleAsk() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !activeDocumentId || isAsking) return;

    // Show the user's question immediately.
    setMessages((previous) => [
      ...previous,
      { role: "user", text: trimmedQuestion },
    ]);
    setQuestion("");
    setIsAsking(true);

    try {
      const result = await askQuestion(trimmedQuestion, activeDocumentId);
      setMessages((previous) => [
        ...previous,
        { role: "bot", text: result.answer, sources: result.sources },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: "bot", text: `Error: ${error.message}`, isError: true },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  function handleQuestionKeyDown(event) {
    // Press Enter to ask (Shift+Enter makes a new line).
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAsk();
    }
  }

  const canAsk =
    Boolean(activeDocumentId) && question.trim().length > 0 && !isAsking;

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1 className="logo">LearnBot</h1>
        <p className="subtitle">Ask questions about your documents.</p>
      </header>

      <main className="layout">
        {/* Left column: upload + document list */}
        <aside className="sidebar">
          <section className="card">
            <h2>Upload a document</h2>
            <label
              className={`dropzone ${isDragging ? "dropzone-active" : ""}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileInputChange}
                hidden
              />
              <span className="dropzone-title">
                Drag &amp; drop a PDF here
              </span>
              <span className="dropzone-subtitle">
                or click to choose a file
              </span>
            </label>

            {uploadStatus && (
              <p className={`status status-${uploadStatus}`}>
                {uploadMessage}
              </p>
            )}
          </section>

          <section className="card">
            <h2>Your documents</h2>
            {documents.length === 0 ? (
              <p className="muted">No documents uploaded yet.</p>
            ) : (
              <ul className="document-list">
                {documents.map((document) => (
                  <li key={document.id}>
                    <button
                      type="button"
                      className={`document-item ${
                        document.id === activeDocumentId ? "active" : ""
                      }`}
                      onClick={() => handleSelectDocument(document.id)}
                    >
                      <span className="document-name">
                        {document.filename}
                      </span>
                      {document.id === activeDocumentId && (
                        <span className="badge">Active</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>

        {/* Right column: chat */}
        <section className="chat card">
          <div className="chat-header">
            <h2>Chat</h2>
            <span className="chat-document">
              {activeDocument ? activeDocument.filename : "No document selected"}
            </span>
          </div>

          <div className="chat-messages">
            {messages.length === 0 ? (
              <p className="muted chat-empty">
                {activeDocumentId
                  ? "Ask your first question about this document."
                  : "Upload and select a document to start asking questions."}
              </p>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${
                    message.role === "user" ? "message-user" : "message-bot"
                  }`}
                >
                  <div className={`bubble ${message.isError ? "bubble-error" : ""}`}>
                    {message.text}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <div className="sources">
                      <span className="sources-label">Sources:</span>
                      {message.sources.map((source, sourceIndex) => (
                        <span key={sourceIndex} className="source-chip">
                          {source.document}
                          {source.page ? ` - page ${source.page}` : ""}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
            {isAsking && (
              <div className="message message-bot">
                <div className="bubble bubble-loading">
                  Thinking
                  <span className="dots">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="chat-input">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleQuestionKeyDown}
              placeholder={
                activeDocumentId
                  ? "Type your question and press Enter..."
                  : "Select a document first..."
              }
              disabled={!activeDocumentId || isAsking}
              rows={2}
            />
            <button
              type="button"
              className="ask-button"
              onClick={handleAsk}
              disabled={!canAsk}
            >
              {isAsking ? "Asking..." : "Ask"}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
