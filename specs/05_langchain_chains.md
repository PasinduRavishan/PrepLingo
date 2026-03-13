# SPEC 05 — LangChain Chains Design

**Status:** ✅ SCAFFOLDED (Phase 0/1) — Full implementation in Phase 4/5
**Files:** `backend/app/langchain_layer/`

---

## LangChain Layer Overview

All AI logic is isolated in `langchain_layer/`. Nothing outside this folder
imports LangChain directly. Services call into this layer only.

```
app/
├── services/         ← Business logic (calls langchain_layer)
└── langchain_layer/
    ├── chains/       ← The actual LLM pipelines (LCEL chains)
    ├── prompts/      ← Prompt templates per interview type
    ├── retrievers/   ← Dual retriever (resume + knowledge)
    ├── memory/       ← Conversation history per session
    └── vector_store/ ← ChromaDB interface + embedding model
```

---

## LCEL — How LangChain Chains Work

LCEL (LangChain Expression Language) uses the `|` operator to chain components.
Data flows left → right, output of each step becomes input of next.

```
input_dict
    │
    ├── retriever  →  format_docs  →  "context" string
    │
    ├── passthrough  →  "history" (from memory)
    │
    ├── passthrough  →  "user_answer"
    │
    └── passthrough  →  "question_number"
                │
                ▼ (dict assembled)
        ChatPromptTemplate  ← fills all variables into system+human messages
                │
                ▼
        ChatGoogleGenerativeAI  ← sends to Gemini API, gets response
                │
                ▼
        StrOutputParser  ← extracts text from AIMessage object
                │
                ▼
        "Tell me about how you handled caching in your project."
```

---

## QuestionChain

**File:** `langchain_layer/chains/question_chain.py`
**Purpose:** Generate the next interview question given context + history + user's answer

**Input:**
```python
{
    "user_answer": "I used Redis for caching with a TTL of 5 minutes.",
    "question_number": 3,
    "history": [...]  # List of HumanMessage/AIMessage objects from memory
}
```

**Output:** Plain string — the next question to ask

**LCEL Chain:**
```
{context, history, user_answer, question_number}
    | PromptTemplate (per interview type)
    | ChatGoogleGenerativeAI (temperature=0.7)
    | StrOutputParser
    → "Why did you choose a 5-minute TTL specifically? How did you determine that value?"
```

---

## EvaluationChain

**File:** `langchain_layer/chains/evaluation_chain.py`
**Purpose:** Score the user's answer across multiple dimensions

**Input:**
```python
{
    "question": "How does database indexing work?",
    "user_answer": "Indexing creates a B-tree structure...",
    "context": "RAG-retrieved ideal answer context",
    "interview_type": "technical"
}
```

**Output:** Structured dict (via JsonOutputParser)
```python
{
    "technical_correctness": 7,
    "depth_of_explanation": 6,
    "clarity": 8,
    "overall_score": 7,
    "strengths": ["Correct explanation of B-tree", "Good example"],
    "weaknesses": ["Missed Hash index type", "No mention of composite indexes"],
    "suggestions": ["Read about Hash indexes", "Practice composite index scenarios"]
}
```

**Why JsonOutputParser not just StrOutputParser?**
- StrOutputParser → plain text → we'd need to regex-parse it (fragile)
- JsonOutputParser → tells LLM to output JSON → parses it → Python dict (reliable)
- Parser includes format instructions in the prompt automatically

---

## Dual Retriever

**File:** `langchain_layer/retrievers/dual_retriever.py`
**Purpose:** Retrieve BOTH resume chunks AND domain knowledge simultaneously

```
Session starts:
  build_dual_retriever(
    guest_id="abc-123",
    interview_type="technical"
  )
  → MergerRetriever (resume_retriever + knowledge_retriever)

At each AI turn:
  dual_retriever.invoke("How does indexing work in the context of MongoDB?")
  →
  resume_retriever runs  →  [chunk: "Used MongoDB in e-commerce project"]
  knowledge_retriever runs →  [chunk: "MongoDB uses B-tree indexes by default..."]
  
  MergerRetriever merges → [resume_chunk_1, knowledge_chunk_1, resume_chunk_2, knowledge_chunk_2]
```

**Why 2 from resume + 3 from knowledge (default)?**
- Resume gives WHO/WHAT context (personalization)
- Knowledge gives WHAT IS GOOD context (grounding)
- 3 knowledge > 2 resume because domain correctness matters more for evaluation

---

## Conversation Memory

**File:** `langchain_layer/memory/session_memory.py`
**Purpose:** Store conversation per session; inject history into prompts

```python
# At message N:
history = get_history(session_id)  # List of past messages
# [HumanMessage("I used Redis"), AIMessage("Why Redis over Memcached?"), ...]

# After generating question + evaluation:
save_exchange(session_id, user_answer, ai_question)
# Adds to memory window

# Memory window: k=6 means max 6 exchanges (12 messages total)
# When session has 8 questions, window holds all of them
```

**Why WindowMemory not FullMemory?**
- Full memory grows unbounded → prompts exceed Gemini's context limit
- Window(6) = enough to track the interview flow without overflow
- For 8-question sessions, we never actually hit the window limit

---

## Prompt Templates — Per Type

Each interview type has its own prompt file:

| File | Persona | Focus |
|------|---------|-------|
| `technical_prompt.py` | Senior engineer | CS concepts, tech depth |
| `system_design_prompt.py` | Staff engineer | Architecture, scale |
| `behavioral_prompt.py` | Hiring manager | STAR stories, soft skills |
| `resume_interview_prompt.py` | Recruiter | CV deep-dive, decisions |

**Common Structure (all 4):**
```python
ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),     ← Persona + rules + {context} + {question_number}
    MessagesPlaceholder("history"), ← LangChain memory injects here
    ("human", HUMAN_TEMPLATE),     ← Current task with {user_answer}
])
```

---

## Full Chain Assembly (Phase 5)

When `POST /api/session/{id}/message` is called:

```python
# 1. Load session from DB
session = db.get(InterviewSession, session_id)

# 2. Build dual retriever (once per session, ideally cached)
retriever = build_dual_retriever(session.guest_id, session.interview_type)

# 3. Get the right prompt for this interview type
prompt = get_prompt_for_type(session.interview_type)

# 4. Build question chain
q_chain = build_question_chain(retriever, prompt)

# 5. Get conversation history from memory
history = get_history(session_id)

# 6. Generate next question (async — doesn't block server)
ai_question = await q_chain.ainvoke({
    "user_answer": user_message,
    "question_number": session.question_count + 1,
    "history": history,
})

# 7. Evaluate the user's answer
evaluation = await evaluate_answer(
    question=last_ai_question,
    user_answer=user_message,
    context=retrieved_context,
    interview_type=session.interview_type,
)

# 8. Save everything to DB
# 9. Update memory
# 10. Return to frontend
```
