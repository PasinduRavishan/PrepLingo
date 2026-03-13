# SPEC 02 — RAG Design (All 4 Interview Types)

**Status:** Draft — Pending Knowledge Base Source Decisions

---

## Core Principle: Every Interview Type Uses RAG

The RAG pipeline is the backbone of PrepLingo. There are TWO retrieval sources always active:

```
At every AI turn:
  RETRIEVE from:
  ├── [1] User's Resume Chunks     → personalization, CV-specific context
  └── [2] Domain Knowledge Chunks  → grounded, accurate interview content

  COMBINE into prompt → LLM generates next question / evaluation
```

This means every question the AI asks is grounded in BOTH what the user knows
(from their resume) AND what real interview guides say about that topic.

---

## How RAG Works in LangChain (Step by Step)

### Phase A — Ingestion (One-Time Setup)

```
                    KNOWLEDGE BASE INGESTION

Raw Documents (PDF, .md, .txt)
        ↓
Document Loaders  [LangChain: PyMuPDFLoader, TextLoader]
        ↓
Text Splitter     [LangChain: RecursiveCharacterTextSplitter]
  chunk_size=800, chunk_overlap=100
        ↓
Embedding Model   [OpenAI: text-embedding-3-small  OR
                   HuggingFace: all-MiniLM-L6-v2]
        ↓
Vector Store      [FAISS / ChromaDB]
  Stored with metadata: {source, interview_type, topic}
```

### Phase B — Resume Ingestion (Per User)

```
User uploads PDF
        ↓
PyMuPDFLoader → raw text
        ↓
RecursiveCharacterTextSplitter (smaller chunks: 400 tokens)
        ↓
Same Embedding Model
        ↓
User-specific namespace in Vector Store
  metadata: {user_id, section: "skills"/"projects"/"experience"}
```

### Phase C — Retrieval (At Interview Time)

```
User sends an answer
        ↓
Query = f"{interview_type_context} + {user_answer_snippet}"
        ↓
Retriever.get_relevant_documents(query, k=4)
  → 2 chunks from resume store
  → 2 chunks from domain knowledge store
        ↓
RetrievedContext = join(chunks)
        ↓
PromptTemplate.format(
  context=RetrievedContext,
  history=ConversationMemory,
  user_answer=user_answer
)
        ↓
LLM → Next Question or Evaluation
```

---

## Interview Type 1: Resume-Based Interview

### Goal
Deep-dive into the user's specific projects, skills, and experience.
The CV IS the knowledge base. The AI acts like a recruiter who has studied the resume.

### RAG Knowledge Sources

| Source | Content | Format |
|---|---|---|
| **User's Resume** | Projects, skills, experience, education | PDF (per user) |
| Interview Coaching Guides | How to structure project explanations (STAR for projects) | .md / .txt |
| Common Resume-based Q patterns | "Tell me about X project", "How did you handle Y challenge" | .txt or Q&A format |
| Technical depth guides | Follow-up patterns for common tech stacks (React, Node, etc.) | .txt |

### How CV Feeds RAG
- Resume is chunked by section: Skills, Projects (one chunk per project), Experience, Education
- Each project chunk includes: name, description, tech stack, outcomes
- When AI asks about "Project X", it retrieves the project chunk + interview coaching guide

### Example Flow
```
Resume chunk retrieved:
  "Project: Blockchain Supply Chain using Hyperledger Fabric, Docker.
   Implemented smart contracts for tracking goods."

Knowledge chunk retrieved:
  "When asking about blockchain projects, probe: consensus mechanism,
   scalability decisions, data privacy approach."

AI Question generated:
  "You mentioned using Hyperledger Fabric in your supply chain project.
   Can you explain the consensus mechanism you chose and why?"
```

### Documents to Collect
- [ ] "How to answer project-based interview questions" guides
- [ ] Common behavioral-technical hybrid questions
- [ ] "STAR method for projects" framework docs
- [ ] Tech-specific "what interviewers look for" articles

---

## Interview Type 2: Technical Knowledge Interview

### Goal
Test CS fundamentals and engineering knowledge. Questions are anchored to the
technologies in the user's CV, then expand to related concepts.

### RAG Knowledge Sources

| Source | Content | Format |
|---|---|---|
| **User's Resume** | Skills, technologies used | PDF (per user) |
| CS Fundamentals | Data structures, algorithms, complexity | .md files |
| Backend Engineering | REST, GraphQL, HTTP, caching, queuing | .md files |
| Databases | SQL vs NoSQL, indexing, ACID, CAP theorem | .md files |
| Programming Concepts | OOP, functional programming, design patterns | .md files |
| Language-Specific | Python/JS/Java-specific interview concepts | .md per language |
| Interview Q&A Sets | Common technical interview Q&As with explanations | .txt Q&A format |

### How CV Connects
- AI extracts skills from CV (e.g., "Python, MongoDB, React")
- First retrieves domain knowledge matching those technologies
- Starts with topics the user knows, then expands to adjacent concepts

### Example Flow
```
Resume chunk retrieved:
  "Skills: MongoDB, Express.js, React, Node.js (MERN stack)"

Knowledge chunk retrieved:
  "MongoDB uses document-based storage. Key interview topics:
   indexing strategies, aggregation pipeline, sharding vs replication."

AI Question generated:
  "Since you've worked with MongoDB in your projects, explain how
   you would design an indexing strategy for a high-read application."
```

### Documents to Collect
- [ ] "System design interview handbook" (free GitHub resources)
- [ ] LeetCode/InterviewBit concept articles
- [ ] "Backend engineering concepts" article sets
- [ ] Database concept guides (SQL/NoSQL)
- [ ] CS fundamentals cheat sheets

---

## Interview Type 3: System Design Interview

### Goal
Test ability to design scalable systems. Problems are anchored to the
user's experience level and project domain, then scaled up.

### RAG Knowledge Sources

| Source | Content | Format |
|---|---|---|
| **User's Resume** | Project domain, tech stack, scale of projects | PDF (per user) |
| Architecture Patterns | Load balancing, caching, CDN, sharding, replication | .md files |
| Real-World System Designs | URL shortener, messaging system, Netflix, Uber, Twitter | .md per system |
| Scalability Guides | Horizontal vs vertical scaling, microservices vs monolith | .md files |
| Distributed Systems | CAP theorem, consistency models, consensus algorithms | .md files |
| API Design | REST vs GraphQL vs gRPC, API gateway patterns | .md files |
| Database Selection | When to use SQL vs NoSQL vs cache vs search | .md files |

### How CV Connects
- If CV shows "built a real-time chat app" → AI picks messaging system design problems
- If CV shows "e-commerce backend" → AI picks product catalog design, cart system design
- AI anchors the design problem to something near the candidate's experience

### Example Flow
```
Resume chunk retrieved:
  "Project: Real-time chat system using Socket.io, Redis for pub/sub,
   MongoDB for message storage. Handled 100 concurrent users."

Knowledge chunk retrieved:
  "Designing scalable messaging systems: WebSockets vs SSE vs polling,
   message fan-out patterns, read vs write optimized storage."

AI Question generated:
  "You built a real-time chat system. Now design a messaging system
   like WhatsApp that needs to handle 10 million concurrent users.
   Where would you start?"
```

### Documents to Collect
- [ ] "System Design Primer" by Alex Xu (structured notes)
- [ ] ByteByteGo article summaries
- [ ] "Designing Data-Intensive Applications" key chapters (notes)
- [ ] Real architecture case studies (Twitter, Netflix, Uber — public blogs)
- [ ] Scalability patterns reference

---

## Interview Type 4: Behavioral Interview

### Goal
Test soft skills, communication, and professional situations using the STAR method.
Questions are grounded in the candidate's actual CV experiences.

### RAG Knowledge Sources

| Source | Content | Format |
|---|---|---|
| **User's Resume** | Projects, experience, roles, teams | PDF (per user) |
| STAR Method Guide | Situation, Task, Action, Result framework | .md |
| Behavioral Question Bank | 100+ common behavioral questions by category | .txt Q&A |
| Answer Evaluation Rubric | What makes a strong behavioral answer | .md |
| Soft Skills Framework | Leadership, teamwork, conflict, deadlines, failure | .md |
| Common Themes | "Tell me about a challenge", "Describe a conflict" patterns | .md |

### How CV Connects
- AI scans CV for roles, team sizes, project counts, timelines
- Generates situational questions grounded in the user's actual experience
- "You led a team of 3 for your capstone project — tell me about a conflict..."

### Example Flow
```
Resume chunk retrieved:
  "Led a team of 4 to deliver a blockchain supply chain system
   within 3 months. Used Agile methodology."

Knowledge chunk retrieved:
  "STAR method: When asking about team conflicts, probe for: what the
   conflict was, what role the candidate played, and the resolution outcome."

AI Question generated:
  "You led a team of 4 on a tight 3-month deadline. Tell me about a
   situation where you had a disagreement with a teammate and how you
   resolved it."
```

### Documents to Collect
- [ ] STAR method comprehensive guide
- [ ] "Top 50 behavioral interview questions" with ideal answer structures
- [ ] Soft skills competency frameworks
- [ ] Amazon Leadership Principles explanations (popular in interviews)
- [ ] "How to tell your project story" coaching guides

---

## Unified RAG Pipeline Design

### Dual Retriever Strategy

```python
# Pseudocode — LangChain LCEL

def build_retriever(user_id: str, interview_type: str):
    resume_retriever = vector_store.as_retriever(
        search_kwargs={"filter": {"user_id": user_id}, "k": 2}
    )
    knowledge_retriever = vector_store.as_retriever(
        search_kwargs={"filter": {"type": interview_type}, "k": 3}
    )
    return MergerRetriever(retrievers=[resume_retriever, knowledge_retriever])
```

### Prompt Structure (All 4 Types Follow This Pattern)

```
SYSTEM PROMPT:
  You are an expert {interview_type} interviewer.
  Your goal is to assess the candidate's ability.
  Use the context below to ask grounded, specific questions.

CONTEXT (from RAG):
  [Resume chunks relevant to current conversation]
  [Domain knowledge chunks relevant to current topic]

CONVERSATION HISTORY:
  [Last 6 messages in memory]

CURRENT TASK:
  The candidate just answered: "{user_answer}"
  Now ask the next relevant question OR generate an evaluation.
```

---

## Knowledge Base — Document Sources Plan

### Free / Open Sources to Use

| Resource | Interview Type | Format | Location |
|---|---|---|---|
| System Design Primer (GitHub) | System Design | Markdown | github.com/donnemartin/system-design-primer |
| Tech Interview Handbook (GitHub) | Technical, Behavioral | Markdown | github.com/yangshun/tech-interview-handbook |
| ByteByteGo articles (public) | System Design | Web scrape / manual | blog.bytebytego.com |
| InterviewBit concepts | Technical | Manual extract | interviewbit.com |
| STAR method guides | Behavioral | Manual write | — |
| Amazon LP guides | Behavioral | Manual write | — |
| "Cracking the Coding Interview" concepts | Technical | Manual notes | — |

### Document Organization in Repo

```
backend/
└── knowledge_base/
    ├── technical/
    │   ├── databases.md
    │   ├── backend_concepts.md
    │   ├── data_structures.md
    │   ├── networking.md
    │   └── language_specific/
    │       ├── python.md
    │       ├── javascript.md
    │       └── java.md
    ├── system_design/
    │   ├── patterns/
    │   │   ├── caching.md
    │   │   ├── load_balancing.md
    │   │   ├── database_design.md
    │   │   └── api_design.md
    │   └── case_studies/
    │       ├── url_shortener.md
    │       ├── messaging_system.md
    │       ├── social_feed.md
    │       └── video_streaming.md
    ├── behavioral/
    │   ├── star_method.md
    │   ├── common_questions.md
    │   ├── soft_skills_framework.md
    │   └── leadership_principles.md
    └── resume_interview/
        ├── project_questions.md
        ├── techstack_deepdive.md
        └── strengths_weaknesses.md
```

---

## Chunking Strategy

| Document Type | Chunk Size | Overlap | Rationale |
|---|---|---|---|
| Domain Knowledge .md | 800 tokens | 100 tokens | Concepts need full context |
| System Design Case Studies | 600 tokens | 80 tokens | Each section is self-contained |
| Q&A Sets | 400 tokens | 50 tokens | One Q&A pair per chunk |
| Resume Sections | 400 tokens | 50 tokens | Project = one chunk |
| Behavioral Guides | 500 tokens | 80 tokens | Framework steps need grouping |

---

## Metadata Schema for Vector Documents

```python
{
  "source": "system_design/caching.md",
  "interview_type": "system_design",  # or "technical"/"behavioral"/"resume"
  "topic": "caching",
  "subtopic": "cache_invalidation",
  "user_id": None,  # None for static knowledge, user_id for resume chunks
  "section": None   # "projects"/"skills" for resume chunks
}
```

This metadata enables filtered retrieval:
- "Give me only system_design chunks about caching"
- "Give me only resume chunks for user_123"
