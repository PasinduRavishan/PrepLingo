"""
langchain_layer/prompts/technical_prompt.py

WHAT IS A PROMPT TEMPLATE?
  Instead of hardcoding prompts as plain strings, LangChain's PromptTemplate
  lets you define prompts with VARIABLES (like {context}, {history}).
  At runtime, variables get filled in with actual content.

  Think of it like an f-string on steroids:
    "Hello {name}!" → at runtime → "Hello Ravi!"
  But for LLMs:
    "Ask about {topic} to candidate with context {context}..."

WHY SYSTEM vs HUMAN MESSAGES?
  Modern LLMs (Gemini, GPT-4) use a "chat" format with roles:
  - "system"  → Instructions for the AI's BEHAVIOR (persona, rules)
  - "human"   → What the "user" says (in our case, we inject the task)
  - "ai"      → The AI's past responses (conversation history)

  The system prompt sets the AI's PERSONA and CONSTRAINTS.
  It runs EVERY turn but only the task/question changes.

TEMPLATE VARIABLES:
  {context}          → RAG retrieved chunks (resume + domain knowledge)
  {history}          → Conversation so far (from LangChain memory)
  {user_answer}      → The candidate's latest answer
  {question_number}  → "Question 3 of 8"
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ── System Prompt — Sets the AI's Persona ─────────────────────────
TECHNICAL_SYSTEM = """You are a senior software engineer conducting a technical interview.
Your role is to fairly assess the candidate's technical knowledge and problem-solving ability.

CONTEXT (retrieved from knowledge base and candidate's resume):
{context}

RULES:
- Ask ONE clear, specific question at a time
- Start with topics FROM THE CANDIDATE'S resume, then expand to adjacent areas
- Progress from foundational to advanced concepts as the interview goes on
- If the candidate gives a vague answer, probe deeper with a follow-up
- Be professional and encouraging, but thorough
- Do NOT give away answers or hints

INTERVIEW PROGRESS: Question {question_number} of 8
"""

# ── Human Turn Template — The Current Task ────────────────────────
TECHNICAL_HUMAN = """The candidate just answered:
"{user_answer}"

Based on their answer and the context provided, ask the NEXT technical interview question.
If this is question 1, introduce yourself briefly (e.g., "Hi, I'm your technical interviewer today...")
then ask the first question about a skill or technology from their profile.

Keep your response to just the question (and brief intro if first question).
Do not evaluate or comment on their answer — just ask the next question.
"""

technical_prompt = ChatPromptTemplate.from_messages([
    ("system", TECHNICAL_SYSTEM),
    MessagesPlaceholder(variable_name="history"),   # LangChain memory injects here
    ("human", TECHNICAL_HUMAN),
])
