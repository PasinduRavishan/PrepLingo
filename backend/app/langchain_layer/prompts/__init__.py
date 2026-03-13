"""
langchain_layer/prompts/__init__.py

WHY A HELPER FUNCTION TO GET THE PROMPT?
  We have 4 different prompts — one per interview type.
  The session_service.py needs to pick the RIGHT one based on the
  interview_type field in the database.

  Without this helper, session_service would need to import all 4
  and write its own if/else chain. This keeps that logic here.

  clean call:  prompt = get_prompt_for_type("technical")
  messy call:  if interview_type == "technical": prompt = technical_prompt ...
"""

from app.langchain_layer.prompts.technical_prompt import technical_prompt
from app.langchain_layer.prompts.system_design_prompt import system_design_prompt
from app.langchain_layer.prompts.behavioral_prompt import behavioral_prompt
from app.langchain_layer.prompts.resume_interview_prompt import resume_interview_prompt


# Map string → prompt template
_PROMPT_MAP = {
    "technical":     technical_prompt,
    "system_design": system_design_prompt,
    "behavioral":    behavioral_prompt,
    "resume":        resume_interview_prompt,
}


def get_prompt_for_type(interview_type: str):
    """
    Get the ChatPromptTemplate for a given interview type.

    Args:
        interview_type: One of "technical", "system_design", "behavioral", "resume"

    Returns:
        The matching ChatPromptTemplate

    Raises:
        ValueError if interview_type is not recognized
    """
    prompt = _PROMPT_MAP.get(interview_type)
    if not prompt:
        raise ValueError(
            f"Unknown interview_type: '{interview_type}'. "
            f"Valid types: {list(_PROMPT_MAP.keys())}"
        )
    return prompt
