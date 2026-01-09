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
    # 检查是否提供了参数
    skip_script = False
    session_file = None
    skip_to_cover = False
    theme_name = None
    concept = "聚类"
    
    if len(sys.argv) > 1:
        # 解析命令行参数
        args = sys.argv[1:]
        
        # 检查是否是封面测试模式
        if '--cover' in args or '-c' in args:
            skip_to_cover = True
            # 查找主题名称参数
            try:
                cover_index = args.index('--cover') if '--cover' in args else args.index('-c')
                if cover_index + 1 < len(args) and not args[cover_index + 1].startswith('-'):
                    theme_name = args[cover_index + 1]
            except:
                pass
            print("[INFO] 封面生成测试模式")
            if theme_name:
                print(f"[INFO] 使用指定主题名称: {theme_name}")
        else:
            # 如果提供了参数，假设是 session 文件路径
            session_file = args[0]
            skip_script = True
            print(f"[INFO] 将从 session 文件读取内容: {session_file}")
            print("[INFO] 跳过脚本生成步骤")
    else:
        # 正常流程：生成脚本
        print(f"[INFO] 将生成新脚本，概念: {concept}")
    
    # 创建控制器并运行工作流
    if skip_to_cover:
        workflow = AutoMangaWorkflow()
        await workflow.run(skip_to_cover=True, theme_name=theme_name)
    elif skip_script:
        workflow = AutoMangaWorkflow()  # 不需要 concept，因为跳过生成
        await workflow.run(skip_script_generation=True, session_file=session_file)
    else:
        workflow = AutoMangaWorkflow(concept=concept)
        await workflow.run()


if __name__ == '__main__':
    asyncio.run(main())