"""
将棋の囲いデータ定義

castle_definitions_template.md に基づいて作成。
座標はテンプレートの英字表記から日本語座標に変換済み。
変換ルール: a→一, b→二, c→三, d→四, e→五, f→六, g→七, h→八, i→九
"""

from dataclasses import dataclass
from typing import List


@dataclass
class CastleCondition:
    """
    囲いの構成条件。

    Attributes:
        piece_type: 駒の種類（玉、金、銀、桂、香、歩、角、飛）
        positions: 可能な位置のリスト（例: ["8八", "7九"]）
        required: 必須かどうか（距離が離れすぎるとスコア0になる）
        weight: 重み（0.0～1.0）
        negated: Trueなら「その駒がそのマスにない」条件
        strict: Trueなら完全一致必須（指定位置にいないとスコア0）
    """
    piece_type: str
    positions: List[str]
    required: bool
    weight: float
    negated: bool = False
    strict: bool = False  # 完全一致必須

    def __init__(self, piece_type: str, positions: List[str], required: bool = True, 
                 weight: float = 0.0, negated: bool = False, strict: bool = False):
        """CastleCondition の初期化。"""
        self.piece_type = piece_type
        self.positions = positions
        self.required = required
        self.weight = weight
        self.negated = negated
        self.strict = strict


@dataclass
class CastleDefinition:
    """
    囲いの定義。

    Attributes:
        name: 囲いの名前
        conditions: 構成条件のリスト
        min_confidence: 最小信頼度（0.0～1.0）
        category: カテゴリ（居飛車/振り飛車）
        description: 説明
    """
    name: str
    conditions: List[CastleCondition]
    min_confidence: float
    category: str = ""
    description: str = ""

    def __init__(self, name: str, conditions: List[CastleCondition], min_confidence: float,
                 category: str = "", description: str = ""):
        """CastleDefinition の初期化。"""
        self.name = name
        self.conditions = conditions
        self.min_confidence = min_confidence
        self.category = category
        self.description = description


# ========================================
# 矢倉系（居飛車）
# ========================================

カニ囲い = CastleDefinition(
    name="カニ囲い",
    conditions=[
        CastleCondition("玉", ["6九"], required=True, weight=0.30),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["5八"], required=True, weight=0.25),
        CastleCondition("銀", ["6八"], required=True, weight=0.20),
    ],
    min_confidence=0.9,
    category="居飛車",
    description="居飛車の基本的な囲い。矢倉への発展途上の形。"
)

矢倉 = CastleDefinition(
    name="矢倉",
    conditions=[
        CastleCondition("金", ["7八"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["7七"], required=True, weight=0.25),
        CastleCondition("歩", ["6七"], required=True, weight=0.5),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="相居飛車の代表的な囲い。金銀3枚で玉を守る。"
)

金矢倉 = CastleDefinition(
    name="金矢倉",
    conditions=[
        CastleCondition("玉", ["8八", "7九"], required=True, weight=0.30),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["7七"], required=True, weight=0.20),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="相居飛車の代表的な囲い。金銀3枚で玉を守る。"
)

銀矢倉 = CastleDefinition(
    name="銀矢倉",
    conditions=[
        CastleCondition("玉", ["8八", "7九"], required=True, weight=0.30),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("銀", ["6七"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["7七"], required=True, weight=0.20),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="金矢倉の6七金を銀に換えた形。銀2枚で構成。"
)

片矢倉 = CastleDefinition(
    name="片矢倉",
    conditions=[
        CastleCondition("玉", ["7八"], required=True, weight=0.35, strict=True),
        CastleCondition("金", ["6八"], required=True, weight=0.30),
        CastleCondition("金", ["6七"], required=True, weight=0.20),
        CastleCondition("銀", ["7七"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="角換わりでよく用いられる囲い。玉が7八に位置する。"
)

総矢倉 = CastleDefinition(
    name="総矢倉",
    conditions=[
        CastleCondition("玉", ["8八", "7九"], required=True, weight=0.25),
        CastleCondition("金", ["7八"], required=True, weight=0.20),
        CastleCondition("金", ["6七"], required=True, weight=0.20),
        CastleCondition("銀", ["7七"], required=True, weight=0.20),
        CastleCondition("銀", ["5七"], required=True, weight=0.15, strict=True),
    ],
    min_confidence=0.75,
    category="居飛車",
    description="矢倉の完成形。銀2枚を使った堅固な囲い。"
)

矢倉穴熊 = CastleDefinition(
    name="矢倉穴熊",
    conditions=[
        CastleCondition("玉", ["9九"], required=True, weight=0.30, ),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.20),
        CastleCondition("銀", ["7七"], required=True, weight=0.15, strict=True),
        CastleCondition("香", ["9八"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="矢倉から穴熊に発展させた形。"
)

菊水矢倉 = CastleDefinition(
    name="菊水矢倉",
    conditions=[
        CastleCondition("玉", ["8九"], required=True, weight=0.30),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.20),
        CastleCondition("銀", ["8八"], required=True, weight=0.15, strict=True),
        CastleCondition("桂", ["7七"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="矢倉の変化形。玉が8九、銀が8八、桂が7七の形。"
)

銀立ち矢倉 = CastleDefinition(
    name="銀立ち矢倉",
    conditions=[
        CastleCondition("玉", ["8八", "7九"], required=True, weight=0.35),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.25),
        CastleCondition("銀", ["7六"], required=True, weight=0.15, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="銀を7六に立てた矢倉。攻撃的な形。"
)

菱矢倉 = CastleDefinition(
    name="菱矢倉",
    conditions=[
        CastleCondition("玉", ["8八", "7九"], required=True, weight=0.30),
        CastleCondition("金", ["7八"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.20),
        CastleCondition("銀", ["7七"], required=True, weight=0.15, strict=True),
        CastleCondition("銀", ["6六"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="銀2枚を使った矢倉の発展形。菱形に配置。"
)

# ========================================
# 雁木・ボナンザ系（居飛車）
# ========================================

雁木囲い = CastleDefinition(
    name="雁木囲い",
    conditions=[
        CastleCondition("玉", ["6九"], required=True, weight=0.25),
        CastleCondition("金", ["7八"], required=True, weight=0.20),
        CastleCondition("金", ["5八"], required=True, weight=0.20),
        CastleCondition("銀", ["6七"], required=True, weight=0.20, strict=True),
        CastleCondition("銀", ["5七"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="階段状の駒配置が特徴。相居飛車で用いられる。"
)

ボナンザ囲い = CastleDefinition(
    name="ボナンザ囲い",
    conditions=[
        CastleCondition("玉", ["7八"], required=True, weight=0.35),
        CastleCondition("金", ["6八"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["5八"], required=True, weight=0.25),
        CastleCondition("銀", ["7七"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="コンピュータ将棋ソフトBonanzaが好んだ囲い。"
)

# ========================================
# 美濃系（振り飛車）
# ========================================

美濃囲い = CastleDefinition(
    name="美濃囲い",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.35),
        CastleCondition("金", ["5八"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["4九"], required=True, weight=0.25),
        CastleCondition("銀", ["3八"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="振り飛車の代表的な囲い。横からの攻めに強い。"
)

高美濃囲い = CastleDefinition(
    name="高美濃囲い",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.35),
        CastleCondition("金", ["4七"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["4九"], required=True, weight=0.25),
        CastleCondition("銀", ["3八"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="美濃囲いの金を4七に上げた形。上部が厚い。"
)

振り飛車銀冠 = CastleDefinition(
    name="振り飛車銀冠",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.40),
        CastleCondition("金", ["3八"], required=True, weight=0.35),
        CastleCondition("銀", ["2七"], required=True, weight=0.25, strict=True),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="美濃囲いから発展。銀が玉の冠のように2七に配置。"
)

居飛車銀冠 = CastleDefinition(
    name="居飛車銀冠",
    conditions=[
        CastleCondition("玉", ["8八"], required=True, weight=0.40),
        CastleCondition("金", ["7八"], required=True, weight=0.35),
        CastleCondition("銀", ["8七"], required=True, weight=0.25, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="居飛車の銀冠。銀が8七に配置。"
)

銀美濃 = CastleDefinition(
    name="銀美濃",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.30),
        CastleCondition("金", ["4九"], required=True, weight=0.25),
        CastleCondition("銀", ["4七", "5八"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["3八"], required=True, weight=0.20),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="美濃囲いに銀を追加した堅固な形。"
)

ダイヤモンド美濃 = CastleDefinition(
    name="ダイヤモンド美濃",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.25),
        CastleCondition("金", ["5八"], required=True, weight=0.20),
        CastleCondition("金", ["4九"], required=True, weight=0.20),
        CastleCondition("銀", ["3八"], required=True, weight=0.20),
        CastleCondition("銀", ["4七"], required=True, weight=0.15, strict=True),
    ],
    min_confidence=0.75,
    category="振り飛車",
    description="金銀4枚を使ったダイヤモンド型の堅固な囲い。"
)

木村美濃 = CastleDefinition(
    name="木村美濃",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.40),
        CastleCondition("金", ["3八"], required=True, weight=0.35, strict=True),
        CastleCondition("銀", ["4七"], required=True, weight=0.25),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="木村義雄十四世名人が使った形。"
)

片美濃囲い = CastleDefinition(
    name="片美濃囲い",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.40),
        CastleCondition("金", ["4九"], required=True, weight=0.35),
        CastleCondition("銀", ["3八"], required=True, weight=0.25),
        CastleCondition("金", ["5八"], required=True, weight=0.20, negated=True),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="美濃囲いの簡易形。手数が少ない。"
)

ちょんまげ美濃 = CastleDefinition(
    name="ちょんまげ美濃",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.30),
        CastleCondition("金", ["4九"], required=True, weight=0.25),
        CastleCondition("銀", ["3八"], required=True, weight=0.20),
        CastleCondition("歩", ["3七"], required=True, weight=0.15),
        CastleCondition("歩", ["2六"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="玉頭の歩を突いた美濃囲い。見た目がちょんまげに似る。"
)

坊主美濃 = CastleDefinition(
    name="坊主美濃",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.30),
        CastleCondition("金", ["4九"], required=True, weight=0.25),
        CastleCondition("銀", ["3八"], required=True, weight=0.20),
        # 玉頭の歩がないことが特徴（2七～2四に歩がない）
        CastleCondition("歩", ["2七"], required=True, weight=0.0625, negated=True),
        CastleCondition("歩", ["2六"], required=True, weight=0.0625, negated=True),
        CastleCondition("歩", ["2五"], required=True, weight=0.0625, negated=True),
        CastleCondition("歩", ["2四"], required=True, weight=0.0625, negated=True),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="玉頭の歩が消失した美濃囲い。玉頭が弱い。"
)

# ========================================
# 左美濃系（居飛車）
# ========================================

左美濃 = CastleDefinition(
    name="左美濃",
    conditions=[
        CastleCondition("玉", ["8八"], required=True, weight=0.30),
        CastleCondition("金", ["5八"], required=True, weight=0.25),
        CastleCondition("金", ["6九"], required=True, weight=0.25),
        CastleCondition("銀", ["7八"], required=True, weight=0.20, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="対振り飛車の囲い。美濃囲いを左右反転させた形。"
)

天守閣美濃 = CastleDefinition(
    name="天守閣美濃",
    conditions=[
        CastleCondition("玉", ["8七"], required=True, weight=0.40, strict=True),
        CastleCondition("金", ["6九"], required=True, weight=0.30),
        CastleCondition("銀", ["7八"], required=True, weight=0.30),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="玉が8七に上がった左美濃の発展形。"
)

四枚美濃 = CastleDefinition(
    name="四枚美濃",
    conditions=[
        CastleCondition("玉", ["8七"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["6九"], required=True, weight=0.25),
        CastleCondition("銀", ["7八"], required=True, weight=0.25),
        CastleCondition("銀", ["7七"], required=True, weight=0.20, strict=True),
    ],
    min_confidence=0.75,
    category="居飛車",
    description="金銀4枚を使った左美濃の発展形。"
)

# ========================================
# 舟囲い系（居飛車）
# ========================================

舟囲い = CastleDefinition(
    name="舟囲い",
    conditions=[
        CastleCondition("玉", ["7八"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["6九"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["5八"], required=True, weight=0.25),
        CastleCondition("銀", ["7九"], required=True, weight=0.20),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="対振り飛車の基本的な囲い。手数が少なく急戦向き。"
)

エルモ囲い = CastleDefinition(
    name="エルモ囲い",
    conditions=[
        CastleCondition("玉", ["7八"], required=True, weight=0.25),
        CastleCondition("銀", ["6八"], required=True, weight=0.20),
        CastleCondition("金", ["7九"], required=True, weight=0.20, strict=True),
        CastleCondition("角", ["8八"], required=True, weight=0.15),
        CastleCondition("銀", ["5七"], required=False, weight=0.10),
        CastleCondition("金", ["5九"], required=False, weight=0.10),
    ],
    min_confidence=0.6,
    category="居飛車",
    description="elmo（将棋AI）が好んで使った対振り飛車の囲い。角が8八に残る形。"
)


# ========================================
# 穴熊系
# ========================================

居飛車穴熊 = CastleDefinition(
    name="居飛車穴熊",
    conditions=[
        CastleCondition("玉", ["9九"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["7九"], required=True, weight=0.25),
        CastleCondition("銀", ["8八"], required=True, weight=0.20),
        CastleCondition("桂", ["8九"], required=True, weight=0.15),
        CastleCondition("香", ["9八"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.75,
    category="居飛車",
    description="対振り飛車の代表的な囲い。非常に堅固。"
)

松尾流穴熊 = CastleDefinition(
    name="松尾流穴熊",
    conditions=[
        CastleCondition("玉", ["9九"], required=True, weight=0.25),
        CastleCondition("金", ["6七"], required=True, weight=0.15),
        CastleCondition("金", ["7八"], required=True, weight=0.15),
        CastleCondition("金", ["7九"], required=True, weight=0.15, negated=True),
        CastleCondition("銀", ["7九"], required=True, weight=0.15),
        CastleCondition("銀", ["8八"], required=True, weight=0.15),
        CastleCondition("桂", ["8九"], required=True, weight=0.10),
        CastleCondition("香", ["9八"], required=True, weight=0.05),
    ],
    min_confidence=0.75,
    category="居飛車",
    description="松尾歩八段が開発した穴熊の変化形。"
)

銀冠穴熊 = CastleDefinition(
    name="銀冠穴熊",
    conditions=[
        CastleCondition("玉", ["9九"], required=True, weight=0.30),
        CastleCondition("金", ["8八"], required=True, weight=0.20),
        CastleCondition("金", ["7八"], required=True, weight=0.20),
        CastleCondition("銀", ["8七"], required=True, weight=0.20, strict=True),
        CastleCondition("桂", ["8九"], required=True, weight=0.15),
        CastleCondition("香", ["9八"], required=True, weight=0.15, strict=True),
    ],
    min_confidence=0.75,
    category="居飛車",
    description="穴熊から銀冠に発展させた形。"
)

ビッグ4 = CastleDefinition(
    name="ビッグ4",
    conditions=[
        CastleCondition("玉", ["9九"], required=True, weight=0.25),
        CastleCondition("金", ["7八"], required=True, weight=0.15),
        CastleCondition("金", ["8八"], required=True, weight=0.15),
        CastleCondition("銀", ["7七"], required=True, weight=0.15),
        CastleCondition("銀", ["8七"], required=True, weight=0.15),
        CastleCondition("桂", ["8九"], required=True, weight=0.10),
        CastleCondition("香", ["9八"], required=True, weight=0.05),
    ],
    min_confidence=0.75,
    category="居飛車・振り飛車",
    description="穴熊の究極進化形。金銀4枚で守る。"
)

箱入り娘 = CastleDefinition(
    name="箱入り娘",
    conditions=[
        CastleCondition("玉", ["7八"], required=True, weight=0.35),
        CastleCondition("金", ["6九"], required=True, weight=0.25),
        CastleCondition("金", ["6八"], required=True, weight=0.25),
        CastleCondition("銀", ["7九"], required=True, weight=0.15, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="舟囲いの発展形。玉を金銀で囲む。"
)

ミレニアム囲い = CastleDefinition(
    name="ミレニアム囲い",
    conditions=[
        CastleCondition("玉", ["8九"], required=True, weight=0.40, strict=True),
        CastleCondition("金", ["7九"], required=True, weight=0.35, strict=True),
        CastleCondition("銀", ["8八"], required=True, weight=0.25, strict=True),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="対振り飛車で用いられる独特の囲い。"
)

振り飛車穴熊 = CastleDefinition(
    name="振り飛車穴熊",
    conditions=[
        CastleCondition("玉", ["1九"], required=True, weight=0.30),
        CastleCondition("金", ["3九"], required=True, weight=0.25),
        CastleCondition("銀", ["2八"], required=True, weight=0.20),
        CastleCondition("桂", ["2九"], required=True, weight=0.15),
        CastleCondition("香", ["1八"], required=True, weight=0.10, strict=True),
    ],
    min_confidence=0.75,
    category="振り飛車",
    description="振り飛車の穴熊。非常に堅固。"
)

# ========================================
# その他（相振り飛車・特殊）
# ========================================

右矢倉 = CastleDefinition(
    name="右矢倉",
    conditions=[
        CastleCondition("玉", ["2八"], required=True, weight=0.40),
        CastleCondition("金", ["3八"], required=True, weight=0.35, strict=True),
        CastleCondition("銀", ["3七"], required=True, weight=0.25, strict=True),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="矢倉を左右反転させた形。相振り飛車で用いられる。"
)

金無双 = CastleDefinition(
    name="金無双",
    conditions=[
        CastleCondition("玉", ["3八"], required=True, weight=0.40, strict=True),
        CastleCondition("金", ["4八"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["5八"], required=True, weight=0.30),
    ],
    min_confidence=0.7,
    category="振り飛車",
    description="相振り飛車の代表的な囲い。金が2枚横に並ぶ。"
)

中住まい = CastleDefinition(
    name="中住まい",
    conditions=[
        CastleCondition("玉", ["5八"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["7八"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["3八"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["4八"], required=True, weight=0.20),
    ],
    min_confidence=0.6,
    category="居飛車・振り飛車",
    description="玉を中央付近に配置する囲い。"
)

中原囲い = CastleDefinition(
    name="中原囲い",
    conditions=[
        CastleCondition("玉", ["6九"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["7八"], required=True, weight=0.20, strict=True),
        CastleCondition("金", ["5九"], required=True, weight=0.20, strict=True),
        CastleCondition("銀", ["8八"], required=True, weight=0.20),
        CastleCondition("銀", ["4八"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="中原誠十六世名人が愛用した囲い。"
)

アヒル囲い = CastleDefinition(
    name="アヒル囲い",
    conditions=[
        CastleCondition("玉", ["5八"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["7九"], required=True, weight=0.20, strict=True),
        CastleCondition("金", ["3九"], required=True, weight=0.20, strict=True),
        CastleCondition("銀", ["6八"], required=True, weight=0.20),
        CastleCondition("銀", ["4八"], required=True, weight=0.15),
    ],
    min_confidence=0.7,
    category="居飛車・振り飛車",
    description="アヒルのような形の特殊な囲い。"
)

いちご囲い = CastleDefinition(
    name="いちご囲い",
    conditions=[
        CastleCondition("玉", ["6八"], required=True, weight=0.30, strict=True),
        CastleCondition("金", ["7八"], required=True, weight=0.25, strict=True),
        CastleCondition("金", ["5八"], required=True, weight=0.25, strict=True),
        CastleCondition("銀", ["7九"], required=True, weight=0.20),
    ],
    min_confidence=0.7,
    category="居飛車",
    description="1(5)・1(6)・5(銀)で「いちご」。"
)


# ========================================
# 全ての囲いをリストにまとめる
# ========================================

ALL_CASTLES = [
    # 矢倉系
    カニ囲い, 矢倉, 金矢倉, 銀矢倉, 片矢倉, 総矢倉,
    矢倉穴熊, 菊水矢倉, 銀立ち矢倉, 菱矢倉,
    # 雁木・ボナンザ系
    雁木囲い, ボナンザ囲い,
    # 美濃系（振り飛車）
    美濃囲い, 高美濃囲い, 振り飛車銀冠, 居飛車銀冠,
    銀美濃, ダイヤモンド美濃, 木村美濃, 片美濃囲い,
    ちょんまげ美濃, 坊主美濃,
    # 左美濃系
    左美濃, 天守閣美濃, 四枚美濃,
    # 舟囲い・エルモ系
    舟囲い, エルモ囲い,
    # 穴熊系
    居飛車穴熊, 松尾流穴熊, 銀冠穴熊, ビッグ4,
    箱入り娘, ミレニアム囲い, 振り飛車穴熊,
    # その他
    右矢倉, 金無双, 中住まい, 中原囲い, アヒル囲い, いちご囲い,
]


# ========================================
# ユーティリティ関数
# ========================================

def get_castle_by_name(name: str) -> CastleDefinition:
    """
    名前で囲いを検索する。

    Args:
        name: 囲いの名前

    Returns:
        CastleDefinition: 見つかった囲い、見つからない場合はNone
    """
    for castle in ALL_CASTLES:
        if castle.name == name:
            return castle
    return None


def get_castles_by_category(category: str) -> List[CastleDefinition]:
    """
    カテゴリで囲いを検索する。

    Args:
        category: カテゴリ（"居飛車" or "振り飛車"）

    Returns:
        List[CastleDefinition]: 該当する囲いのリスト
    """
    return [castle for castle in ALL_CASTLES if category in castle.category]


def print_all_castles():
    """全ての囲いを表示する。"""
    print(f"登録されている囲いの総数: {len(ALL_CASTLES)}\n")

    print("=" * 60)
    print("居飛車の囲い")
    print("=" * 60)
    for castle in get_castles_by_category("居飛車"):
        print(f"\n【{castle.name}】")
        print(f"  説明: {castle.description}")
        print(f"  最小信頼度: {castle.min_confidence}")
        print(f"  条件数: {len(castle.conditions)}")

    print("\n" + "=" * 60)
    print("振り飛車の囲い")
    print("=" * 60)
    for castle in get_castles_by_category("振り飛車"):
        if "居飛車" not in castle.category:
            print(f"\n【{castle.name}】")
            print(f"  説明: {castle.description}")
            print(f"  最小信頼度: {castle.min_confidence}")
            print(f"  条件数: {len(castle.conditions)}")


if __name__ == "__main__":
    print_all_castles()
