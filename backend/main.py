"""
LearnBot FastAPI backend.

This is a thin API layer that connects the React frontend to the RAG pipeline
in rag.py. It only exposes three small endpoints:

    GET  /api/health  - check that the backend is running
    POST /api/upload  - upload and process a PDF
    POST /api/ask     - ask a question about an uploaded document
"""

import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag

app = FastAPI(title="LearnBot API")

# Allow the React development server to call this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    """Request body for /api/ask."""

    question: str
    document_id: str


@app.get("/api/health")
def health():
    """Return a simple status so the frontend knows the backend is up."""
    return {"status": "ok", "message": "LearnBot backend is running."}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Validate, extract, embed and store an uploaded PDF."""
    filename = file.filename or "document.pdf"

    # 1. Check the file extension.
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Please upload a PDF file."
        )

    # 2. Read the file into memory.
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # 3. A valid PDF starts with the magic bytes "%PDF".
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="This file does not look like a valid PDF document.",
        )

    # 4. Give the document a short unique id used to isolate its chunks.
    document_id = uuid.uuid4().hex[:12]

    try:
        info = rag.process_pdf(file_bytes, filename, document_id)
    except ValueError as error:
        # Readable problems with the PDF (empty text, protected, etc.).
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process the PDF. Please check the file and try "
            f"again. (Details: {error})",
        )

    return {
        "message": "Document processed successfully.",
        "document_id": document_id,
        "filename": filename,
        "pages": info["pages"],
        "chunks": info["chunks"],
    }


@app.post("/api/ask")
def ask_question(request: AskRequest):
    """Retrieve relevant chunks and generate an answer for a question."""
    question = request.question.strip()

    # 1. Basic validation.
    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question.")
    if not request.document_id:
        raise HTTPException(
            status_code=400, detail="Please upload and select a document first."
        )

    # 2. Run the RAG workflow.
    try:
        return rag.answer_question(question, request.document_id)
    except RuntimeError as error:
        # Missing token or Hugging Face inference problems.
        raise HTTPException(status_code=502, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not answer the question right now. Please try again. "
            f"(Details: {error})",
        )
