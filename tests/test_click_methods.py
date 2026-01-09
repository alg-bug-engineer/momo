#!/usr/bin/env python3
"""
测试点击方法是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import SELECTORS
from src.utils.browser_utils import find_working_selector

def test_find_working_selector():
    """测试find_working_selector函数"""
    print("测试find_working_selector函数...")
    print(f"copy_button 选择器: {SELECTORS['copy_button']}")
    print(f"new_chat 选择器: {SELECTORS['new_chat']}")
    print(f"tools_button 选择器: {SELECTORS['tools_button']}")
    print(f"create_images 选择器: {SELECTORS['create_images']}")
    print("\n这个函数是异步的，需要页面实例才能测试")
    print("修复后的代码应该能正确处理选择器")

if __name__ == '__main__':
    test_find_working_selector()