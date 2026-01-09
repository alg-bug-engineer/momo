#!/usr/bin/env python3
"""
测试导入是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
from src.utils.path_utils import setup_python_path
project_root = setup_python_path(__file__)
print(f"项目根目录: {project_root}")

try:
    from src.core.auto_manga_workflow import AutoMangaWorkflow
    print("✓ 成功导入 AutoMangaWorkflow")
except ImportError as e:
    print(f"✗ 导入 AutoMangaWorkflow 失败: {e}")

try:
    from src.config.settings import SELECTORS
    print("✓ 成功导入 settings.SELECTORS")
except ImportError as e:
    print(f"✗ 导入 settings.SELECTORS 失败: {e}")

try:
    from src.utils.file_utils import save_text_to_file
    print("✓ 成功导入 save_text_to_file")
except ImportError as e:
    print(f"✗ 导入 save_text_to_file 失败: {e}")

print("\n测试完成！")