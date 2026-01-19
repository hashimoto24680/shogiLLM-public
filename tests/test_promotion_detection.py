
import unittest
import cshogi
from src.features.extractor import FeatureExtractor
from src.features.dynamic import extract_dynamic_features

class TestPromotionDetection(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()

    def test_promotion_remains(self):
        """成駒が盤面に残るケース"""
        # 初期局面: 7六歩、3四歩、2二角成（後手馬ができる）
        start_sfen = "lnsgk2nl/6gs1/p1ppppb1p/6R2/9/1rP6/P2PPPP1P/1BG1K4/LNS2GSNL w 3P2p 20"
        board = cshogi.Board(start_sfen)
        before = self.extractor.extract_static(board.sfen())
        
        # 3手進める: △2二同銀 (馬を取る)、▲同金... ではなくもっと単純に
        # start_sfenから △8八角成 だけ指す
        # start_sfenはデータにあった局面を使用
        
        # △3三角 -> ▲5八玉 -> △8八角成 (馬ができる)
        # 初期局面
        initial_sfen = "lnsgk1snl/6gb1/p1pppp2p/6R2/9/1rP6/P2PPPP1P/1BG6/LNS1KGSNL w 3P2p 16"
        board = cshogi.Board(initial_sfen)
        before = self.extractor.extract_static(board.sfen())
        
        # 手順: △3三角 -> ▲5八玉 -> △8八角成
        moves = ["3a3c", "5i5h", "2b8h+"] 
        for move in moves:
            board.push_usi(move)
            
        after = self.extractor.extract_static(board.sfen())
        
        dynamic = extract_dynamic_features(before, after, moves)
        
        print(f"\nTest 1 (Remains): Promotions = {dynamic.promotions}")
        self.assertTrue(any("後手に馬" in p for p in dynamic.promotions))

    def test_promotion_captured(self):
        """成駒が取られて盤面に残らないケース"""
        # 手順: △3三角 -> ▲5八玉 -> △8八角成 -> ▲同銀 (馬が取られる)
        initial_sfen = "lnsgk1snl/6gb1/p1pppp2p/6R2/9/1rP6/P2PPPP1P/1BG6/LNS1KGSNL w 3P2p 16"
        board = cshogi.Board(initial_sfen)
        before = self.extractor.extract_static(board.sfen())
        
        moves = ["3a3c", "5i5h", "2b8h+", "7i8h"]
        for move in moves:
            board.push_usi(move)
            
        after = self.extractor.extract_static(board.sfen())
        
        dynamic = extract_dynamic_features(before, after, moves)
        
        print(f"Test 2 (Captured): Promotions = {dynamic.promotions}")
        # 成駒は残っていないので空のはず
        self.assertEqual(len(dynamic.promotions), 0)

    def test_existing_promotion_moves(self):
        """既に存在する成駒が移動するだけのケース"""
        # 初期局面で既に馬がいる状態を作る
        # ln1g4l/2s1ksgb1/p1ppppn1p/6RP1/2P6/P8/2NPPPP1P/1+B1G1K4/LNS2GSNL b 2Pb2p 12
        # (盤面適当ですが、8八に馬がいるとします)
        
        # 簡易的に作る: 初期局面から馬を作る手順を進めた状態をstartとする
        initial_sfen = "lnsgk1snl/6gb1/p1pppp2p/6R2/9/1rP6/P2PPPP1P/1BG6/LNS1KGSNL w 3P2p 16"
        board = cshogi.Board(initial_sfen)
        board.push_usi("3a3c")
        board.push_usi("5i5h")
        board.push_usi("2b8h+") # 馬ができる
        
        start_sfen = board.sfen()
        before = self.extractor.extract_static(start_sfen)
        
        # 馬を移動させるだけの局面
        board.push_usi("8h6f") # 馬が移動
        after_sfen = board.sfen()
        after = self.extractor.extract_static(after_sfen)
        
        dynamic = extract_dynamic_features(before, after, ["8h6f"])
        
        print(f"Test 3 (Existing Move): Promotions = {dynamic.promotions}")
        # 成駒の数は変わっていないので空のはず
        self.assertEqual(len(dynamic.promotions), 0)

if __name__ == '__main__':
    unittest.main()
