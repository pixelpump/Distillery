import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Iterator

load_dotenv()
load_dotenv(".local.env", override=True)

OPENROUTER_MODEL = "google/gemini-flash-1.5"

SUMMARY_PROMPT = "Summarize the following article in 5 concise bullet points. Be direct, no preamble."


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in the environment.")
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
