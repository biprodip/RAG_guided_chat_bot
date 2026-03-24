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
GET  /       Serve the chat web interface (``templates/chat.html``).
POST /get    Accept a form field ``msg``, run the RAG chain, return the answer
             as plain text.

Run with::

    python app.py           # development
    gunicorn app:app        # production (recommended)
"""

from flask import Flask, render_template, jsonify, request
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os


app = Flask(__name__)


load_dotenv(override=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


embeddings = download_hugging_face_embeddings()

index_name = "rag-guided-chatbot" 

# Embed each chunk and upload the embeddings into Pinecone database index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)


retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":2})

chatModel = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)



@app.route("/")
def index():
    """Render the chat web interface.

    Returns:
        Rendered ``chat.html`` template.
    """
    return render_template('chat.html')


@app.route("/get", methods=["GET", "POST"])
def chat():
    """Process a user message and return the RAG-generated answer.

    Reads the ``msg`` field from the submitted form, invokes the retrieval
    chain, and returns the answer string as plain text.

    Returns:
        str: Concise answer (≤ 2 sentences) grounded in the retrieved context.
    """
    msg = request.form["msg"]
    input = msg
    print(input)
    response = rag_chain.invoke({"input": msg})
    print("Response : ", response["answer"])
    return str(response["answer"])



if __name__ == '__main__':
    app.run(host="0.0.0.0", port= 8080, debug= True)