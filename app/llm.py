"""OpenAI API呼び出しモジュール（Structured Outputs使用）"""

import os
from openai import OpenAI
from typing import Type, TypeVar
from pydantic import BaseModel
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# OpenAIクライアントの初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

T = TypeVar('T', bound=BaseModel)


def generate_structured_response(
    prompt: str,
    response_model: Type[T],
    model: str = "gpt-4o-2024-08-06",
    temperature: float = 0.7
) -> T:
    """
    OpenAI APIを使用して構造化された応答を生成
    
    Args:
        prompt: プロンプト文字列
        response_model: Pydanticモデル（レスポンスの型）
        model: 使用するOpenAIモデル
        temperature: 生成の温度パラメータ
    
    Returns:
        response_model型のインスタンス
    """
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀な営業支援AIアシスタントです。正確で実用的な情報を提供してください。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format=response_model,
            temperature=temperature
        )
        
        return completion.choices[0].message.parsed
    
    except Exception as e:
        raise Exception(f"OpenAI API呼び出しエラー: {str(e)}")


def generate_email(prompt: str, response_model: Type[T]) -> T:
    """営業メール生成"""
    return generate_structured_response(
        prompt=prompt,
        response_model=response_model,
        temperature=0.7
    )


def summarize_meeting(prompt: str, response_model: Type[T]) -> T:
    """商談議事録要約"""
    return generate_structured_response(
        prompt=prompt,
        response_model=response_model,
        temperature=0.5  # 要約は一貫性を重視
    )


def generate_proposal(prompt: str, response_model: Type[T]) -> T:
    """提案書アウトライン生成"""
    return generate_structured_response(
        prompt=prompt,
        response_model=response_model,
        temperature=0.6
    )
