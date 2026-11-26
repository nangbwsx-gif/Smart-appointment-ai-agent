"""
pytest 公共配置

作用：
1. 保证以仓库根目录为工作目录（项目的模板/静态文件/数据库路径都是相对 CWD 的）
2. 把仓库根加入 sys.path，保证 `import app` 可用
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if Path.cwd() != ROOT:
    os.chdir(ROOT)
