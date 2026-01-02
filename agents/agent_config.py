"""
Gemini API Configuration using OpenAI SDK syntax.

Uses the OpenAI SDK with base_url override to connect to Gemini API.
This provides familiar API patterns while using Gemini's free tier.
"""

import os
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI  # Changed from 'agents' to 'openai'

load_dotenv()

logger = logging.getLogger("agents")

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

# Validate API key before initializing client
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set it in your .env file or environment."
    )

# Initialize OpenAI client with Gemini base URL
client = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL
)

# Model configuration
MODEL = GEMINI_MODEL
TEMPERATURE = GEMINI_TEMPERATURE
MAX_TOKENS = GEMINI_MAX_TOKENS


def verify_gemini_config() -> bool:
    """
    Verify that Gemini API is properly configured.

    Returns:
        bool: True if configuration is valid, False otherwise
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        return False

    if not GEMINI_API_KEY.startswith("AIza"):
        logger.warning("GEMINI_API_KEY doesn't start with expected prefix 'AIza'")

    logger.info(f"Gemini configured: model={MODEL}, temp={TEMPERATURE}")
    return True


async def get_chat_completion(  # Made async since using AsyncOpenAI
    messages: list,
    tools: list = None,
    temperature: float = None,
    max_tokens: int = None
):
    """
    Get a chat completion from Gemini API.

    Args:
        messages: List of message dicts with 'role' and 'content'
        tools: Optional list of tool definitions for function calling
        temperature: Optional temperature override
        max_tokens: Optional max_tokens override

    Returns:
        OpenAI ChatCompletion response object
    """
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature or TEMPERATURE,
        "max_tokens": max_tokens or MAX_TOKENS,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        response = await client.chat.completions.create(**kwargs)  # Added await
        return response
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise


# Verify configuration on module load
if GEMINI_API_KEY:
    logger.info("Gemini API configured")
else:
    logger.warning("GEMINI_API_KEY not set - chat features will not work")