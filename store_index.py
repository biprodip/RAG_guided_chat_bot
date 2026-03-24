"""
store_index.py
--------------
One-time (or on-demand) script to build the Pinecone vector store index.

Pipeline
~~~~~~~~
1. Load all ``*.pdf`` files from the ``data/`` directory.
2. Strip unnecessary metadata, keeping only the ``source`` path.
3. Split the text into 500-character chunks (20-character overlap).
4. Initialise the HuggingFace sentence-transformer embedding model.
5. Create the Pinecone serverless index (``rag-guided-chatbot``) if it does
   not already exist — dimension 384, cosine similarity, AWS ``us-east-1``.
6. Embed all chunks and upsert them into the index.

Usage::

    python store_index.py

Required environment variables (``PINECONE_API_KEY``, ``OPENAI_API_KEY``)
are loaded from a ``.env`` file in the project root.

.. note::
   Re-running this script will **add** vectors to an existing index rather
   than replacing them.  To perform a clean re-index, delete the Pinecone
   index from the console first.
"""

from dotenv import load_dotenv
import os
from src.helper import load_pdf_file, filter_to_minimal_docs, text_split, download_hugging_face_embeddings
from pinecone import Pinecone 
from pinecone import ServerlessSpec 
from langchain_pinecone import PineconeVectorStore

load_dotenv()


PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


extracted_data=load_pdf_file(data='data/')
filter_data = filter_to_minimal_docs(extracted_data)
text_chunks=text_split(filter_data)

embeddings = download_hugging_face_embeddings()

pinecone_api_key = PINECONE_API_KEY
pc = Pinecone(api_key=pinecone_api_key)


index_name = "rag-guided-chatbot"  # change if desired

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)


docsearch = PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=index_name,
    embedding=embeddings, 
)