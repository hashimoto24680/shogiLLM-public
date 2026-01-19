# -*- coding: utf-8 -*-
"""
教師データ生成パッケージ

LLM学習用の教師データを生成するためのスクリプト群を提供する。

モジュール:
    - generate_training_data: 局面特徴＋コメントから教師データ生成
    - generate_commentary_openai: OpenAI APIで解説文を生成
    - convert_kif_to_json: KIF形式からJSON形式への変換
    - cleanse_kif_commentary: KIFコメントのクレンジング
"""
