# -*- coding: utf-8 -*-
"""
戦法パターン定義

shogi_castles_data.py と同様の形式で定義。
positions に複数マスを指定可能（OR条件）。
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class StrategyCondition:
    """
    戦法の条件。

    Attributes:
        piece_type: 駒の種類（玉、金、銀、桂、香、歩、角、飛）
        positions: 可能な位置のリスト（例: ["8八", "7九"]）。piece_on_file/piece_in_handの場合はNone。
        required: 必須かどうか（距離が離れすぎるとスコア0になる）
        weight: 重み（0.0～1.0）
        condition_type: 条件タイプ（デフォルト: "piece_on"）
            - "piece_on": 駒が特定のマスにいる（positions使用）
            - "piece_on_file": 駒が特定の筋にいる（files使用）
            - "piece_in_hand": 駒を持ち駒として持っている
        files: 筋のリスト（piece_on_file用）
        side: "sente" or "gote"（後手の駒を指定する場合）
        strict: Trueなら完全一致必須（指定位置にいないとスコア0）
    """
    piece_type: str
    positions: Optional[List[str]] = None
    required: bool = True
    weight: float = 0.0
    condition_type: str = "piece_on"
    files: Optional[List[int]] = None
    side: str = "sente"
    strict: bool = False  # 完全一致必須

    def __init__(self, piece_type: str, positions: Optional[List[str]] = None,
                 required: bool = True, weight: float = 0.0,
                 condition_type: str = "piece_on", files: Optional[List[int]] = None,
                 side: str = "sente", strict: bool = False):
        """StrategyCondition の初期化。"""
        self.piece_type = piece_type
        self.positions = positions
        self.required = required
        self.weight = weight
        self.condition_type = condition_type
        self.files = files
        self.side = side
        self.strict = strict


@dataclass
class StrategyDefinition:
    """
    戦法の定義。

    Attributes:
        name: 戦法の名前
        category: カテゴリ（居飛車/振り飛車/相掛かり/etc.）
        conditions: 条件リスト
        min_confidence: この値以上でマッチと判定
        description: 説明
    """
    name: str
    category: str
    conditions: List[StrategyCondition]
    min_confidence: float = 0.5
    description: str = ""

    def __init__(self, name: str, category: str, conditions: List[StrategyCondition],
                 min_confidence: float = 0.5, description: str = ""):
        """StrategyDefinition の初期化。"""
        self.name = name
        self.category = category
        self.conditions = conditions
        self.min_confidence = min_confidence
        self.description = description


# ========================================
# 戦法パターン定義（辞書形式）
# ========================================

STRATEGY_PATTERNS: Dict[str, StrategyDefinition] = {
    # ========================================
    # 矢倉系戦法
    # ========================================
    "3七銀戦法": StrategyDefinition(
        name="3七銀戦法",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["8八", "7九"], required=True, weight=0.20, strict=True),
            StrategyCondition("飛", ["2八"], required=True, weight=0.20, strict=True),
            StrategyCondition("金", ["7八"], required=True, weight=0.20, strict=True),
            StrategyCondition("銀", ["7七"], required=True, weight=0.20, strict=True),
            StrategyCondition("銀", ["3七"], required=True, weight=0.20, strict=True),
        ],
        min_confidence=0.7,
        description="矢倉戦における急戦策。銀を3七に配置。"
    ),
    "脇システム": StrategyDefinition(
        name="脇システム",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["8八", "7九"], required=True, weight=0.15, strict=True),
            StrategyCondition("角", ["4六"], required=True, weight=0.20, strict=True),
            StrategyCondition("金", ["7八"], required=True, weight=0.10, strict=True),
            StrategyCondition("金", ["6七"], required=True, weight=0.10, strict=True),
            StrategyCondition("銀", ["7七"], required=True, weight=0.10, strict=True),
            StrategyCondition("銀", ["3七"], required=True, weight=0.15),
            StrategyCondition("角", ["6四"], required=False, weight=0.20, side="gote"),
        ],
        min_confidence=0.7,
        description="脇謙二九段が考案した矢倉戦法。角を4六に配置。"
    ),
    "森下システム": StrategyDefinition(
        name="森下システム",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["8八", "7九"], required=True, weight=0.15, strict=True),
            StrategyCondition("角", ["6八"], required=True, weight=0.20, strict=True),
            StrategyCondition("金", ["7八"], required=True, weight=0.15, strict=True),
            StrategyCondition("金", ["6七"], required=True, weight=0.15, strict=True),
            StrategyCondition("銀", ["7七"], required=True, weight=0.15, strict=True),
        ],
        min_confidence=0.7,
        description="森下卓九段が考案した矢倉戦法。角を6八に引く。"
    ),
    "雀刺し": StrategyDefinition(
        name="雀刺し",
        category="居飛車",
        conditions=[
            StrategyCondition("飛", ["1八"], required=True, weight=0.30),
            StrategyCondition("金", ["7八"], required=True, weight=0.15),
            StrategyCondition("金", ["5八"], required=True, weight=0.15),
            StrategyCondition("香", ["1七"], required=True, weight=0.20, strict=True),
            StrategyCondition("歩", ["1六"], required=True, weight=0.20, strict=True),
        ],
        min_confidence=0.7,
        description="端攻めを狙う戦法。1筋に飛車と香を集中。"
    ),
    "米長流急戦矢倉": StrategyDefinition(
        name="米長流急戦矢倉",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["6九", "7八"], required=True, weight=0.15),
            StrategyCondition("角", ["8八"], required=True, weight=0.20, strict=True),
            StrategyCondition("金", ["7八"], required=True, weight=0.15),
            StrategyCondition("金", ["5八"], required=True, weight=0.15),
            StrategyCondition("銀", ["6六"], required=True, weight=0.20, strict=True),
            StrategyCondition("歩", ["5六"], required=True, weight=0.15, strict=True),
        ],
        min_confidence=0.7,
        description="米長邦雄永世棋聖が考案した急戦策。"
    ),
    "カニカニ銀": StrategyDefinition(
        name="カニカニ銀",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["5九"], required=True, weight=0.15),
            StrategyCondition("飛", ["5八"], required=True, weight=0.15, strict=True),
            StrategyCondition("金", ["6九"], required=True, weight=0.10),
            StrategyCondition("金", ["4九"], required=True, weight=0.10),
            StrategyCondition("銀", ["6六"], required=True, weight=0.20, strict=True),
            StrategyCondition("銀", ["4六"], required=True, weight=0.20, strict=True),
            StrategyCondition("歩", ["5六"], required=True, weight=0.10, strict=True),
        ],
        min_confidence=0.7,
        description="児玉孝一七段が考案。銀2枚をカニのハサミのように配置。"
    ),
    "中原流急戦矢倉": StrategyDefinition(
        name="中原流急戦矢倉",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["6九", "7八"], required=True, weight=0.20, strict=True),
            StrategyCondition("角", ["8八"], required=True, weight=0.20),
            StrategyCondition("金", ["7八"], required=True, weight=0.20),
            StrategyCondition("金", ["4七"], required=True, weight=0.25, strict=True),
            StrategyCondition("歩", ["6七"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="中原誠十六世名人が考案した急戦策。"
    ),
    "矢倉中飛車": StrategyDefinition(
        name="矢倉中飛車",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["6九"], required=True, weight=0.15, strict=True),
            StrategyCondition("飛", ["5八"], required=True, weight=0.30, strict=True),
            StrategyCondition("角", ["8八"], required=True, weight=0.15),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("銀", ["5七"], required=True, weight=0.15),
            StrategyCondition("歩", ["6七"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="矢倉模様から中飛車に振る戦法。"
    ),

    # ========================================
    # 居飛車急戦系
    # ========================================
    "右四間飛車": StrategyDefinition(
        name="右四間飛車",
        category="居飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.60, condition_type="piece_on_file", files=[4], strict=True),
            StrategyCondition("歩", ["4六"], required=True, weight=0.40, strict=True),
            StrategyCondition("銀", ["5六"], required=True, weight=0.40),
        ],
        min_confidence=0.7,
        description="飛車を4筋に振って攻める急戦策。"
    ),
    "原始棒銀": StrategyDefinition(
        name="原始棒銀",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["5九"], required=True, weight=0.15),
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[2]),
            StrategyCondition("銀", ["2六", "2七", "3五", "1五"], required=True, weight=0.45, strict=True),
            StrategyCondition("歩", ["2五"], required=True, weight=0.20),
        ],
        min_confidence=0.7,
        description="銀を2筋に棒のように進める単純明快な急戦策。"
    ),
    "右玉": StrategyDefinition(
        name="右玉",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["4八", "3八"], required=True, weight=0.40),
            StrategyCondition("飛", ["2九", "2八"], required=True, weight=0.20),
            StrategyCondition("銀", ["4七"], required=True, weight=0.20),
            StrategyCondition("桂", ["3七"], required=True, weight=0.20),
        ],
        min_confidence=0.7,
        description="玉を右側に配置する持久戦向きの戦法。"
    ),
    "かまいたち戦法": StrategyDefinition(
        name="かまいたち戦法",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["5九"], required=True, weight=0.10),
            StrategyCondition("金", ["6九"], required=True, weight=0.10),
            StrategyCondition("金", ["4九"], required=True, weight=0.10),
            StrategyCondition("銀", ["7九"], required=True, weight=0.15),
            StrategyCondition("銀", ["5七"], required=True, weight=0.30, strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.10),
            StrategyCondition("歩", ["5六"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="銀を7九に残す独特の戦法。"
    ),
    "パックマン戦法": StrategyDefinition(
        name="パックマン戦法",
        category="後手番限定",
        conditions=[
            StrategyCondition("歩", ["7六"], required=True, weight=0.30),
            StrategyCondition("歩", ["4四"], required=True, weight=0.30, side="gote", strict=True),
            StrategyCondition("歩", ["3三"], required=True, weight=0.40, side="gote", strict=True),
        ],
        min_confidence=0.7,
        description="3手目まで。後手番限定の奇襲戦法。"
    ),
    "新米長玉": StrategyDefinition(
        name="新米長玉",
        category="後手番限定",
        conditions=[
            StrategyCondition("玉", ["6二"], required=True, weight=1.0, side="gote", strict=True),
            StrategyCondition("飛", ["8二"], required=True, weight=1.0, side="gote", strict=True),
            StrategyCondition("銀", ["7一"], required=True, weight=1.0, side="gote", strict=True),
        ],
        min_confidence=0.7,
        description="後手番限定。玉を6二に配置。"
    ),

    # ========================================
    # 角換わり系
    # ========================================
    "角換わり": StrategyDefinition(
        name="角換わり",
        category="居飛車",
        conditions=[
            StrategyCondition("歩", ["7六"], required=True, weight=0.10),
            StrategyCondition("歩", ["6七"], required=True, weight=0.10),
            StrategyCondition("歩", ["2五"], required=True, weight=0.10),
            StrategyCondition("角", None, required=True, weight=0.40, condition_type="piece_in_hand"),
            StrategyCondition("銀", ["3三"], required=True, weight=0.10, side="gote"),
            StrategyCondition("歩", ["3四"], required=True, weight=0.10, side="gote"),
            StrategyCondition("歩", ["4三"], required=True, weight=0.10, side="gote"),
        ],
        min_confidence=0.7,
        description="角を交換して持ち合う相居飛車の戦型。"
    ),
    "腰掛け銀": StrategyDefinition(
        name="腰掛け銀",
        category="居飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.15, condition_type="piece_on_file", files=[2]),
            StrategyCondition("金", ["5八"], required=True, weight=0.10),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("銀", ["7七"], required=True, weight=0.10),
            StrategyCondition("銀", ["5六"], required=True, weight=0.40),
            StrategyCondition("歩", ["7六"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="銀を5六に「腰掛ける」ように配置する戦法。"
    ),
    "早繰り銀": StrategyDefinition(
        name="早繰り銀",
        category="居飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.15, condition_type="piece_on_file", files=[2]),
            StrategyCondition("銀", ["4六"], required=True, weight=0.40),
            StrategyCondition("歩", ["7六"], required=True, weight=0.05),
            StrategyCondition("歩", ["6七"], required=True, weight=0.05),
            StrategyCondition("歩", ["5七"], required=True, weight=0.05),
            StrategyCondition("歩", ["4七"], required=True, weight=0.05),
            StrategyCondition("歩", ["3六"], required=True, weight=0.05),
            StrategyCondition("歩", ["2五"], required=True, weight=0.10),
        ],
        min_confidence=0.7,
        description="銀を早く繰り出して攻める急戦策。"
    ),
    "筋違い角": StrategyDefinition(
        name="筋違い角",
        category="居飛車",
        conditions=[
            StrategyCondition("角", ["4五"], required=True, weight=0.50),
            StrategyCondition("歩", ["7六"], required=True, weight=0.15),
            StrategyCondition("銀", ["2二"], required=False, weight=0.20, side="gote"),
            StrategyCondition("歩", ["3四"], required=False, weight=0.15, side="gote"),
        ],
        min_confidence=0.7,
        description="角を4五に打ち込む奇襲戦法。"
    ),

    # ========================================
    # 相掛かり系
    # ========================================
    "相掛かり": StrategyDefinition(
        name="相掛かり",
        category="相掛かり",
        conditions=[
            StrategyCondition("金", ["7八"], required=True, weight=0.15),
            StrategyCondition("歩", ["2五"], required=True, weight=0.25),
            StrategyCondition("歩", ["7七"], required=True, weight=0.10),
            StrategyCondition("金", ["3二"], required=True, weight=0.15, side="gote"),
            StrategyCondition("歩", ["8五"], required=True, weight=0.25, side="gote"),
            StrategyCondition("歩", ["3三"], required=True, weight=0.10, side="gote"),
        ],
        min_confidence=0.7,
        description="お互いに飛車先の歩を交換する戦型。"
    ),
    "横歩取り": StrategyDefinition(
        name="横歩取り",
        category="相掛かり",
        conditions=[
            StrategyCondition("飛", ["3四"], required=True, weight=0.25),
            StrategyCondition("角", ["8八"], required=True, weight=0.10),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("銀", ["7九"], required=True, weight=0.05),
            StrategyCondition("歩", ["7六"], required=True, weight=0.05),
            StrategyCondition("飛", ["8六"], required=True, weight=0.25, side="gote"),
            StrategyCondition("角", ["2二"], required=True, weight=0.05, side="gote"),
            StrategyCondition("金", ["3二"], required=True, weight=0.05, side="gote"),
            StrategyCondition("銀", ["3一"], required=True, weight=0.10, side="gote"),
        ],
        min_confidence=0.7,
        description="相掛かりから横歩を取る激しい戦型。"
    ),
    "3三角型空中戦法": StrategyDefinition(
        name="3三角型空中戦法",
        category="後手番限定",
        conditions=[
            StrategyCondition("飛", ["3四"], required=True, weight=0.15),
            StrategyCondition("角", ["8八"], required=True, weight=0.10),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("銀", ["7九"], required=True, weight=0.05),
            StrategyCondition("歩", ["7六"], required=True, weight=0.05),
            StrategyCondition("飛", ["8六"], required=True, weight=0.15, side="gote"),
            StrategyCondition("角", ["3三"], required=True, weight=0.25, side="gote", strict=True),
            StrategyCondition("金", ["3二"], required=True, weight=0.05, side="gote"),
            StrategyCondition("銀", ["3一"], required=True, weight=0.10, side="gote"),
        ],
        min_confidence=0.7,
        description="後手番限定。角を3三に上がる横歩取りの一型。"
    ),
    "嬉野流": StrategyDefinition(
        name="嬉野流",
        category="居飛車",
        conditions=[
            StrategyCondition("角", ["7九"], required=True, weight=0.25, strict=True),
            StrategyCondition("銀", ["6八"], required=True, weight=0.25),
            StrategyCondition("歩", ["7七"], required=True, weight=0.30, strict=True),
            StrategyCondition("歩", ["5六"], required=True, weight=0.20),
        ],
        min_confidence=0.7,
        description="嬉野宏明氏が考案した力戦型戦法。"
    ),

    # ========================================
    # 振り飛車系
    # ========================================
    "ゴキゲン中飛車": StrategyDefinition(
        name="ゴキゲン中飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.40, condition_type="piece_on_file", files=[5], strict=True),
            StrategyCondition("角", ["8八"], required=True, weight=0.15),
            StrategyCondition("歩", ["7六"], required=True, weight=0.15),
            StrategyCondition("歩", ["6七"], required=True, weight=0.15),
            StrategyCondition("歩", ["5六"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="近藤正和六段が考案した中飛車戦法。"
    ),
    "ツノ銀中飛車": StrategyDefinition(
        name="ツノ銀中飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[5], strict=True),
            StrategyCondition("角", ["7七"], required=True, weight=0.20),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("銀", ["6七"], required=True, weight=0.20),
            StrategyCondition("銀", ["4七"], required=True, weight=0.20),
            StrategyCondition("歩", ["5六"], required=True, weight=0.10),
        ],
        min_confidence=0.7,
        description="角をツノのように7七に配置する中飛車。"
    ),
    "四間飛車": StrategyDefinition(
        name="四間飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.50, condition_type="piece_on_file", files=[6], strict=True),
            StrategyCondition("歩", ["6六"], required=True, weight=0.25),
            StrategyCondition("歩", ["7六"], required=True, weight=0.25),
        ],
        min_confidence=0.7,
        description="飛車を6筋（四間）に振る代表的な振り飛車戦法。"
    ),
    "藤井システム": StrategyDefinition(
        name="藤井システム",
        category="振り飛車",
        conditions=[
            StrategyCondition("玉", ["5九"], required=True, weight=0.10, strict=True),
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[6], strict=True),
            StrategyCondition("金", ["5八"], required=True, weight=0.10),
            StrategyCondition("金", ["4九"], required=True, weight=0.10),
            StrategyCondition("銀", ["3八"], required=True, weight=0.15),
            StrategyCondition("歩", ["6六"], required=True, weight=0.10),
            StrategyCondition("歩", ["4六"], required=True, weight=0.25),
        ],
        min_confidence=0.7,
        description="藤井猛九段が考案した四間飛車の一型。居飛車穴熊対策。"
    ),
    "立石流": StrategyDefinition(
        name="立石流",
        category="振り飛車",
        conditions=[
            StrategyCondition("玉", ["2八"], required=True, weight=0.15),
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[6]),
            StrategyCondition("角", ["8八"], required=True, weight=0.15),
            StrategyCondition("金", ["7八"], required=True, weight=0.10),
            StrategyCondition("歩", ["7五"], required=True, weight=0.20),
            StrategyCondition("歩", ["6五"], required=True, weight=0.20),
        ],
        min_confidence=0.7,
        description="立石勝巳八段が考案した四間飛車の一型。浮き飛車にする。"
    ),
    "レグスペ": StrategyDefinition(
        name="レグスペ",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[6], strict=True),
            StrategyCondition("銀", ["7七"], required=True, weight=0.40, strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.20),
            StrategyCondition("歩", ["6七"], required=True, weight=0.20),
        ],
        min_confidence=0.7,
        description="四間飛車で早めに銀を7七に上げる戦法。"
    ),
    "三間飛車": StrategyDefinition(
        name="三間飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.60, condition_type="piece_on_file", files=[7], strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.40),
        ],
        min_confidence=0.7,
        description="飛車を7筋（三間）に振る振り飛車戦法。石田流への発展が可能。"
    ),
    "石田流": StrategyDefinition(
        name="石田流",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", ["7六"], required=True, weight=0.25),
            StrategyCondition("角", ["9七"], required=True, weight=0.15),
            StrategyCondition("銀", ["6七"], required=True, weight=0.15),
            StrategyCondition("桂", ["7七"], required=True, weight=0.15),
            StrategyCondition("歩", ["7五"], required=True, weight=0.15, strict=True),
            StrategyCondition("歩", ["6六"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="飛車を7六に浮かせる三間飛車の発展形。"
    ),
    "早石田": StrategyDefinition(
        name="早石田",
        category="振り飛車",
        conditions=[
            StrategyCondition("歩", ["7五"], required=True, weight=1.0),
            StrategyCondition("飛", ["7八", "7六"], required=True, weight=0.25),

        ],
        min_confidence=0.7,
        description="4手目までに飛車を7五に浮かせる急戦策。"
    ),
    "鬼殺し": StrategyDefinition(
        name="鬼殺し",
        category="奇襲",
        conditions=[
            StrategyCondition("桂", ["7七"], required=True, weight=0.50, strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.25, strict=True),
            StrategyCondition("歩", ["3四"], required=True, weight=0.25, side="gote"),
        ],
        min_confidence=0.7,
        description="桂馬を7七に跳ねる序盤の奇襲戦法。"
    ),

    # ========================================
    # 向かい飛車系
    # ========================================
    "ダイレクト向かい飛車": StrategyDefinition(
        name="ダイレクト向かい飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.35, condition_type="piece_on_file", files=[8], strict=True),
            StrategyCondition("角", None, required=True, weight=0.25, condition_type="piece_in_hand"),
            StrategyCondition("銀", ["7七"], required=True, weight=0.20, strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.10, strict=True),
            StrategyCondition("飛", ["8二"], required=False, weight=0.10, side="gote"),
        ],
        min_confidence=0.7,
        description="角交換後に8筋に飛車を振る戦法。"
    ),
    "阪田流向飛車": StrategyDefinition(
        name="阪田流向飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.25, condition_type="piece_on_file", files=[8]),
            StrategyCondition("角", None, required=True, weight=0.25, condition_type="piece_in_hand"),
            StrategyCondition("金", ["7七"], required=True, weight=0.25, strict=True),
            StrategyCondition("歩", ["7六"], required=True, weight=0.10),
            StrategyCondition("歩", ["8五"], required=True, weight=0.15, side="gote"),
        ],
        min_confidence=0.7,
        description="阪田三吉が考案した向かい飛車。金を7七に上げる。"
    ),
    "向飛車": StrategyDefinition(
        name="向飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.30, condition_type="piece_on_file", files=[8], strict=True),
            StrategyCondition("角", ["7七"], required=True, weight=0.20),
            StrategyCondition("銀", ["6七"], required=True, weight=0.15),
            StrategyCondition("歩", ["8七"], required=True, weight=0.10),
            StrategyCondition("歩", ["7六"], required=True, weight=0.10),
            StrategyCondition("歩", ["6六"], required=True, weight=0.15),
        ],
        min_confidence=0.7,
        description="飛車を8筋（向かい側）に振る戦法。"
    ),

    # ========================================
    # 対振り飛車急戦系
    # ========================================
    "4五歩早仕掛け": StrategyDefinition(
        name="4五歩早仕掛け",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["7八"], required=True, weight=0.10),
            StrategyCondition("飛", None, required=True, weight=0.15, condition_type="piece_on_file", files=[2]),
            StrategyCondition("角", ["8八"], required=True, weight=0.10),
            StrategyCondition("銀", ["4八"], required=True, weight=0.15),
            StrategyCondition("桂", ["3七"], required=True, weight=0.15),
            StrategyCondition("歩", ["4五"], required=True, weight=0.35),
        ],
        min_confidence=0.7,
        description="対振り飛車の急戦策。4筋の歩を突いて仕掛ける。"
    ),
    "超速": StrategyDefinition(
        name="超速",
        category="居飛車",
        conditions=[
            StrategyCondition("玉", ["6八"], required=True, weight=0.05),
            StrategyCondition("飛", None, required=True, weight=0.15, condition_type="piece_on_file", files=[2]),
            StrategyCondition("角", ["8八"], required=True, weight=0.05),
            StrategyCondition("金", ["6九"], required=True, weight=0.05),
            StrategyCondition("金", ["4九"], required=True, weight=0.05),
            StrategyCondition("銀", ["7九"], required=True, weight=0.05),
            StrategyCondition("歩", ["7六"], required=True, weight=0.05),
            StrategyCondition("歩", ["5六"], required=True, weight=0.05),
            StrategyCondition("歩", ["3六"], required=True, weight=0.10),
            StrategyCondition("歩", ["2五"], required=True, weight=0.10),
            StrategyCondition("玉", ["7二"], required=True, weight=0.05, side="gote"),
            StrategyCondition("飛", None, required=True, weight=0.20, condition_type="piece_on_file", files=[5], side="gote"),
            StrategyCondition("角", ["3三"], required=False, weight=0.05, side="gote"),
            StrategyCondition("歩", ["3四"], required=False, weight=0.05, side="gote"),
        ],
        min_confidence=0.7,
        description="対ゴキゲン中飛車の急戦策。銀を早く繰り出す。"
    ),

    # ========================================
    # 基本戦型（汎用）
    # ========================================
    "居飛車": StrategyDefinition(
        name="居飛車",
        category="居飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.60, condition_type="piece_on_file", files=[2]),
            StrategyCondition("玉", None, required=False, weight=0.40, condition_type="piece_on_file", files=[6, 7, 8, 9]),
        ],
        min_confidence=0.5,
        description="飛車を動かさない基本戦型。"
    ),
    "中飛車": StrategyDefinition(
        name="中飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition("飛", None, required=True, weight=0.50, condition_type="piece_on_file", files=[5]),
            StrategyCondition("玉", None, required=False, weight=0.30, condition_type="piece_on_file", files=[1, 2, 3, 4]),
            StrategyCondition("歩", ["5六"], required=False, weight=0.20),
        ],
        min_confidence=0.5,
        description="飛車を5筋に振る戦法。"
    ),
}


# ========================================
# 全ての戦法をリストにまとめる
# ========================================

ALL_STRATEGIES = list(STRATEGY_PATTERNS.values())


# ========================================
# ユーティリティ関数
# ========================================

def get_strategy_by_name(name: str) -> StrategyDefinition:
    """
    名前で戦法を検索する。

    Args:
        name: 戦法の名前

    Returns:
        StrategyDefinition: 見つかった戦法、見つからない場合はNone
    """
    return STRATEGY_PATTERNS.get(name)


def get_strategies_by_category(category: str) -> list[StrategyDefinition]:
    """
    カテゴリで戦法を検索する。

    Args:
        category: カテゴリ（"居飛車", "振り飛車", etc.）

    Returns:
        list[StrategyDefinition]: 該当する戦法のリスト
    """
    return [s for s in ALL_STRATEGIES if category in s.category]


def print_all_strategies():
    """全ての戦法を表示する。"""
    print(f"登録されている戦法の総数: {len(ALL_STRATEGIES)}\n")

    categories = ["居飛車", "振り飛車", "相掛かり", "奇襲", "後手番限定"]
    for cat in categories:
        strategies = get_strategies_by_category(cat)
        if strategies:
            print("=" * 60)
            print(f"{cat}系の戦法")
            print("=" * 60)
            for s in strategies:
                print(f"\n【{s.name}】")
                print(f"  説明: {s.description}")
                print(f"  最小信頼度: {s.min_confidence}")
                print(f"  条件数: {len(s.conditions)}")


if __name__ == "__main__":
    print_all_strategies()
