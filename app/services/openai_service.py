# app/services/openai_service.py
import os
from typing import Type, TypeVar
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()  # ← これがないと .env を読まない

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

T = TypeVar("T", bound=BaseModel)


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)

def call_llm(system_prompt: str, user_prompt: str) -> str:
    client = _get_client()
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.output_text

def parse_llm(schema: Type[T], system_prompt: str, user_prompt: str) -> T:
    client = _get_client()
    resp = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=schema,
    )
    return resp.output_parsed
