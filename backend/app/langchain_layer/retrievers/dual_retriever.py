"""
langchain_layer/retrievers/dual_retriever.py

THE DUAL RETRIEVER CONCEPT:

  At every AI turn in the interview, we need TWO types of context:

  1. WHO IS THIS PERSON? → resume_retriever
     - Fetches chunks from the user's CV
     - Gives the AI: "This person knows React, built a blockchain project..."
     - Enables PERSONALIZATION

  2. WHAT DOES A GOOD ANSWER LOOK LIKE? → knowledge_retriever
     - Fetches from our curated interview guides
     - Gives the AI: "Good system design answers mention caching, CDN, scaling..."
     - Enables GROUNDING (prevents hallucination)

  MERGED TOGETHER → the AI has BOTH context streams.
  It can ask: "You mentioned React in your blockchain project (resume chunk).
               How would you handle state management at scale? (knowledge chunk)"

HOW MERGERRETRIEVER WORKS:
  MergerRetriever runs BOTH retrievers in parallel (not sequential).
  It interleaves the results: [resume_chunk, knowledge_chunk, resume_chunk, ...]
  
  Total context = k_resume + k_knowledge chunks

QUERY STRATEGY:
  The query sent to both retrievers is constructed from:
  - The interview type context ("system design question about scalability")
  - A snippet of the user's latest answer
  This ensures retrieved chunks are RELEVANT to the current conversation moment.
"""

from langchain_core.runnables import RunnableLambda
from app.langchain_layer.vector_store.store_manager import (
    get_knowledge_retriever,
    get_resume_retriever,
)


def build_dual_retriever(
    guest_id: str,
    interview_type: str,
    k_knowledge: int = 2,
    k_resume: int = 1,
):
    """
    Build the dual retriever for an interview session.
    
    Call this ONCE when creating a session, reuse it for all turns.
    
    Args:
        guest_id: User's UUID (to fetch their resume chunks)
        interview_type: "technical" | "system_design" | "behavioral" | "resume"
        k_knowledge: How many domain knowledge chunks to retrieve per turn
        k_resume: How many resume chunks to retrieve per turn
    
    Returns:
        Runnable retriever — can be used like a single retriever:
        results = dual_retriever.invoke("your query")
    
    Example output documents:
        [
          Document(page_content="React uses virtual DOM for...", 
                   metadata={"source": "technical/frontend.md"}),
          Document(page_content="Candidate's project: Built e-commerce...",
                   metadata={"source": "resume", "guest_id": "abc-123"}),
          ...
        ]
    """
    resume_retriever = get_resume_retriever(guest_id=guest_id, k=k_resume)
    knowledge_retriever = get_knowledge_retriever(
        interview_type=interview_type, k=k_knowledge
    )

    def _merged_retrieve(query: str):
        # Keep retrieval resilient across LangChain versions by composing results here.
        resume_docs = resume_retriever.invoke(query)
        knowledge_docs = knowledge_retriever.invoke(query)

        # Interleave docs so resume context and knowledge context are both represented.
        merged = []
        max_len = max(len(resume_docs), len(knowledge_docs))
        for i in range(max_len):
            if i < len(resume_docs):
                merged.append(resume_docs[i])
            if i < len(knowledge_docs):
                merged.append(knowledge_docs[i])
        return merged

    return RunnableLambda(_merged_retrieve)


def format_retrieved_docs(docs: list) -> str:
    """
    Convert retrieved Document objects into a single formatted string
    for injection into the prompt.
    
    WHY A HELPER FUNCTION?
      LangChain retrievers return Document objects. Prompt templates need strings.
      This bridge converts between them.
    
    Output format:
        --- Source: technical/databases.md ---
        Database indexing creates a B-tree structure that...

        --- Source: resume ---
        Candidate's project: Blockchain Supply Chain using...
    """
    if not docs:
        return "No relevant context found."

    MAX_DOC_CHARS = 700
    formatted = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        content = (doc.page_content or "").strip()
        if len(content) > MAX_DOC_CHARS:
            content = content[:MAX_DOC_CHARS] + " ..."
        formatted.append(f"--- Source: {source} ---\n{content}")

    return "\n\n".join(formatted)
