#!/usr/bin/env python3
"""
Auto-Manga 自动漫画生成项目

主入口脚本
"""

import asyncio
import sys

# 添加项目根目录到 Python 路径
from src.utils.path_utils import setup_python_path
project_root = setup_python_path(__file__)

from src.core.auto_manga_workflow import AutoMangaWorkflow


async def main():
    """主函数"""
    # 检查是否提供了 session 文件参数
    skip_script = False
    session_file = None
    
    if len(sys.argv) > 1:
        # 如果提供了参数，假设是 session 文件路径
        session_file = sys.argv[1]
        skip_script = True
        print(f"[INFO] 将从 session 文件读取内容: {session_file}")
        print("[INFO] 跳过脚本生成步骤")
    else:
        # 正常流程：生成脚本
        concept = "大模型领域的幻觉"
        print(f"[INFO] 将生成新脚本，概念: {concept}")
    
    # 创建控制器并运行工作流
    if skip_script:
        workflow = AutoMangaWorkflow()  # 不需要 concept，因为跳过生成
        await workflow.run(skip_script_generation=True, session_file=session_file)
    else:
        concept = "大模型领域的幻觉"
        workflow = AutoMangaWorkflow(concept=concept)
        await workflow.run()


if __name__ == '__main__':
    asyncio.run(main())