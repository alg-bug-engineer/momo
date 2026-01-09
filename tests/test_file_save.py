#!/usr/bin/env python3
"""
测试文件保存功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.file_utils import save_text_to_file

def test_file_save():
    """测试文件保存功能"""
    test_content = """
测试内容

这是用于测试文件保存功能的内容。

包含多行文本和一些特殊字符：
- 中文
- English
- 数字：123456
- 符号：!@#$%^&*()
"""
    try:
        # 测试默认目录
        print("测试默认目录保存...")
        saved_path = save_text_to_file(test_content)
        print(f"✓ 文件已保存到: {saved_path}")
        
        # 测试指定目录
        print("\n测试指定目录保存...")
        saved_path2 = save_text_to_file(test_content, "test_file.txt", "data/sessions")
        print(f"✓ 文件已保存到: {saved_path2}")
        
    except Exception as e:
        print(f"✗ 保存失败: {e}")

if __name__ == "__main__":
    test_file_save()