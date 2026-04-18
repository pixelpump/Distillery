import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Iterator

load_dotenv()
load_dotenv(".local.env", override=True)

OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

SUMMARY_PROMPT = "Summarize the following article in a few concise bullet points. Be direct, no preamble. pay attention to typography and formatting. the text formatting returned should be compatible with simple html. Leave plenty of whitespace"

# Global variable to store API key
_openrouter_api_key = None

def set_openrouter_api_key(api_key: str):
    global _openrouter_api_key
    _openrouter_api_key = api_key

def get_openrouter_api_key() -> str:
    global _openrouter_api_key
    return _openrouter_api_key or os.getenv("OPENROUTER_API_KEY")


def _get_client() -> OpenAI:
    api_key = get_openrouter_api_key()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in the environment or settings.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def stream_summary(text: str) -> Iterator[str]:
    client = _get_client()
    stream = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": text},
        ],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
