"""
USIエンジン動作確認スクリプト

このスクリプトは、やねうら王エンジンがUSIプロトコルで正しく動作するかを検証する。
cshogi_tutorial.ipynb の使用方法を参考に実装。
"""
import os
import sys
from cshogi import Board
from cshogi.usi import Engine

# エンジンパスの定義（プロジェクトルートからの相対パス）
# Windowsの場合は.exe拡張子が必要
ENGINE_PATH = os.path.abspath( # パスを正規化するため
    os.path.join(
        os.getcwd(),
        "engine/yaneuraou/YaneuraOu_NNUE_halfkp_256x2_32_32-V900Git_ZEN2.exe"
    )
)


def verify_usi():
    """
    USIエンジンの動作を検証する関数。
    
    検証内容:
        1. エンジンファイルの存在確認
        2. USIコマンドでエンジンの初期化
        3. isready でエンジン準備完了の確認
        4. position で局面設定
        5. go で探索実行と bestmove 取得
    
    Returns:
        None
    
    Raises:
        SystemExit: エンジンが見つからない場合、またはUSI通信でエラーが発生した場合
    """
    print(f"エンジンパスを確認中: {ENGINE_PATH}")
    if not os.path.exists(ENGINE_PATH):
        print(f"エラー: エンジンが見つかりません: {ENGINE_PATH}")
        sys.exit(1)
    
    print("エンジンを初期化中...")
    engine = Engine(ENGINE_PATH)
    
    try:
        # USIコマンド送信（オプション情報の取得）
        info = engine.usi()
        print(info)
        print("エンジン初期化完了（USIコマンド送信済み）")
        print(f"エンジン名: {engine.name}")
        
        # isready 送信（評価関数の読み込み等）
        print("isready を送信中...")
        engine.isready()
        print("エンジン準備完了（readyok 受信）")
        
        # usinewgame 送信
        engine.usinewgame()
        print("新しい対局を開始")
        
        # 初期局面を設定
        engine.position()
        print("初期局面を設定")
        
        # 探索実行（1秒の秒読み）
        print("1秒間探索中...")
        bestmove, pondermove = engine.go(byoyomi=1000)
        
        print(f"最善手: {bestmove}")
        if pondermove:
            print(f"予想応手: {pondermove}")
        
        print("\n=== USIエンジン検証: 成功 ===")
        
    except Exception as e:
        print(f"USI通信中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.quit()
        print("エンジンを終了しました")


if __name__ == "__main__":
    verify_usi()
