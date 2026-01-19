# -*- coding: utf-8 -*-
"""
cleanse_kif_commentary.py のテスト
"""

import pytest

from src.training.cleanse_kif_commentary import (
    is_move_line,
    remove_sentences_with_keyword,
    contains_keyword,
    load_keywords
)


class TestIsMOveLine:
    """is_move_line関数のテスト"""

    def test_move_line_basic(self):
        """基本的な棋譜行を正しく判定"""
        assert is_move_line("1 ２六歩(27)") is True
        assert is_move_line("100 同　歩(23)") is True
        assert is_move_line("156 投了") is True

    def test_not_move_line(self):
        """コメント行は棋譜行ではない"""
        assert is_move_line("常磐ホテルの見どころは日本庭園。") is False
        assert is_move_line("※局後の感想※") is False

    def test_empty_line(self):
        """空行は棋譜行ではない"""
        assert is_move_line("") is False
        assert is_move_line("   ") is False


class TestRemoveSentencesWithKeyword:
    """remove_sentences_with_keyword関数のテスト"""

    def test_remove_sentence(self):
        """キーワードを含む文のみ削除"""
        line = "対局が開始された。10分の考慮で指した。次の手を見る。"
        result = remove_sentences_with_keyword(line, "分")
        assert result == "対局が開始された。次の手を見る。"

    def test_no_keyword(self):
        """キーワードがない場合は変化なし"""
        line = "対局が開始された。次の手を見る。"
        result = remove_sentences_with_keyword(line, "分")
        assert result == line

    def test_all_sentences_removed(self):
        """全文削除の場合は空文字列"""
        line = "10分の考慮。30分経過。"
        result = remove_sentences_with_keyword(line, "分")
        assert result == ""


class TestContainsKeyword:
    """contains_keyword関数のテスト"""

    def test_line_delete_keyword(self):
        """行削除キーワードを含む場合"""
        keywords = ["ホテル", "食事"]
        sentence_keywords = ["分"]
        
        should_delete, _ = contains_keyword("常磐ホテルで対局", keywords, sentence_keywords)
        assert should_delete is True

    def test_sentence_delete_keyword(self):
        """文削除キーワードは行全体を削除しない"""
        keywords = ["ホテル"]
        sentence_keywords = ["分"]
        
        should_delete, processed = contains_keyword(
            "10分の考慮で指した。良い手だ。", keywords, sentence_keywords
        )
        assert should_delete is False
        assert "良い手だ。" in processed
        assert "分" not in processed

    def test_no_keyword(self):
        """キーワードなしの場合は削除しない"""
        keywords = ["ホテル"]
        sentence_keywords = ["分"]
        
        should_delete, processed = contains_keyword(
            "良い手だ。", keywords, sentence_keywords
        )
        assert should_delete is False
        assert processed == "良い手だ。"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
