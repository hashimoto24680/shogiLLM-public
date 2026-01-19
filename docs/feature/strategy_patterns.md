# 戦法パターンデータベース設計

戦法を認識するためのパターン定義とconfidence計算ロジック。

## データ構造

```python
@dataclass
class StrategyCondition:
    """戦法の条件"""
    condition_type: str   # "piece_on", "piece_moved", "file_control" etc.
    params: dict          # 条件パラメータ
    required: bool
    weight: float

@dataclass
class StrategyDefinition:
    """戦法の定義"""
    name: str
    category: str         # "居飛車", "振り飛車", "相振り" etc.
    conditions: list[StrategyCondition]
    min_confidence: float
```

## 条件タイプ

| タイプ | 説明 | パラメータ例 |
|--------|------|-------------|
| `piece_on` | 駒がマスにいる | `{"piece": "飛", "squares": ["2八"]}` |
| `piece_on_file` | 駒が筋にいる | `{"piece": "飛", "files": [4, 5, 6]}` |
| `piece_not_moved` | 駒が初期位置 | `{"piece": "飛"}` |
| `castle_match` | 囲いがマッチ | `{"castle": "美濃"}` |

---

## 戦法パターン定義

### 居飛車系

| 戦法名 | 条件 |
|--------|------|
| **居飛車** | 飛:2筋(必須,0.5), 玉:8筋以上(オプション,0.3), 角:初期位置or交換済(オプション,0.2) |
| **矢倉戦法** | 飛:2筋(必須,0.3), 囲い:矢倉(必須,0.5), 銀:7七(オプション,0.2) |
| **角換わり** | 角:持ち駒(必須,0.5), 飛:2筋(必須,0.3), 銀:7七or5七(オプション,0.2) |
| **相掛かり** | 飛:2筋(必須,0.4), 歩:2五(必須,0.4), 角:初期位置(オプション,0.2) |

### 振り飛車系

| 戦法名 | 条件 |
|--------|------|
| **四間飛車** | 飛:6筋(必須,0.5), 玉:8筋以上(オプション,0.3), 囲い:美濃系(オプション,0.2) |
| **三間飛車** | 飛:7筋(必須,0.5), 玉:8筋以上(オプション,0.3), 囲い:美濃系(オプション,0.2) |
| **中飛車** | 飛:5筋(必須,0.5), 玉:左寄り(オプション,0.3), 歩:5六(オプション,0.2) |
| **向かい飛車** | 飛:8筋(必須,0.5), 玉:2筋付近(オプション,0.3), 囲い:美濃系(オプション,0.2) |
| **ゴキゲン中飛車** | 飛:5筋(必須,0.4), 歩:5五(必須,0.4), 角:2二(オプション,0.2) |

### 対抗形

| 戦法名 | 条件 |
|--------|------|
| **居飛車穴熊** | 飛:2筋(必須,0.3), 囲い:穴熊(必須,0.5), 対戦相手:振り飛車(オプション,0.2) |
| **藤井システム** | 飛:6筋(必須,0.3), 玉:居玉付近(必須,0.4), 角:攻撃位置(オプション,0.3) |

---

## 実装例

```python
STRATEGY_PATTERNS = {
    "四間飛車": StrategyDefinition(
        name="四間飛車",
        category="振り飛車",
        conditions=[
            StrategyCondition(
                condition_type="piece_on_file",
                params={"piece": "飛", "files": [6]},
                required=True,
                weight=0.50
            ),
            StrategyCondition(
                condition_type="piece_on_file",
                params={"piece": "玉", "files": [8, 9]},
                required=False,
                weight=0.30
            ),
            StrategyCondition(
                condition_type="castle_match",
                params={"castles": ["美濃", "銀冠", "穴熊"]},
                required=False,
                weight=0.20
            ),
        ],
        min_confidence=0.5
    ),
    "居飛車": StrategyDefinition(
        name="居飛車",
        category="居飛車",
        conditions=[
            StrategyCondition(
                condition_type="piece_on_file",
                params={"piece": "飛", "files": [2]},
                required=True,
                weight=0.50
            ),
            StrategyCondition(
                condition_type="piece_on_file",
                params={"piece": "玉", "files": [6, 7, 8, 9]},
                required=False,
                weight=0.30
            ),
        ],
        min_confidence=0.5
    ),
    # ... 他の戦法
}
```
