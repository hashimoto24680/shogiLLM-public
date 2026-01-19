# -*- coding: utf-8 -*-
"""
囲い・戦法パターン定義パッケージ

このパッケージは2種類のデータ構造を提供します：
1. 辞書形式（CASTLE_PATTERNS, STRATEGY_PATTERNS）- 名前→定義のマップ
2. リスト形式（ALL_CASTLES, ALL_STRATEGIES）- 定義のリスト
"""

# 囲いデータをインポート
from .castles import (
    ALL_CASTLES,
    CastleCondition,
    CastleDefinition,
    get_castle_by_name,
    get_castles_by_category,
)

# 互換性のため、辞書形式のエイリアスを作成（名前→定義のマップ）
CASTLE_PATTERNS = {castle.name: castle for castle in ALL_CASTLES}

# 戦法データ
from .strategies import (
    ALL_STRATEGIES,
    StrategyCondition,
    StrategyDefinition,
    get_strategy_by_name,
    get_strategies_by_category,
)

# 互換性のため、辞書形式のエイリアスを作成
STRATEGY_PATTERNS = {strategy.name: strategy for strategy in ALL_STRATEGIES}

__all__ = [
    # 囲い
    "CASTLE_PATTERNS",
    "ALL_CASTLES",
    "CastleCondition",
    "CastleDefinition",
    # 戦法
    "STRATEGY_PATTERNS",
    "ALL_STRATEGIES",
    "StrategyCondition",
    "StrategyDefinition",
    # ユーティリティ関数
    "get_castle_by_name",
    "get_castles_by_category",
    "get_strategy_by_name",
    "get_strategies_by_category",
]
