"""
langchain_layer/chains/question_chain.py

THIS IS THE HEART OF THE AI INTERVIEW SYSTEM.

THE QUESTION CHAIN — Full LCEL Explanation:

  LCEL = LangChain Expression Language
  It uses the | (pipe) operator to chain components.
  Data flows LEFT → RIGHT through each component.

  Our chain:
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │  input_dict                                          │
  │   {user_answer, question_number, history}            │
  │       │                                              │
  │       ├──[retriever]──[format_docs]──→ {context}    │
  │       │                                              │
  │       ▼ (all variables collected into dict)          │
  │                                                      │
  │  {context, history, user_answer, question_number}    │
  │       │                                              │
  │       ▼                                              │
  │  [prompt template]  ← fills in all variables        │
  │       │                                              │
  │       ▼                                              │
  │  [ChatGroq]  ← calls Groq API                   │
  │       │                                              │
  │       ▼                                              │
  │  [StrOutputParser]  ← extracts text from AI response│
  │       │                                              │
  │       ▼                                              │
  │  "Tell me about the scaling approach you'd use..."   │
  │  (the next interview question, as a plain string)    │
  └──────────────────────────────────────────────────────┘

WHY RunnablePassthrough and RunnableLambda?
  When building LCEL chains, you often need to:
  - Pass a value through unchanged: RunnablePassthrough()
  - Apply a function to transform data: RunnableLambda(my_function)
  
  These are the LCEL "glue" components.

WHY async (ainvoke not invoke)?
  LLM API calls are I/O-bound (waiting for network response).
  async lets FastAPI handle OTHER requests while waiting for Groq.
  Never block the server with synchronous LLM calls!
"""

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from app.langchain_layer.llm_factory import build_llm
from app.langchain_layer.retrievers.dual_retriever import format_retrieved_docs

# temperature=0.7: creative but focused — good balance for interview questions.
# Fallback to llama-3.1-8b-instant if primary hits rate limit (transparent).
llm = build_llm(temperature=0.7)


def build_question_chain(retriever, prompt):
    """
    Build a question generation chain for a specific interview type.
    
    Called ONCE per session. Reused for all 8 questions.
    
    Args:
        retriever: MergerRetriever (from dual_retriever.py)
                   This retriever knows which user's resume + which knowledge type
        prompt: The interview-type-specific ChatPromptTemplate
    
    Returns:
        A runnable LCEL chain. Invoke with:
        question = await chain.ainvoke({
            "user_answer": "I used Redis for caching...",
            "question_number": 3,
            "history": [...]  # from LangChain memory
        })
    
    HOW THE CHAIN PROCESSES THE INPUT:
    
    Step 1: Parallel input preparation
      The dict {...} creates variables in parallel:
      - "context": runs retriever on user_answer → formats docs as string
      - "history": passes through unchanged (from memory)
      - "user_answer": passes through unchanged
      - "question_number": passes through unchanged
    
    Step 2: Prompt template fills all variables into the prompt messages
    
    Step 3: LLM call — sends filled prompt to Groq
    
    Step 4: StrOutputParser — extracts the text content from Groq's response object
    """
    chain = (
        {
            # RunnableLambda wraps the retriever so it receives user_answer as input
            "context": (
                RunnableLambda(lambda x: x["user_answer"])  # extract user_answer
                | retriever                                  # retrieve relevant docs
                | RunnableLambda(format_retrieved_docs)      # format as string
            ),
            "history": RunnableLambda(lambda x: x.get("history", [])),
            "user_answer": RunnableLambda(lambda x: x["user_answer"]),
            "question_number": RunnableLambda(lambda x: x.get("question_number", 1)),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
