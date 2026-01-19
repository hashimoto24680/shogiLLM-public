# -*- coding: utf-8 -*-
"""
やねうら王USIエンジンのラッパー

cshogi.usi.Engine を使用してやねうら王と通信し、
MultiPV（複数候補手）や読み筋を取得する。
"""

import os
from dataclasses import dataclass

import cshogi
from cshogi import Board
from cshogi.usi import Engine, MultiPVListener

from src.simulation.models import CandidateMove, score_to_win_rate


# デフォルトのエンジンパス
DEFAULT_ENGINE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "engine", "yaneuraou",
    "YaneuraOu_NNUE_halfkp_256x2_32_32-V900Git_ZEN2.exe"
)


@dataclass
class EngineConfig:
    """
    エンジン設定を格納するデータクラス。
    
    Attributes:
        path: エンジン実行ファイルのパス
        multipv: 取得する候補手の数
        byoyomi: 探索時間（ミリ秒）。nodesが設定されている場合は無視。
        nodes: 探索ノード数制限。設定されている場合はbyoyomiより優先。
    """
    path: str = DEFAULT_ENGINE_PATH
    multipv: int = 1
    byoyomi: int = 1000
    nodes: int | None = None


class YaneuraouWrapper:
    """
    やねうら王USIエンジンのラッパークラス。
    
    局面を分析し、複数の候補手と評価値、読み筋を取得する。
    
    Attributes:
        engine: cshogi.usi.Engine インスタンス
        config: エンジン設定
    """
    
    def __init__(self, config: EngineConfig | None = None):
        """
        やねうら王ラッパーを初期化する。
        
        Args:
            config: エンジン設定。Noneの場合はデフォルト設定を使用。
        """
        self.config = config or EngineConfig()
        self._engine: Engine | None = None
    
    def connect(self) -> None:
        """
        エンジンに接続し、初期化する。
        """
        path = os.path.abspath(self.config.path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"エンジンが見つかりません: {path}")
        
        self._engine = Engine(path)
        self._engine.usi()
        
        # エンジン設定
        self._engine.setoption("Threads", 12)
        self._engine.setoption("USI_Hash", 2048)
        self._engine.setoption("MultiPV", self.config.multipv)
        
        self._engine.isready()
    
    def disconnect(self) -> None:
        """
        エンジンとの接続を終了する。
        """
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
    
    def analyze(self, sfen: str) -> list[CandidateMove]:
        """
        局面を分析し、候補手のリストを取得する。
        
        Args:
            sfen: 分析対象の局面（SFEN形式）
            
        Returns:
            候補手のリスト（評価値順）
        """
        if self._engine is None:
            self.connect()
        
        # 局面設定
        self._engine.usinewgame()
        self._engine.position(sfen=sfen)

        # 手番（SFENの手番）を取得
        # USIのscore(cp/mate)は「手番側から見た値」なので、ここで
        # 『先手有利=正、後手有利=負』に正規化する。
        board = Board()
        board.set_sfen(sfen)
        sente_multiplier = 1 if board.turn == cshogi.BLACK else -1
        
        # MultiPVリスナーで探索
        listener = MultiPVListener()
        if self.config.nodes is not None:
            # ノード数制限で探索
            self._engine.go(nodes=self.config.nodes, listener=listener.listen())
        else:
            # 秒読みで探索
            self._engine.go(byoyomi=self.config.byoyomi, listener=listener.listen())
        
        # 結果を取得
        candidates = []
        for info in listener.info:
            pv = info.get("pv", []) # 読み筋 Principal Variation
            move = pv[0] if pv else ""
            
            # スコア取得: 'cp'キーに評価値、'mate'キーに詰み手数
            if "cp" in info: # 評価値 CentiPawn
                score = int(info["cp"]) * sente_multiplier
            elif "mate" in info:
                mate = info["mate"]
                # 詰みの場合は大きな値を設定
                if mate == "+" or (isinstance(mate, int) and mate > 0):
                    score = 100000 * sente_multiplier
                else:
                    score = -100000 * sente_multiplier
            else:
                score = 0
            
            if move:
                candidates.append(CandidateMove(
                    move=move,
                    score=score,
                    win_rate=score_to_win_rate(score),
                    pv=pv,
                ))
        
        return candidates
    
    def get_pv_positions(self, sfen: str, pv: list[str]) -> list[str]:
        """
        読み筋を進めた後の各局面を取得する。
        
        Args:
            sfen: 開始局面（SFEN形式）
            pv: 読み筋の手順リスト
            
        Returns:
            各手を進めた後のSFEN形式局面のリスト
        """
        board = Board()
        board.set_sfen(sfen)
        
        positions = []
        for move_usi in pv:
            board.push_usi(move_usi)
            positions.append(board.sfen())
        
        return positions
    
    def __enter__(self):
        """コンテキストマネージャーのenter。"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのexit。"""
        self.disconnect()
        return False
