# -*- coding: utf-8 -*-
"""
pytest設定ファイル

このファイルをtests/に配置することで、pytestがプロジェクトルートを
モジュールパスとして認識するようになる。
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
