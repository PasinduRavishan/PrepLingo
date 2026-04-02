"""
langchain_layer/memory/session_memory.py

WHAT IS CONVERSATION MEMORY IN LANGCHAIN?

  LLMs are STATELESS — they don't remember previous messages.
  Each API call to Gemini is completely independent.

  Memory bridges this gap by:
  1. Storing the conversation history
  2. Injecting it into each new prompt as "history"

  So the LLM SEEMS to remember — but really, we're replaying the history
  as part of every prompt.

  AI:   "Tell me about your blockchain project."
  User: "I built a supply chain tracker."
  AI:   "How did you handle consensus?" ← AI "remembers" the previous answer
                                           because we injected it into the prompt

WINDOW MEMORY vs FULL BUFFER MEMORY:
  Full Buffer: keeps EVERY message. Problem: prompts get huge fast.
  Window Buffer: keeps only the LAST K exchanges.
    - Old exchanges are cut off (first in, first out)
    - K=6 means last 6 Q&A pairs = ~12 messages
    - For an 8-question interview, we keep almost everything

WHY PER-SESSION MEMORY:
  Each interview session needs its OWN memory object.
  We can't share memory across sessions — User A's interview
  would bleed into User B's session.

  We store memory objects in a dict keyed by session_id.
  In production, this would use Redis. For now, in-memory dict is fine.

  { 1: ConversationBufferWindowMemory, 2: ConversationBufferWindowMemory, ... }
"""

from langchain_core.messages import AIMessage, HumanMessage

# In-memory store: { session_id (int) -> list[BaseMessage] }
# We keep the latest 6 exchanges = 12 messages.
_session_memories: dict[int, list] = {}
_MAX_EXCHANGES = 6
_MAX_MESSAGES = _MAX_EXCHANGES * 2


def get_or_create_memory(session_id: int) -> list:
    """
    Get existing memory for a session, or create new memory.
    
    Call this at the start of every /message request.
    
    Keeps last 6 exchanges (12 messages: Human + AI per exchange).
    Returns a list of LangChain message objects compatible with
    ChatPromptTemplate MessagesPlaceholder.
    """
    if session_id not in _session_memories:
        _session_memories[session_id] = []
    return _session_memories[session_id]


def save_exchange(session_id: int, user_answer: str, ai_question: str):
    """
    Save an exchange (user answer + AI question) to memory.
    
    Call this AFTER each successful /message request.
    
    Args:
        session_id: The interview session
        user_answer: What the user said
        ai_question: What the AI replied with (the next question)
    """
    history = get_or_create_memory(session_id)
    history.append(HumanMessage(content=user_answer))
    history.append(AIMessage(content=ai_question))

    # Sliding window: keep only the latest 6 exchanges.
    if len(history) > _MAX_MESSAGES:
        del history[:-_MAX_MESSAGES]


def get_history(session_id: int) -> list:
    """
    Get the conversation history as a list of Message objects.
    
    Returns empty list if session not found (handles new sessions gracefully).
    
    The list is injected into the prompt at the MessagesPlaceholder:
        ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),  ← here
            ("human", HUMAN_TEMPLATE),
        ])
    """
    if session_id not in _session_memories:
        return []
    return _session_memories[session_id]


def clear_memory(session_id: int):
    """
    Clear session memory when interview ends.
    Frees up memory resources.
    """
    if session_id in _session_memories:
        del _session_memories[session_id]
