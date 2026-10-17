# 🤖 LearnBot — AI-Powered Document Q&A

**Upload PDFs. Ask questions. Get answers from your documents using RAG.**

LearnBot is a web application that enables users to upload PDF documents and ask questions in natural language. It uses Retrieval-Augmented Generation (RAG) to retrieve relevant text and generate context-aware answers with source page references.

<p align="center">
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangChain-RAG-1C3C3C" alt="LangChain" />
  <img src="https://img.shields.io/badge/ChromaDB-Vector%20Database-purple" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Hugging%20Face-Models-yellow?logo=huggingface&logoColor=black" alt="Hugging Face" />
</p>

---

## ✨ Features

- 📄 **PDF Upload** — Upload documents for processing.
- 💬 **Document Q&A** — Ask questions in natural language.
- 🔍 **Semantic Search** — Retrieve relevant text chunks using embeddings.
- 🧠 **RAG Pipeline** — Generate answers grounded in document content.


## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| React.js, Vite | Frontend and development server |
| Python, FastAPI | Backend API |
| LangChain | RAG pipeline and document processing |
| ChromaDB | Vector storage and similarity search |
| Sentence Transformers | Text embeddings |
| Hugging Face | Language models and hosted inference |
| PyPDF | PDF text extraction |

## 🏗️ Architecture

```text
        ┌──────────────────┐
        │   React Frontend │
        │  Upload & Chat   │
        └────────┬─────────┘
                 │ HTTP API
                 ▼
        ┌──────────────────┐
        │   FastAPI Server │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  PDF Processing  │
        │  Split into Chunks│
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │   Embeddings     │
        │ Sentence Transformers
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │     ChromaDB     │
        │  Vector Search   │
        └────────┬─────────┘
                 │
         Relevant Text Chunks
                 │
                 ▼
        ┌──────────────────┐
        │  Language Model  │
        │ Answer Generation│
        └────────┬─────────┘
                 │
                 ▼
          Answer in Chat UI
```

## 📁 Project Structure

```text
LearnBot/
├── backend/
│   ├── main.py
│   ├── rag.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── api.js
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LearnBot
```

### 2. Set Up the Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```




### 3. Set Up the Frontend



```powershell
cd frontend
npm install
npm run dev
```

### 4. Open the Application

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/health |

Keep both the frontend and backend terminals running.

## 🔄 How It Works

1. Upload a PDF document through the React interface.
2. Extract its text using LangChain's `PyPDFLoader`.
3. Split the text into overlapping chunks.
4. Convert chunks into embeddings using `all-MiniLM-L6-v2`.
5. Store the embeddings in ChromaDB.
6. Retrieve the most relevant chunks for each question.
7. Pass the retrieved context to the language model.
8. Display the generated answer and available source pages.








---

