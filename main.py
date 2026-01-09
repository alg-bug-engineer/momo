#!/usr/bin/env python3
"""
Auto-Manga 自动漫画生成项目

主入口脚本
"""

import argparse
import asyncio
import sys
import time

# 添加项目根目录到 Python 路径
from src.utils.path_utils import setup_python_path
project_root = setup_python_path(__file__)

from src.core.auto_manga_workflow import AutoMangaWorkflow
from src.utils.logger import init_logger


async def main():
    """主函数"""
    # 生成会话ID
    session_id = str(int(time.time()))
    
    # 初始化日志系统
    logger = init_logger(session_id)
    logger.info("=== Auto-Manga 自动漫画生成项目启动 ===")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Auto-Manga 自动漫画生成项目')
    parser.add_argument('--concept', '-concept', type=str, default=None,
                        help='漫画概念/主题（例如：智能体、大模型领域的幻觉等）')
    parser.add_argument('--cover', '-c', type=str, nargs='?', const='', default=None,
                        metavar='THEME_NAME',
                        help='封面生成测试模式，可选指定主题名称')
    parser.add_argument('session_file', type=str, nargs='?', default=None,
                        help='Session 文件路径（如果提供，将跳过脚本生成步骤）')
    
    args = parser.parse_args()
    
    # 确定运行模式
    skip_script = False
    session_file = None
    skip_to_cover = False
    theme_name = None
    concept = args.concept
    
    if args.cover is not None:
        # 封面测试模式
        skip_to_cover = True
        if args.cover:  # 如果提供了主题名称
            theme_name = args.cover
        logger.info("封面生成测试模式")
        if theme_name:
            logger.info(f"使用指定主题名称: {theme_name}")
    elif args.session_file:
        # Session 文件模式
        session_file = args.session_file
        skip_script = True
        logger.info(f"将从 session 文件读取内容: {session_file}")
        logger.info("跳过脚本生成步骤")
    else:
        # 正常流程：生成脚本
        if concept is None:
            logger.error("错误：未提供概念参数。请使用 --concept 或 -concept 参数指定概念。")
            logger.info("示例: python main.py --concept 智能体")
            sys.exit(1)
        logger.info(f"将生成新脚本，概念: {concept}")
    
    try:
        # 创建控制器并运行工作流
        if skip_to_cover:
            workflow = AutoMangaWorkflow(session_id=session_id)
            await workflow.run(skip_to_cover=True, theme_name=theme_name)
        elif skip_script:
            workflow = AutoMangaWorkflow(session_id=session_id)  # 不需要 concept，因为跳过生成
            await workflow.run(skip_script_generation=True, session_file=session_file)
        else:
            workflow = AutoMangaWorkflow(concept=concept, session_id=session_id)
            await workflow.run()
            
        logger.info("=== 工作流执行完成 ===")
    except Exception as e:
        logger.exception(f"工作流执行过程中发生错误: {str(e)}")
        raise


if __name__ == '__main__':
    asyncio.run(main())