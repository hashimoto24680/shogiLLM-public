# 局面特徴生成エンジン 検証計画

## 概要

`src/features/` パッケージの検証計画。静的特徴・動的特徴の抽出が正しく動作することを確認する。

---

## 自動テスト

### テストファイル

`tests/test_features.py`

### 実行コマンド

```bash
pytest tests/test_features.py -v
```

---

## テストデータ

テスト用SFENは `tests/data_for_tests/` に集約する。

### 共通テストSFEN一覧

| 名前 | SFEN | 用途 |
|------|------|------|
| 初期局面 | `lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1` | 基本テスト |
| 飛車得局面 | `lnsgkgsnl/7b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b R 1` | 駒得テスト |
| 先手居飛車エルモ＋後手四間美濃 | `ln1g3nl/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1PSP2P/1BKS3R1/LNG1G2NL b - 1` | 囲い・戦法複合テスト |
| 角換わり中盤（後手番・後手不利） | `ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28` | 勝率変換テスト |
| 角換わり中盤2（先手番・先手有利） | `ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29` | 勝率変換テスト |
| 棒銀終盤（先手番・先手極めて不利） | `ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29` | 勝率変換テスト |
| 棒銀終盤2（後手番・後手極めて有利） | `ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30` | 勝率変換テスト |

> **注意**: 局面を使うテストは**すべてのSFEN**でテストし、**すべてpass**すること。

---

## テストケース一覧

### 低次元静的特徴（static_low.py）

> **SFEN一致確認**: 入力したSFENと`StaticFeatures.sfen`が一致することを確認。

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_square_to_japanese` | マス番号→日本語座標変換 | - | `coordinates.py`で実装済み。テストで確認。 |
| `test_get_adjacent_squares` | 隣接マス取得 | 全81マス | `data_for_tests/adjacant_squares.py`の全データがpass |
| `test_extract_all_squares` | 81マス情報抽出 | 全SFEN | 81個のSquareInfo。結果を`features/`に出力して確認可能に。 |
| `test_extract_hand_pieces` | 持ち駒抽出 | 全SFEN | 正しい枚数 |
| `test_piece_info_in_square` | マスに駒情報が含まれる | 全SFEN | PieceInfo.piece_type等が正しい |

### 高次元静的特徴（static_high.py）

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_recognize_castle_elmo` | エルモ囲い認識 | 先手居飛車エルモ局面 | 先手にエルモ囲いがマッチ |
| `test_recognize_castle_mino` | 美濃囲い認識 | 先手居飛車エルモ局面 | 後手に美濃囲いがマッチ |
| `test_recognize_strategy_ibisha` | 居飛車認識 | 先手居飛車エルモ局面 | 先手が居飛車と判定 |
| `test_recognize_strategy_shiken` | 四間飛車認識 | 先手居飛車エルモ局面 | 後手が四間飛車と判定 |
| `test_calculate_king_safety` | 玉安全度計算 | 全SFEN | 妥当なsafety_score |

### 駒得計算（material.py）

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_calculate_material_initial` | 初期局面の駒得 | 初期局面 | advantage = 0 |
| `test_calculate_material_advantage` | 駒得あり局面 | 飛車得局面 | advantage ≈ 10 |
| `test_piece_values` | 駒点数定義 | - | 飛=10, 角=8, 等 |

### 駒の働き（piece_activity.py, dlshogi_wrapper.py）

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_dlshogi_predict` | dlshogi推論 | 全SFEN | value: 0.0-1.0 |
| `test_piece_activity_calculation` | 駒の働き計算 | 全SFEN | 各駒のactivity値 |

### 動的特徴（dynamic.py）

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_extract_dynamic_features` | 2局面比較 | before, after | DynamicFeatures |
| `test_dynamic_with_moves` | 手順付き比較 | moves_between指定 | moves_betweenが保持される |

### 統合API（extractor.py）

| テストケース | 検証内容 | 入力 | 期待結果 |
|-------------|---------|------|---------|
| `test_extract_static` | 静的特徴抽出 | 全SFEN | StaticFeatures |
| `test_extract_dynamic` | 動的特徴抽出 | 2つのSFEN | DynamicFeatures |
| `test_to_text` | テキスト変換 | StaticFeatures | LLM入力用文字列 |

---

## 手動検証

### Jupyter Notebook確認

`notebooks/feature_extraction_demo.ipynb` を作成し、以下を確認：

1. 実際の棋譜局面で特徴抽出
2. 抽出結果の可視化
3. LLM入力用テキストの確認

### 論文の図との比較

論文で使用する図（▲6五歩の例など）で期待通りの特徴が抽出されるか確認。

---

## 依存関係

| ファイル | 依存先 |
|---------|-------|
| static_low.py | cshogi, models.py, coordinates.py |
| static_high.py | static_low.py, patterns/*, material.py, dlshogi_wrapper.py |
| dynamic.py | static_low.py, static_high.py |
| extractor.py | 全て |
