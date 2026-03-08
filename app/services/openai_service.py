# app/services/openai_service.py
import os
from typing import Type, TypeVar
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()  # ← これがないと .env を読まない

client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

T = TypeVar("T", bound=BaseModel)

def call_llm(system_prompt: str, user_prompt: str) -> str:
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.output_text

def parse_llm(schema: Type[T], system_prompt: str, user_prompt: str) -> T:
    resp = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=schema,
    )
    return resp.output_parsed
