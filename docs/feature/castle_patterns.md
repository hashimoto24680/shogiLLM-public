# 囲いパターンデータベース設計

囲いを認識するためのパターン定義とconfidence計算ロジック。

## データ構造

```python
@dataclass
class CastleCondition:
    """囲いの条件（1つの駒配置）"""
    piece_type: str       # "金", "銀", "玉" etc.
    squares: list[str]    # 許容されるマス（OR条件）例: ["7八", "6八"]
    required: bool        # True=必須, False=オプション
    weight: float         # confidence計算の重み（0.0〜1.0）

@dataclass
class CastleDefinition:
    """囲いの定義"""
    name: str
    conditions: list[CastleCondition]
    min_confidence: float  # この値以上でマッチと判定（デフォルト: 0.7）
```

## Confidence計算ロジック

### 基本式
```
条件スコア = max(0, weight - 距離 * 0.1)
confidence = Σ(条件スコア) / Σ(全条件のweight)
```

### 距離計算
- 条件で指定されたマスと、実際の駒位置との**ユークリッド距離**（小数点以下1桁で丸め）
- 例: 条件「玉:8八」、実際「玉:7八」→ 距離=1.0 → スコア=0.3-0.1=0.2
- 例: 条件「銀:7七」、実際「銀:6六」→ 距離=√2≈1.4 → スコア=0.2-0.14=0.06

### 複数枚ある駒の扱い
同じ駒種が複数ある場合（金2枚、銀2枚など）：
1. 各条件に対して、盤上の同種駒から**最も距離が近い駒**を対応させる
2. 1つの駒は1つの条件にしか対応できない（貪欲法でマッチング）
3. 対応する駒がない場合 → スコア=0

### 必須条件の扱い
- 必須条件が1つでも「スコア=0」→ confidence=0.0（囲い不成立）

---

## 囲いパターン定義

### 先手の囲い（後手は座標を反転: 筋は10-筋、段は10-段）

| 囲い名 | 条件（先手） |
|--------|------|
| **矢倉** | 玉:8八(必須,0.25), 金:7八(必須,0.25), 金:6七(必須,0.25), 銀:7七(必須,0.25) |
| **美濃** | 玉:2八(必須,0.25), 金:5八(必須,0.25), 銀:3八(必須,0.25), 金:4九(必須,0.25) |
---

## 実装例

```python
CASTLE_PATTERNS = {
    "矢倉": CastleDefinition(
        name="矢倉",
        conditions=[
            CastleCondition("玉", ["8八"], required=True, weight=0.30),
            CastleCondition("金", ["7八"], required=True, weight=0.25),
            CastleCondition("金", ["6七"], required=True, weight=0.25),
            CastleCondition("銀", ["7七"], required=True, weight=0.20),
        ],
        min_confidence=0.7
    ),
    "美濃": CastleDefinition(
        name="美濃",
        conditions=[
            CastleCondition("玉", ["8八"], required=True, weight=0.20),
            CastleCondition("金", ["5八"], required=True, weight=0.30),
            CastleCondition("銀", ["7八"], required=True, weight=0.25),
            CastleCondition("銀", ["6九"], required=False, weight=0.15),
            CastleCondition("桂", ["9九"], required=False, weight=0.10),
        ],
        min_confidence=0.7
    ),
    # ... 他の囲い
}
```
