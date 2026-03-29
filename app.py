"""
app.py
------
Flask web application for the RAG-guided medical chatbot.

Startup sequence
~~~~~~~~~~~~~~~~
1. Load ``PINECONE_API_KEY`` and ``OPENAI_API_KEY`` from the ``.env`` file.
2. Initialise the HuggingFace sentence-transformer embedding model
   (``all-MiniLM-L6-v2``, 384 dimensions).
3. Connect to the pre-populated Pinecone vector store index
   ``rag-guided-chatbot``.
4. Build the LangChain RAG chain::

       PineconeVectorStore (retriever, k=2)
           └─► create_stuff_documents_chain  (ChatOpenAI gpt-4o-mini + system prompt)
               └─► create_retrieval_chain

Routes
~~~~~~
GET  /         Serve the chat web interface (``templates/chat.html``).
POST /get      Accept a form field ``msg``, run the RAG chain, return the answer
               as plain text.
GET  /health   Return app liveness status as JSON.

Run with::

    python app.py           # development
    gunicorn app:app        # production (recommended)
"""

import json
import logging
import os
import uuid

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore

from src.helper import download_hugging_face_embeddings
from src.prompt import system_prompt


# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Attach any extra fields passed via logger.xxx(extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload)


def _configure_logging() -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    return logging.getLogger(__name__)


logger = _configure_logging()


# ---------------------------------------------------------------------------
# Flask app + rate limiter
# NOTE: The default in-memory storage works for a single process.
# For multi-worker gunicorn deployments swap to Redis:
#   Limiter(storage_uri="redis://localhost:6379")
# ---------------------------------------------------------------------------

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Per-request ID middleware (useful for correlating logs)
# ---------------------------------------------------------------------------

@app.before_request
def _assign_request_id() -> None:
    g.request_id = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Environment & secrets
# ---------------------------------------------------------------------------

load_dotenv(override=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PINECONE_API_KEY:
    raise EnvironmentError("PINECONE_API_KEY is not set.")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY is not set.")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# ---------------------------------------------------------------------------
# RAG pipeline initialisation
# ---------------------------------------------------------------------------

logger.info("Loading embedding model…")
embeddings = download_hugging_face_embeddings()

index_name = "rag-guided-chatbot"
logger.info("Connecting to Pinecone index.", extra={"index": index_name})
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings,
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 2})

chat_model = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chat_model, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

logger.info("RAG pipeline ready.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the chat web interface."""
    return render_template("chat.html")


@app.route("/get", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def chat():
    """Process a user message and return the RAG-generated answer.

    Reads the ``msg`` field from the submitted form, validates it, invokes
    the retrieval chain, and returns the answer string as plain text.

    Returns:
        str: Concise answer (≤ 2 sentences) grounded in the retrieved context.

    Error responses:
        400: Empty or missing ``msg`` field.
        500: Internal error while calling the RAG chain.
    """
    request_id = g.get("request_id", "-")

    # --- Input validation ---------------------------------------------------
    msg = request.form.get("msg", "").strip()
    if not msg:
        logger.warning(
            "Empty message received.",
            extra={"request_id": request_id},
        )
        return jsonify({"error": "Message must not be empty."}), 400

    if len(msg) > 1000:
        logger.warning(
            "Message exceeds character limit.",
            extra={"request_id": request_id, "length": len(msg)},
        )
        return jsonify({"error": "Message must be 1 000 characters or fewer."}), 400

    # --- RAG chain invocation -----------------------------------------------
    logger.info(
        "Received chat request.",
        extra={"request_id": request_id, "msg_length": len(msg)},
    )

    try:
        response = rag_chain.invoke({"input": msg})
        answer = response.get("answer", "I could not find a relevant answer.")
    except Exception:
        logger.exception(
            "RAG chain invocation failed.",
            extra={"request_id": request_id},
        )
        return (
            "An internal error occurred. Please try again later.",
            500,
        )

    logger.info(
        "Chat request completed.",
        extra={"request_id": request_id, "answer_length": len(answer)},
    )
    return str(answer)


@app.route("/health")
def health():
    """Liveness probe for load balancers and container orchestrators.

    Returns:
        JSON ``{"status": "ok"}`` with HTTP 200.
    """
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
