"""
langchain_layer/chains/evaluation_chain.py

THE EVALUATION CHAIN — Scoring Answers with Structured Output

THE PROBLEM:
  LLMs return TEXT. But we need STRUCTURED DATA (a Python dict with scores).
  
  Without structure, we'd get:
    "The answer was quite good! I'd give it maybe a 7 out of 10 for technical
     accuracy, though they missed mentioning caching..."
  
  We can't easily parse that into a database row.

THE SOLUTION: JsonOutputParser + Response Schema
  We tell the LLM EXACTLY what format to return:
  {
    "technical_correctness": 7,
    "depth_of_explanation": 6,
    "clarity": 8,
    "overall_score": 7,
    "strengths": ["Clear explanation", "Good examples"],
    "weaknesses": ["Missed caching", "No mention of CDN"],
    "suggestions": ["Study cache-aside pattern"]
  }

  The parser:
  1. Instructs the LLM to return JSON (via format_instructions in the prompt)
  2. Parses the response text as JSON
  3. Returns a Python dict

HOW IT RUNS IN THE SYSTEM:
  After QuestionChain generates the next question AND saves the user's answer,
  EvaluationChain runs on the SAME user answer to score it.
  
  Both chains run in sequence (not parallel, to avoid rate limits):
    user_answer → QuestionChain → next_question (saved to DB)
    user_answer → EvaluationChain → evaluation (saved to DB)
  
  The frontend gets BOTH in the same API response.

EVALUATION PROMPT DESIGN:
  Key: we give the LLM the IDEAL answer context (from RAG knowledge),
  so it knows what a GOOD answer looks like before scoring.
"""

import json
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel
from app.config import get_settings

settings = get_settings()

# Use a slightly lower temperature for evaluation — we want consistent scores
# temperature=0.1 means the LLM sticks to the task rather than being creative
llm = ChatGroq(
    model=settings.groq_model,
    groq_api_key=settings.groq_api_key,
    temperature=0.1,
)


class EvaluationSchema(BaseModel):
    """
    The JSON structure we expect from the LLM.
    JsonOutputParser uses this to validate the LLM's response.
    
    If the LLM returns invalid JSON or wrong field names,
    the parser will raise an error we can catch and retry.
    """
    technical_correctness: int  # 0-10: Is the answer factually accurate?
    depth_of_explanation: int   # 0-10: Did they explain deeply enough?
    clarity: int                # 0-10: Was it well-communicated?
    overall_score: int          # 0-10: Weighted combined score
    strengths: list[str]        # What they did well
    weaknesses: list[str]       # What was missing or wrong
    suggestions: list[str]      # Actionable things to study/improve


# JsonOutputParser wraps our schema and auto-generates formatting instructions
parser = JsonOutputParser(pydantic_object=EvaluationSchema)

EVALUATION_PROMPT_TEMPLATE = """You are an expert interview evaluator.

INTERVIEW QUESTION THAT WAS ASKED:
{question}

CANDIDATE'S ANSWER:
{user_answer}

IDEAL ANSWER CONTEXT (from knowledge base — what a good answer covers):
{context}

INTERVIEW TYPE: {interview_type}

Evaluate the candidate's answer fairly. Consider:
- What they got RIGHT (even if incomplete)
- What KEY POINTS they MISSED (compared to ideal answer context)
- How CLEARLY they communicated their answer

SCORING GUIDE:
  0-3: Poor — major gaps, factual errors
  4-5: Below average — basic understanding, lacks depth
  6-7: Average — correct but incomplete
  8-9: Good — thorough with minor gaps
  10:  Excellent — comprehensive and well-communicated

{format_instructions}

Respond ONLY with the JSON object. No other text.
"""

evaluation_prompt = PromptTemplate(
    template=EVALUATION_PROMPT_TEMPLATE,
    input_variables=["question", "user_answer", "context", "interview_type"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# The evaluation chain
# PromptTemplate → LLM → JsonOutputParser
evaluation_chain = evaluation_prompt | llm | parser


async def evaluate_answer(
    question: str,
    user_answer: str,
    context: str,
    interview_type: str,
) -> dict:
    """
    Evaluate a candidate's answer and return structured scores.
    
    Args:
        question: The AI question that was asked
        user_answer: The candidate's answer
        context: RAG-retrieved ideal answer context
        interview_type: For adjusting evaluation criteria
    
    Returns:
        dict with keys: technical_correctness, depth_of_explanation,
                        clarity, overall_score, strengths, weaknesses, suggestions
    
    Error handling:
        If LLM returns malformed JSON, we return a default score
        rather than crashing the whole interview session.
    """
    try:
        result = await evaluation_chain.ainvoke({
            "question": question,
            "user_answer": user_answer,
            "context": context,
            "interview_type": interview_type,
        })
        return result
    except Exception as e:
        # Fallback — never break the interview due to evaluation failure
        print(f"⚠️ Evaluation chain error: {e}")
        return {
            "technical_correctness": 5,
            "depth_of_explanation": 5,
            "clarity": 5,
            "overall_score": 5,
            "strengths": ["Answer was provided"],
            "weaknesses": ["Evaluation unavailable for this answer"],
            "suggestions": ["Review the topic and try again"],
        }
