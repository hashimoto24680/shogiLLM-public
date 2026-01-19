# -*- coding: utf-8 -*-
from __future__ import annotations


def get_openai_client():
    """openai>=1.x を想定。"""
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise ImportError(
            "openai パッケージが見つかりません。requirementsのopenaiを .venv にインストールしてください。"
        ) from e

    return OpenAI()
