from typing import Any

import numpy as np
from cshogi import PIECE_SYMBOLS


def dlfeatures_to_sfen(feature1: np.ndarray[Any, np.dtype[Any]], feature2: np.ndarray[Any, np.dtype[Any]]) -> str:
    """
    dlshogiのfeature1とfeature2をsfenに変換する
    """
    # feature1は盤面情報、feature2は持ち駒情報がメイン
    # 手番は常に先手側にある(後手番の局面は反転させる)
    # feature1, feature2ともに各要素は0 or 1

    # feature1は(62, 9, 9)のshapeを持つ
    # 各駒(歩, 香, ..., 竜)の14種の駒がどの位置に存在しているか
    # 各駒(歩, 香, ..., 竜)の14種の駒がどの位置に利いているか
    # 各位置に何枚の駒が利いているか(最大で3)
    # 先後それぞれで計算するので、(14 + 14 + 3) * 2 = 62

    # feature2は(57, 9, 9)のshapeを持つ
    # 各駒(歩, 香, ..., 飛)の7種の駒を何枚持っているか
    # 歩はルール上18枚まで持つことができるが、9枚以上持ち駒にあることはレアケースなので
    # dlshogiでは8枚までしか扱っていない。(9枚以上持っていても、8枚しか持っていないものと見なす)
    # 最後の1チャネルは王手がかかっているかどうか
    # (歩: 8 + 香: 4 + 桂: 4 + 銀: 4 + 金: 4 + 角: 2 + 飛: 2) * 2 + 1 = 57

    # ----------feature1----------

    # 数字と駒の関係は以下の通り
    # 先手の駒に対して+8で成り駒、+16で後手の駒になるような番号が振られている
    # そのため0や15, 16に対応する駒は存在しない
    # {1: '歩', 2: '香', 3: '桂', 4: '銀', 5: '角', 6: '飛', 7: '金', 8: '玉',
    # 9: 'と', 10: '杏', 11: '圭', 12: '全', 13: '馬', 14: '龍',
    # 17: 'v歩', 18: 'v香', 19: 'v桂', 20: 'v銀', 21: 'v角', 22: 'v飛', 23: 'v金', 24: 'v玉',
    # 25: 'vと', 26: 'v杏', 27: 'v圭', 28: 'v全', 29: 'v馬', 30: 'v龍'}

    b = np.argmax(
        np.concatenate(
            [
                np.zeros_like(feature1, shape=(1, 9, 9)),  # 0
                feature1[:14],
                np.zeros_like(feature1, shape=(2, 9, 9)),  # 15, 16
                feature1[31:45],
            ]
        ),
        axis=0,
    )

    # 初期局面なら以下のような配列bが返る
    # array([[18,  0, 17,  0,  0,  0,  1,  0,  2],
    #        [19, 21, 17,  0,  0,  0,  1,  6,  3],
    #        [20,  0, 17,  0,  0,  0,  1,  0,  4],
    #        [23,  0, 17,  0,  0,  0,  1,  0,  7],
    #        [24,  0, 17,  0,  0,  0,  1,  0,  8],
    #        [23,  0, 17,  0,  0,  0,  1,  0,  7],
    #        [20,  0, 17,  0,  0,  0,  1,  0,  4],
    #        [19, 22, 17,  0,  0,  0,  1,  5,  3],
    #        [18,  0, 17,  0,  0,  0,  1,  0,  2]], dtype=int64)

    # 普通の盤面の向きに合わせるために90度右に回転させる
    b = b.T[:, ::-1]

    # ----------feature2----------

    # feature2から先手/後手の各持ち駒がそれぞれ何枚あるかの配列に変換する
    # 初期局面なら[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,]
    # 先手の持ち駒が角、後手の持ち駒が銀２枚なら[0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0,]

    pih_feature = feature2[:56, 0, 0].astype(int)
    pieces_in_hand = [
        pih_feature[:8].sum(),  # 先手の歩(上限8枚)
        pih_feature[8:12].sum(),  # 先手の香(上限4枚)
        pih_feature[12:16].sum(),  # 先手の桂(上限4枚)
        pih_feature[16:20].sum(),  # 先手の銀(上限4枚)
        pih_feature[20:24].sum(),  # 先手の金(上限4枚)
        pih_feature[24:26].sum(),  # 先手の角(上限2枚)
        pih_feature[26:28].sum(),  # 先手の飛(上限2枚)
        pih_feature[28:36].sum(),  # 後手の歩(上限8枚)
        pih_feature[36:40].sum(),  # 後手の香(上限4枚)
        pih_feature[40:44].sum(),  # 後手の桂(上限4枚)
        pih_feature[44:48].sum(),  # 後手の銀(上限4枚)
        pih_feature[48:52].sum(),  # 後手の金(上限4枚)
        pih_feature[52:54].sum(),  # 後手の角(上限2枚)
        pih_feature[54:56].sum(),  # 後手の飛(上限2枚)
    ]

    # ----------sfenへの変換----------
    sfen = []
    empty = 0
    for row in b:
        for piece in row:
            symbol = PIECE_SYMBOLS[piece % 16]
            if piece // 16 == 0:
                symbol = symbol.upper()

            if not symbol:
                empty += 1
            else:
                if empty:
                    sfen.append(str(empty))
                    empty = 0
                sfen.append(symbol)

        if empty:
            sfen.append(str(empty))
            empty = 0

        sfen.append("/")

    # 最後の/を外す
    sfen = sfen[:-1]
    sfen.append(" ")

    # 常に手番は先手側
    sfen.append("b")
    sfen.append(" ")

    # 持ち駒
    if sum(pieces_in_hand) == 0:
        sfen.append("-")
    else:
        b_pih_seq, w_pih_seq = pieces_in_hand[:7], pieces_in_hand[7:14]
        for symbol, count in zip(["r", "b", "g", "s", "n", "l", "p"], b_pih_seq[::-1], strict=False):
            if count == 0:
                continue
            if count > 1:
                sfen.append(str(count))
            sfen.append(symbol.upper())

        for symbol, count in zip(["r", "b", "g", "s", "n", "l", "p"], w_pih_seq[::-1], strict=False):
            if count == 0:
                continue
            if count > 1:
                sfen.append(str(count))
            sfen.append(symbol)

    # 手数
    sfen.append(" ")
    sfen.append("1")

    return "".join(sfen)
