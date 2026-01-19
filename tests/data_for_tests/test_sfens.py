# テスト用SFENデータ
# 局面を使うテストはすべてのSFENでテストし、すべてpassすること

# ============================================================
# 基本テスト用
# ============================================================

# 初期局面（先手番）
INITIAL_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"

# 飛車得局面（先手持ち駒に飛車）
ROOK_ADVANTAGE_SFEN = "lnsgkgsnl/7b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b R 1"

# 先手居飛車エルモ囲い＋後手四間飛車美濃囲い
# 囲い・戦法の複合テスト用
ELMO_VS_SHIKEN_SFEN = "ln1g3nl/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1PSP2P/1BKS3R1/LNG1G2NL b - 1"

# ============================================================
# 勝率変換テスト用局面（先手/後手 × 有利/不利 の4パターン）
# ============================================================

# パターン1: （角換わり中盤）
# 後手番、後手不利 
KAKUGAWARI_CHUBAN_SFEN = "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28"

# パターン2: （角換わり中盤2）
# 先手番、先手有利
KAKUGAWARI_CHUBAN2_SFEN = "ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29"

# パターン3: （棒銀終盤2）
# 後手番、後手が極めて有利
BOUGIN_SHUUBAN2_SFEN = "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30"

# パターン4: （棒銀終盤）
# 先手番、先手が極めて不利
BOUGIN_SHUUBAN_SFEN = "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29"

# ============================================================
# テストで使用するSFEN一覧
# ============================================================

ALL_TEST_SFENS = [
    INITIAL_SFEN,
    ROOK_ADVANTAGE_SFEN,
    ELMO_VS_SHIKEN_SFEN,
    KAKUGAWARI_CHUBAN_SFEN,
    KAKUGAWARI_CHUBAN2_SFEN,
    BOUGIN_SHUUBAN_SFEN,
    BOUGIN_SHUUBAN2_SFEN,
]
