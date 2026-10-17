"""
LearnBot RAG pipeline.

This file contains the whole Retrieval-Augmented Generation (RAG) workflow:
1. Read a PDF with LangChain's PyPDFLoader.
2. Split the text with RecursiveCharacterTextSplitter.
3. Create embeddings with the Hugging Face embedding model.
4. Store and retrieve chunks with ChromaDB.
5. Generate an answer with a Hugging Face text generation model.


"""

import os
import tempfile

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import (
    HuggingFaceEmbeddings,
    HuggingFaceEndpoint,
    HuggingFacePipeline,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Read the .env file that sits next to this file.
load_dotenv()



# Embedding model runs locally through sentence-transformers.
EMBEDDING_MODEL_ID = os.getenv(
    "EMBEDDING_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2"
)

# Hosted text generation model used through the Hugging Face Inference Providers API.
HUGGINGFACE_MODEL_ID = os.getenv(
    "HUGGINGFACE_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3"
)

# Token is read from the environment and never sent to the frontend.
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()

# How answers are generated:
#   "local"  -> a small Hugging Face model runs on this computer (no token, no quota)
#   "hosted" -> the Hugging Face Inference Providers API is called (needs a token)
MODEL_MODE = os.getenv("MODEL_MODE", "local").strip().lower()

# Local text generation model (used when MODEL_MODE=local).
# Qwen2.5-0.5B-Instruct is small and fast. For better answers (but slower and a
# larger download) try "Qwen/Qwen2.5-1.5B-Instruct".
LOCAL_MODEL_ID = os.getenv("LOCAL_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
LOCAL_MAX_NEW_TOKENS = int(os.getenv("LOCAL_MAX_NEW_TOKENS", "200"))

# RAG settings.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "3"))

# Where ChromaDB keeps its files so data survives backend restarts.
VECTORSTORE_DIR = os.getenv(
    "VECTORSTORE_DIR", os.path.join(os.path.dirname(__file__), "chroma_db")
)
COLLECTION_NAME = "learnbot_documents"

# Prompt used to force the model to stay grounded in the document.
# A plain text prompt keeps this working with text-generation models, both local
# and hosted.
ANSWER_PROMPT = PromptTemplate.from_template(
    "You are LearnBot, a study assistant.\n"
    "Answer the question using ONLY the context below.\n"
    "If the context does not contain the answer, reply with exactly this sentence: "
    "'I could not find the answer in the uploaded document.'\n"
    "Write a short, direct answer. Do not repeat these instructions, the context "
    "or the question.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


# ---------------------------------------------------------------------------
# Small cached helpers (loading a model is slow, so we do it only once)
# ---------------------------------------------------------------------------

_embeddings = None
_vector_store = None
_llm = None


def get_embeddings():
    """Create the Hugging Face embedding model (all-MiniLM-L6-v2 by default)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_ID)
    return _embeddings


def get_vector_store():
    """Open the persistent ChromaDB collection."""
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=VECTORSTORE_DIR,
        )
    return _vector_store


def get_llm():
    """Create the Hugging Face model used to answer questions."""
    global _llm
    if _llm is None:
        if MODEL_MODE == "hosted":
            if not HUGGINGFACEHUB_API_TOKEN:
                raise RuntimeError(
                    "The Hugging Face token is missing. Either add "
                    "HUGGINGFACEHUB_API_TOKEN to backend/.env, or set "
                    "MODEL_MODE=local to run a model on this computer."
                )
            # Call the hosted text-generation endpoint through LangChain.
            _llm = HuggingFaceEndpoint(
                repo_id=HUGGINGFACE_MODEL_ID,
                huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN,
                task="text-generation",
                max_new_tokens=512,
                temperature=0.1,
            )
        else:
            # Local mode: download a small model once and run it on the CPU.
            # No token and no inference quota are needed.
            _llm = HuggingFacePipeline.from_model_id(
                model_id=LOCAL_MODEL_ID,
                task="text-generation",
                pipeline_kwargs={
                    "max_new_tokens": LOCAL_MAX_NEW_TOKENS,
                    "do_sample": False,
                    "return_full_text": False,
                },
            )
    return _llm


# ---------------------------------------------------------------------------
# Main RAG functions
# ---------------------------------------------------------------------------


def process_pdf(file_bytes, original_filename, document_id):
    """
    Read a PDF, split it into chunks and store them in ChromaDB.

    Returns a small dictionary with the number of pages and chunks.
    Raises ValueError with a readable message when the PDF is not usable.
    """
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    # PyPDFLoader reads from a file path, so we save the bytes to a temporary file.
    temp_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(temp_dir, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", dir=temp_dir
        ) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        # 1. Extract text page by page.
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
    finally:
        # 2. Delete the temporary PDF: we only need the embeddings afterwards.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # 3. Keep only pages that actually contain text.
    text_pages = [page for page in pages if page.page_content.strip()]
    if not text_pages:
        raise ValueError(
            "No readable text was found in this PDF. It may be a scanned "
            "image or a protected document."
        )

    # 4. Split the text into overlapping chunks.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(text_pages)

    # 5. Add metadata so each chunk knows which document and page it came from.
    for chunk in chunks:
        chunk.metadata["document_id"] = document_id
        chunk.metadata["source_name"] = original_filename
        page_number = chunk.metadata.get("page")
        chunk.metadata["page_number"] = (
            page_number + 1 if isinstance(page_number, int) else None
        )

    # 6. Store the chunks and their embeddings in ChromaDB.
    get_vector_store().add_documents(chunks)

    return {
        "pages": len(pages),
        "pages_with_text": len(text_pages),
        "chunks": len(chunks),
    }


def answer_question(question, document_id):
    """
    Retrieve the most relevant chunks for a document and generate an answer.

    Returns {"answer": str, "sources": list}.
    """
    vector_store = get_vector_store()

    # 1. Retrieve the top K chunks belonging to this document only.
    results = vector_store.similarity_search(
        question,
        k=TOP_K,
        filter={"document_id": document_id},
    )

    if not results:
        return {
            "answer": "I could not find the answer in the uploaded document.",
            "sources": [],
        }

    # 2. Join the retrieved chunks into one context block.
    context = "\n\n".join(document.page_content for document in results)

    # 3. Ask the language model to answer using only that context.
    chain = ANSWER_PROMPT | get_llm() | StrOutputParser()
    try:
        answer = chain.invoke({"context": context, "question": question})
    except RuntimeError:
        raise
    except Exception as error:
        if MODEL_MODE == "hosted":
            hint = (
                "This is often a free-tier rate limit or an unavailable model. "
                "Try again later, change HUGGINGFACE_MODEL_ID, or set MODEL_MODE=local "
                "to run a model on this computer instead."
            )
        else:
            hint = (
                "The local model may have failed to download or run. Check your "
                "internet connection or change LOCAL_MODEL_ID in backend/.env."
            )
        raise RuntimeError(
            f"The language model could not generate an answer. {hint} "
            f"(Details: {error})"
        )

    # 4. Collect source page numbers, avoiding duplicates.
    sources = []
    seen_pages = set()
    for document in results:
        page_number = document.metadata.get("page_number")
        source_name = document.metadata.get("source_name")
        key = (source_name, page_number)
        if key in seen_pages:
            continue
        seen_pages.add(key)
        sources.append(
            {
                "document": source_name,
                "page": page_number,
                "snippet": document.page_content[:200].strip(),
            }
        )

    return {"answer": answer.strip(), "sources": sources}
