// Base URL of the FastAPI backend
export const API_URL = "http://localhost:8000";

// Upload a PDF file and return the parsed JSON response.
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Upload failed. Please try again.");
  }
  return data;
}

// Ask a question about a document and return the parsed JSON response.
export async function askQuestion(question, documentId) {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_id: documentId }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Could not get an answer. Please try again.");
  }
  return data;
}
