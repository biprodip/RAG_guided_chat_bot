"""
src/prompt.py
-------------
Defines the system-level instruction injected into every chat turn.

The prompt enforces three behaviours:
  1. **Domain specialisation** — the assistant identifies as a medical assistant.
  2. **Grounded answers** — responses must be based on the retrieved context
     supplied via the ``{context}`` placeholder, which is filled at runtime by
     the LangChain ``create_stuff_documents_chain``.
  3. **Conciseness** — answers are capped at two sentences to keep the UI
     readable and reduce token consumption.
"""

system_prompt = (
    "You are a Medical assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know. Use two sentences maximum and keep the "
    "answer concise."
    "\n\n"
    "{context}"
)