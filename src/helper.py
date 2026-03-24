"""
src/helper.py
-------------
Utility functions for the RAG pipeline:
  - Loading PDF documents from a directory
  - Stripping unnecessary document metadata
  - Splitting documents into fixed-size text chunks
  - Downloading and initialising the HuggingFace sentence-transformer embedding model

These helpers are consumed by both `store_index.py` (offline indexing) and
`app.py` (runtime embedding initialisation).
"""

from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_pdf_file(data: str) -> List[Document]:
    """Load all PDF files found in *data* directory.

    Uses :class:`DirectoryLoader` with :class:`PyPDFLoader` to recursively
    find and parse every ``*.pdf`` file under the given path.

    Args:
        data: Path to the directory containing PDF files.

    Returns:
        A list of :class:`~langchain_core.documents.Document` objects, one per
        page across all PDF files found.
    """
    loader = DirectoryLoader(data,
                             glob="*.pdf",
                             loader_cls=PyPDFLoader)
    documents = loader.load()
    return documents



def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """Strip all metadata except the ``source`` field from a list of documents.

    Pinecone imposes metadata size limits and the downstream RAG chain only
    needs the source path for citation purposes.  This function returns new
    :class:`~langchain_core.documents.Document` objects that preserve the
    original ``page_content`` but contain only ``{"source": <path>}`` in their
    metadata.

    Args:
        docs: Documents produced by :func:`load_pdf_file` (may contain rich
              metadata such as page numbers, author, creation date, etc.).

    Returns:
        A list of cleaned :class:`~langchain_core.documents.Document` objects
        with minimal metadata.
    """
    minimal_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={"source": src}
            )
        )
    return minimal_docs



def text_split(extracted_data: List[Document]) -> List[Document]:
    """Split documents into overlapping fixed-size text chunks.

    Uses :class:`~langchain_text_splitters.RecursiveCharacterTextSplitter` with
    a chunk size of **500 characters** and an overlap of **20 characters**.
    Smaller chunks improve retrieval precision; the overlap preserves sentence
    continuity across chunk boundaries.

    Args:
        extracted_data: Documents to split (typically the output of
            :func:`filter_to_minimal_docs`).

    Returns:
        A list of :class:`~langchain_core.documents.Document` text chunks
        ready for embedding and insertion into the vector store.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks



#Download the Embeddings from HuggingFace 
# def download_hugging_face_embeddings():
#     embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')  #this model return 384 dimensions
#     return embeddings

def download_hugging_face_embeddings() -> HuggingFaceEmbeddings:
    """Download and initialise the HuggingFace sentence-transformer embedding model.

    Uses ``sentence-transformers/all-MiniLM-L6-v2`` which produces
    **384-dimensional** dense vectors.  The model runs on CPU and is cached
    locally by the ``sentence-transformers`` library after the first download.

    Returns:
        A :class:`~langchain_community.embeddings.HuggingFaceEmbeddings`
        instance configured for CPU inference.
    """
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},                 # for CPU
        # encode_kwargs={"normalize_embeddings": True}, # for CPU
    )
    return embeddings