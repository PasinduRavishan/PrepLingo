"""
llm_factory.py — Centralized LLM builder with automatic fallback

WHY THIS FILE EXISTS:
  Both QuestionChain and EvaluationChain need a Groq LLM.
  Rather than each creating their own instance (and duplicating fallback logic),
  they both call build_llm() here.

HOW THE FALLBACK WORKS (LangChain built-in):
  LangChain's .with_fallbacks() wraps any Runnable. When the primary LLM raises
  an exception (e.g. RateLimitError from a Groq 429), LangChain automatically
  retries the same prompt with the fallback LLM — transparent to all callers.

  primary  = llama-3.3-70b-versatile  (best quality, used 99% of the time)
  fallback = llama-3.1-8b-instant     (fast, activates only on rate limit hit)

  The user never sees an error — the interview continues with the fallback model.
"""

import logging
from langchain_groq import ChatGroq
from groq import RateLimitError
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def build_llm(temperature: float = 0.7):
    """
    Build a Groq LLM with automatic fallback on rate limit.

    Args:
        temperature: Sampling temperature.
                     0.7 for question generation (creative but focused).
                     0.1 for evaluation (consistent, deterministic scores).

    Returns:
        A LangChain Runnable. Behaves exactly like ChatGroq but silently
        switches to the fallback model if the primary returns HTTP 429.
    """
    primary = ChatGroq(
        model=settings.groq_model,
        groq_api_key=settings.groq_api_key,
        temperature=temperature,
    )

    fallback = ChatGroq(
        model=settings.groq_fallback_model,
        groq_api_key=settings.groq_api_key,
        temperature=temperature,
    )

    # with_fallbacks() catches RateLimitError from primary and retries with fallback.
    # exceptions_to_handle limits fallback to only rate limits — other errors still raise.
    llm_with_fallback = primary.with_fallbacks(
        [fallback],
        exceptions_to_handle=(RateLimitError,),
    )

    logger.info(
        "LLM built: primary=%s fallback=%s",
        settings.groq_model,
        settings.groq_fallback_model,
    )
    return llm_with_fallback
