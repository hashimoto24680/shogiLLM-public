# -*- coding: utf-8 -*-
"""
局面特徴抽出パッケージ

静的特徴・動的特徴の抽出機能を提供する。
"""

from src.features.extractor import FeatureExtractor
from src.features.dynamic import extract_dynamic_features
from src.features.models import (
    BasePiece,
    PieceInfo,
    SquareInfo,
    HandPieces,
    KingSafety,
    CastlePattern,
    StrategyPattern,
    StaticFeatures,
    DynamicFeatures,
)
from src.features.material import MaterialAdvantage, calculate_material

__all__ = [
    # 統合API
    "FeatureExtractor",
    "extract_dynamic_features",
    # モデル
    "BasePiece",
    "PieceInfo",
    "SquareInfo",
    "HandPieces",
    "KingSafety",
    "CastlePattern",
    "StrategyPattern",
    "StaticFeatures",
    "DynamicFeatures",
    "MaterialAdvantage",
    # 関数
    "calculate_material",
]
